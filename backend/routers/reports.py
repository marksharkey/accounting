from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract
from typing import Optional
from datetime import date
from decimal import Decimal
import io

import models
from database import get_db
from auth import get_current_user
from services.pdf import generate_pl_pdf

router = APIRouter()


@router.get("/ar-aging")
def ar_aging(
    as_of: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    as_of = as_of or date.today()
    invoices = db.query(models.Invoice).filter(
        models.Invoice.status.in_([
            models.InvoiceStatus.sent,
            models.InvoiceStatus.partially_paid
        ]),
        ~models.Invoice.exclude_from_ar_aging
    ).all()

    # Group by client
    client_data = {}
    for inv in invoices:
        days_overdue = (as_of - inv.due_date).days
        client_name = inv.client.display_name
        if client_name not in client_data:
            client_data[client_name] = {
                "current": 0,
                "1_30": 0,
                "31_60": 0,
                "61_90": 0,
                "over_90": 0,
            }

        balance = float(inv.balance_due)

        if days_overdue <= 0:
            client_data[client_name]["current"] += balance
        elif days_overdue <= 30:
            client_data[client_name]["1_30"] += balance
        elif days_overdue <= 60:
            client_data[client_name]["31_60"] += balance
        elif days_overdue <= 90:
            client_data[client_name]["61_90"] += balance
        else:
            client_data[client_name]["over_90"] += balance

    # Add credit balances from applied credit memos (show as negative in over_90)
    applied_credits = db.query(models.CreditMemo).filter(
        models.CreditMemo.status == models.CreditMemoStatus.applied
    ).all()

    for cm in applied_credits:
        client_name = cm.client.display_name
        if client_name not in client_data:
            client_data[client_name] = {
                "current": 0,
                "1_30": 0,
                "31_60": 0,
                "61_90": 0,
                "over_90": 0,
            }
        # Show credits as negative in over_90 bucket
        client_data[client_name]["over_90"] -= float(cm.total)

    # Build client rows
    clients = []
    totals = {"current": 0, "1_30": 0, "31_60": 0, "61_90": 0, "over_90": 0}
    for client_name in sorted(client_data.keys(), key=str.lower):
        amounts = client_data[client_name]
        balance = sum(amounts.values())
        clients.append({
            "name": client_name,
            "current": amounts["current"],
            "1_30": amounts["1_30"],
            "31_60": amounts["31_60"],
            "61_90": amounts["61_90"],
            "over_90": amounts["over_90"],
            "balance": balance,
        })
        for period in totals:
            totals[period] += amounts[period]

    grand_total = sum(totals.values())
    return {
        "as_of": as_of,
        "clients": clients,
        "totals": totals,
        "grand_total": grand_total
    }


@router.get("/revenue-by-period")
def revenue_by_period(
    year: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    results = db.query(
        extract('month', models.Invoice.created_date).label('month'),
        func.sum(models.Invoice.total).label('total'),
        func.count(models.Invoice.id).label('count')
    ).filter(
        extract('year', models.Invoice.created_date) == year,
        models.Invoice.status.in_([
            models.InvoiceStatus.sent,
            models.InvoiceStatus.partially_paid,
            models.InvoiceStatus.paid
        ])
    ).group_by('month').order_by('month').all()

    months = ["January","February","March","April","May","June",
              "July","August","September","October","November","December"]
    data = {m: {"total": 0, "count": 0} for m in months}
    for row in results:
        data[months[int(row.month) - 1]] = {"total": float(row.total or 0), "count": row.count}

    return {"year": year, "months": data, "annual_total": sum(v["total"] for v in data.values())}


@router.get("/client-revenue-summary")
def client_revenue_summary(
    year: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    results = db.query(
        models.Client.id,
        models.Client.company_name,
        func.sum(models.Invoice.total).label('total'),
        func.count(models.Invoice.id).label('invoice_count')
    ).join(models.Invoice).filter(
        extract('year', models.Invoice.created_date) == year,
        models.Invoice.status != models.InvoiceStatus.voided
    ).group_by(models.Client.id).order_by(func.sum(models.Invoice.total).desc()).all()

    return {
        "year": year,
        "clients": [
            {"client_id": r.id, "company_name": r.company_name,
             "total": float(r.total or 0), "invoice_count": r.invoice_count}
            for r in results
        ]
    }


@router.get("/profit-loss")
def profit_loss(
    from_date: date,
    to_date: date,
    db: Session = Depends(get_db),
):
    """
    Accrual basis income statement (P&L) from journal entries.
    Income is revenue account credits minus debits/refunds (4xxx).
    Expenses are expense account debits (5xxx, 6xxx).
    """

    # Income: Sum credits and debits from revenue accounts (4xxx) in journal entries
    # Net income per account = credits - debits (debits are refunds/adjustments)
    income_results = db.query(
        models.JournalEntry.gl_account_code.label('code'),
        models.JournalEntry.gl_account_name.label('name'),
        func.sum(models.JournalEntry.credit).label('credits'),
        func.sum(models.JournalEntry.debit).label('debits')
    ).filter(
        and_(
            models.JournalEntry.transaction_date >= from_date,
            models.JournalEntry.transaction_date <= to_date,
            models.JournalEntry.gl_account_code.like('4%')
        )
    ).group_by(
        models.JournalEntry.gl_account_code,
        models.JournalEntry.gl_account_name
    ).order_by(models.JournalEntry.gl_account_code).all()

    # Calculate net income per account (credits - debits)
    income_data = [
        {
            "code": r.code,
            "name": r.name,
            "amount": float((r.credits or 0) - (r.debits or 0))
        }
        for r in income_results
    ]
    total_income = sum(item["amount"] for item in income_data)

    # Expenses: Sum debits from expense accounts (5xxx, 6xxx) in journal entries
    expense_results = db.query(
        models.JournalEntry.gl_account_code.label('code'),
        models.JournalEntry.gl_account_name.label('name'),
        func.sum(models.JournalEntry.debit).label('total')
    ).filter(
        and_(
            models.JournalEntry.transaction_date >= from_date,
            models.JournalEntry.transaction_date <= to_date,
            (models.JournalEntry.gl_account_code.like('5%')) |
            (models.JournalEntry.gl_account_code.like('6%'))
        )
    ).group_by(
        models.JournalEntry.gl_account_code,
        models.JournalEntry.gl_account_name
    ).order_by(models.JournalEntry.gl_account_code).all()

    # Group expenses by category (A&G, Server Management Fees, etc.)
    expenses_by_category = {}
    for r in expense_results:
        # Extract category from account name (prefix before ":")
        if ':' in r.name:
            category = r.name.split(':')[0]
            line_item = r.name.split(':', 1)[1].strip()
        else:
            category = r.name
            line_item = None

        if category not in expenses_by_category:
            expenses_by_category[category] = []

        expenses_by_category[category].append({
            "code": r.code,
            "name": r.name,
            "line_item": line_item,
            "amount": float(r.total or 0)
        })

    # Build hierarchical expense structure
    expense_data = []
    for category in sorted(expenses_by_category.keys()):
        items = expenses_by_category[category]

        # If category has sub-items (contains colons), show as group
        if any(':' in item['name'] for item in items):
            expense_data.append({
                "type": "category",
                "name": category,
                "items": items,
                "subtotal": sum(item["amount"] for item in items)
            })
        else:
            # Single item categories, add as individual lines
            for item in items:
                expense_data.append({
                    "type": "line",
                    "code": item["code"],
                    "name": item["name"],
                    "amount": item["amount"]
                })

    total_expenses = sum(float(r.total or 0) for r in expense_results)

    return {
        "period": {"from": from_date, "to": to_date},
        "income": income_data,
        "total_income": total_income,
        "expenses": expense_data,
        "total_expenses": total_expenses,
        "net_income": total_income - total_expenses,
    }


@router.get("/profit-loss/pdf")
def profit_loss_pdf(
    from_date: date,
    to_date: date,
    db: Session = Depends(get_db),
):
    """Generate P&L statement as PDF (accrual basis, from journal entries)."""
    # Income: Sum credits and debits from revenue accounts (4xxx)
    # Net income per account = credits - debits (debits are refunds/adjustments)
    income_results = db.query(
        models.JournalEntry.gl_account_code.label('code'),
        models.JournalEntry.gl_account_name.label('name'),
        func.sum(models.JournalEntry.credit).label('credits'),
        func.sum(models.JournalEntry.debit).label('debits')
    ).filter(
        and_(
            models.JournalEntry.transaction_date >= from_date,
            models.JournalEntry.transaction_date <= to_date,
            models.JournalEntry.gl_account_code.like('4%')
        )
    ).group_by(
        models.JournalEntry.gl_account_code,
        models.JournalEntry.gl_account_name
    ).order_by(models.JournalEntry.gl_account_code).all()

    # Calculate net income per account (credits - debits)
    income_data = [
        {
            "code": r.code,
            "name": r.name,
            "amount": float((r.credits or 0) - (r.debits or 0))
        }
        for r in income_results
    ]
    total_income = sum(item["amount"] for item in income_data)

    # Expenses: Sum debits from expense accounts (5xxx, 6xxx) in journal entries
    expense_results = db.query(
        models.JournalEntry.gl_account_code.label('code'),
        models.JournalEntry.gl_account_name.label('name'),
        func.sum(models.JournalEntry.debit).label('total')
    ).filter(
        and_(
            models.JournalEntry.transaction_date >= from_date,
            models.JournalEntry.transaction_date <= to_date,
            (models.JournalEntry.gl_account_code.like('5%')) |
            (models.JournalEntry.gl_account_code.like('6%'))
        )
    ).group_by(
        models.JournalEntry.gl_account_code,
        models.JournalEntry.gl_account_name
    ).order_by(models.JournalEntry.gl_account_code).all()

    # Group expenses by category (A&G, Server Management Fees, etc.)
    expenses_by_category = {}
    for r in expense_results:
        # Extract category from account name (prefix before ":")
        if ':' in r.name:
            category = r.name.split(':')[0]
            line_item = r.name.split(':', 1)[1].strip()
        else:
            category = r.name
            line_item = None

        if category not in expenses_by_category:
            expenses_by_category[category] = []

        expenses_by_category[category].append({
            "code": r.code,
            "name": r.name,
            "line_item": line_item,
            "amount": float(r.total or 0)
        })

    # Build hierarchical expense structure
    expense_data = []
    for category in sorted(expenses_by_category.keys()):
        items = expenses_by_category[category]

        # If category has sub-items (contains colons), show as group
        if any(':' in item['name'] for item in items):
            expense_data.append({
                "type": "category",
                "name": category,
                "items": items,
                "subtotal": sum(item["amount"] for item in items)
            })
        else:
            # Single item categories, add as individual lines
            for item in items:
                expense_data.append({
                    "type": "line",
                    "code": item["code"],
                    "name": item["name"],
                    "amount": item["amount"]
                })

    total_expenses = sum(float(r.total or 0) for r in expense_results)

    # Get company info for header
    company = db.query(models.CompanyInfo).first()

    data = {
        "from_date": from_date,
        "to_date": to_date,
        "income": income_data,
        "total_income": total_income,
        "expenses": expense_data,
        "total_expenses": total_expenses,
        "net_income": total_income - total_expenses,
    }

    output_type, output_bytes = generate_pl_pdf(data, company)

    if output_type == "pdf":
        return StreamingResponse(
            output_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=profit_loss.pdf"}
        )
    else:
        # HTML output - user can print to PDF from browser
        return StreamingResponse(
            io.BytesIO(output_bytes),
            media_type="text/html; charset=utf-8",
            headers={"Content-Disposition": "inline; filename=profit_loss.html"}
        )


@router.get("/profit-loss/transactions")
def profit_loss_transactions(
    from_date: date,
    to_date: date,
    account_code: Optional[str] = None,
    account_name_prefix: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get journal entries for a specific account/category within a date range."""
    query = db.query(models.JournalEntry).filter(
        and_(
            models.JournalEntry.transaction_date >= from_date,
            models.JournalEntry.transaction_date <= to_date,
        )
    )

    if account_code:
        query = query.filter(models.JournalEntry.gl_account_code == account_code)
    elif account_name_prefix:
        query = query.filter(models.JournalEntry.gl_account_name.like(f"{account_name_prefix}:%"))

    entries = query.order_by(models.JournalEntry.transaction_date.desc()).all()

    return {
        "entries": [
            {
                "date": e.transaction_date,
                "gl_account_code": e.gl_account_code,
                "gl_account_name": e.gl_account_name,
                "description": e.description or "",
                "reference_number": e.reference_number or "",
                "debit": float(e.debit),
                "credit": float(e.credit),
            }
            for e in entries
        ]
    }


@router.get("/recurring-revenue")
def recurring_revenue(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    schedules = db.query(models.BillingSchedule).filter_by(is_active=True).all()
    cycle_to_monthly = {
        models.BillingCycle.monthly: 1,
        models.BillingCycle.quarterly: 3,
        models.BillingCycle.semi_annual: 6,
        models.BillingCycle.annual: 12,
        models.BillingCycle.multi_year: 24,
    }
    mrr = Decimal("0.00")
    by_cycle = {}
    for s in schedules:
        months = cycle_to_monthly.get(s.cycle, 1)
        mrr += Decimal(str(s.amount)) / months
        key = s.cycle.value
        if key not in by_cycle:
            by_cycle[key] = {"count": 0, "total": Decimal("0.00")}
        by_cycle[key]["count"] += 1
        by_cycle[key]["total"] += Decimal(str(s.amount))

    return {
        "mrr": float(mrr),
        "arr": float(mrr * 12),
        "by_cycle": {k: {"count": v["count"], "total": float(v["total"])} for k, v in by_cycle.items()},
        "active_schedules": len(schedules),
    }
