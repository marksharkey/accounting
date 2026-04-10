from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract
from typing import Optional
from datetime import date
from decimal import Decimal

import models
from database import get_db
from auth import get_current_user

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
        ])
    ).all()

    buckets = {"current": [], "1_30": [], "31_60": [], "61_90": [], "over_90": []}
    for inv in invoices:
        days_overdue = (as_of - inv.due_date).days
        entry = {
            "invoice_number": inv.invoice_number,
            "client": inv.client.company_name,
            "due_date": inv.due_date,
            "days_overdue": max(0, days_overdue),
            "balance": float(inv.balance_due),
        }
        if days_overdue <= 0:
            buckets["current"].append(entry)
        elif days_overdue <= 30:
            buckets["1_30"].append(entry)
        elif days_overdue <= 60:
            buckets["31_60"].append(entry)
        elif days_overdue <= 90:
            buckets["61_90"].append(entry)
        else:
            buckets["over_90"].append(entry)

    totals = {k: sum(e["balance"] for e in v) for k, v in buckets.items()}
    return {"as_of": as_of, "buckets": buckets, "totals": totals, "grand_total": sum(totals.values())}


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
    current_user: models.User = Depends(get_current_user)
):
    invoices = db.query(models.Invoice).filter(
        and_(
            models.Invoice.created_date >= from_date,
            models.Invoice.created_date <= to_date,
            models.Invoice.status != models.InvoiceStatus.voided
        )
    ).all()
    total_income = sum(float(inv.total) for inv in invoices)

    expense_results = db.query(
        models.ChartOfAccount.code,
        models.ChartOfAccount.name,
        func.sum(models.Expense.amount).label('total')
    ).join(models.Expense, models.Expense.category_id == models.ChartOfAccount.id
    ).filter(
        and_(models.Expense.expense_date >= from_date, models.Expense.expense_date <= to_date)
    ).group_by(models.ChartOfAccount.id).all()

    total_expenses = sum(float(r.total or 0) for r in expense_results)

    return {
        "period": {"from": from_date, "to": to_date},
        "total_income": total_income,
        "expenses": [{"code": r.code, "name": r.name, "total": float(r.total or 0)} for r in expense_results],
        "total_expenses": total_expenses,
        "net_income": total_income - total_expenses,
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
