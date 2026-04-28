#!/usr/bin/env python3
"""
QBO → PrecisionPros Database Import

Modes:
  --full   Truncate all data tables and reimport everything from QBO.
           Use this once for the initial historical import.
  --sync   Import only records modified since the last successful sync.
           Use this for ongoing updates.

Usage:
  python3 qbo_import.py --full [--dry-run]
  python3 qbo_import.py --sync [--dry-run]

Requires:
  - qbo_tokens.json (run qbo_oauth.py first)
  - QBO_CLIENT_ID and QBO_CLIENT_SECRET in .env
"""

import argparse
import json
import os
import sys
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy.orm import Session

load_dotenv()

from database import SessionLocal
import models
from qbo_client import QBOClient

SYNC_FILE = os.path.join(os.path.dirname(__file__), "qbo_last_sync.json")

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def d(val, default="0.00") -> Decimal:
    try:
        return Decimal(str(val or default))
    except InvalidOperation:
        return Decimal(default)


def parse_date(val) -> Optional[date]:
    if not val:
        return None
    if isinstance(val, date):
        return val
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(str(val), fmt).date()
        except ValueError:
            continue
    return None


def addr(obj: dict, field: str) -> str:
    return (obj.get(field) or "").strip()


def map_account_type(qbo_type: str) -> models.AccountType:
    income_types = {"Income", "Other Income"}
    expense_types = {"Cost of Goods Sold", "Expense", "Other Expense"}
    liability_types = {
        "Accounts Payable", "Credit Card", "Other Current Liability",
        "Long-term Liability", "Equity", "Other Liability",
    }
    if qbo_type in income_types:
        return models.AccountType.income
    if qbo_type in expense_types:
        return models.AccountType.expense
    if qbo_type in liability_types:
        return models.AccountType.liability
    return models.AccountType.asset


def map_payment_method(method_name: str) -> models.PaymentMethod:
    name = (method_name or "").lower()
    if any(k in name for k in ("visa", "mastercard", "amex", "discover", "credit")):
        return models.PaymentMethod.credit_card
    if any(k in name for k in ("check", "cheque", "ach", "wire")):
        return models.PaymentMethod.check
    if "cash" in name:
        return models.PaymentMethod.cash
    return models.PaymentMethod.check


def derive_invoice_status(invoice: dict) -> models.InvoiceStatus:
    total = d(invoice.get("TotalAmt", 0))
    balance = d(invoice.get("Balance", 0))
    email_status = invoice.get("EmailStatus", "NotSent")

    if total == Decimal("0"):
        return models.InvoiceStatus.paid
    if balance == Decimal("0"):
        return models.InvoiceStatus.paid
    if balance < total:
        return models.InvoiceStatus.partially_paid
    if email_status == "EmailSent":
        return models.InvoiceStatus.sent
    return models.InvoiceStatus.draft


def load_last_sync() -> Optional[str]:
    if os.path.exists(SYNC_FILE):
        with open(SYNC_FILE) as f:
            data = json.load(f)
            return data.get("last_sync")
    return None


def save_last_sync(ts: str):
    with open(SYNC_FILE, "w") as f:
        json.dump({"last_sync": ts}, f)


# ─────────────────────────────────────────────
# Import phases
# ─────────────────────────────────────────────

def import_accounts(qbo: QBOClient, db: Session, since: Optional[str], dry_run: bool):
    print("\n[1/7] Importing chart of accounts...")
    accounts = qbo.query_since("Account", since) if since else qbo.query("Account")
    created = updated = 0

    for a in accounts:
        qbo_id = str(a["Id"])
        existing = db.query(models.ChartOfAccount).filter_by(qbo_id=qbo_id).first()

        # Build account code: use AcctNum if present, else generate from Id
        code = (a.get("AcctNum") or f"QBO-{qbo_id}").strip()[:10]
        # Ensure code uniqueness when no AcctNum
        if not a.get("AcctNum"):
            code_check = db.query(models.ChartOfAccount).filter_by(code=code).first()
            if code_check and (not existing or code_check.id != existing.id):
                code = f"Q{qbo_id}"[:10]

        acct_type = map_account_type(a.get("AccountType", ""))

        if existing:
            existing.name = a["Name"]
            existing.code = code
            existing.account_type = acct_type
            existing.is_active = a.get("Active", True)
            updated += 1
        else:
            if not dry_run:
                db.add(models.ChartOfAccount(
                    qbo_id=qbo_id,
                    code=code,
                    name=a["Name"],
                    account_type=acct_type,
                    description=a.get("Description"),
                    is_active=a.get("Active", True),
                ))
            created += 1

    if not dry_run:
        db.commit()
    print(f"  Accounts: {created} created, {updated} updated")


def import_clients(qbo: QBOClient, db: Session, since: Optional[str], dry_run: bool) -> dict:
    """Returns mapping of QBO Customer Id -> DB Client id"""
    print("\n[2/7] Importing clients (customers)...")
    customers = qbo.query_since("Customer", since) if since else qbo.query("Customer")
    created = updated = 0
    qbo_to_db: dict[str, int] = {}

    for c in customers:
        qbo_id = str(c["Id"])
        display_name = c.get("DisplayName") or c.get("CompanyName") or c.get("FullyQualifiedName") or f"Client-{qbo_id}"
        company_name = c.get("CompanyName") or display_name
        email = (c.get("PrimaryEmailAddr") or {}).get("Address") or ""
        phone_obj = c.get("PrimaryPhone") or c.get("Mobile") or {}
        phone = phone_obj.get("FreeFormNumber", "")
        addr_obj = c.get("BillAddr") or {}
        given = c.get("GivenName") or ""
        family = c.get("FamilyName") or ""
        full_name = f"{given} {family}".strip() or None

        existing = db.query(models.Client).filter_by(qbo_id=qbo_id).first()

        if existing:
            existing.display_name = display_name
            existing.company_name = company_name
            existing.full_name = full_name
            existing.email = email
            existing.phone = phone
            existing.address_line1 = addr(addr_obj, "Line1")
            existing.address_line2 = addr(addr_obj, "Line2")
            existing.city = addr(addr_obj, "City")
            existing.state = addr(addr_obj, "CountrySubDivisionCode")
            existing.zip_code = addr(addr_obj, "PostalCode")
            existing.is_active = c.get("Active", True)
            updated += 1
            qbo_to_db[qbo_id] = existing.id
        else:
            if not dry_run:
                client = models.Client(
                    qbo_id=qbo_id,
                    display_name=display_name,
                    company_name=company_name,
                    full_name=full_name,
                    email=email,
                    phone=phone,
                    address_line1=addr(addr_obj, "Line1"),
                    address_line2=addr(addr_obj, "Line2"),
                    city=addr(addr_obj, "City"),
                    state=addr(addr_obj, "CountrySubDivisionCode"),
                    zip_code=addr(addr_obj, "PostalCode"),
                    is_active=c.get("Active", True),
                )
                db.add(client)
                db.flush()
                qbo_to_db[qbo_id] = client.id
            created += 1

    if not dry_run:
        db.commit()
        # Reload mapping from DB to catch pre-existing records
        for client in db.query(models.Client).filter(models.Client.qbo_id.isnot(None)):
            qbo_to_db[client.qbo_id] = client.id

    print(f"  Clients: {created} created, {updated} updated")
    return qbo_to_db


def import_invoices(qbo: QBOClient, db: Session, client_map: dict, since: Optional[str], dry_run: bool) -> dict:
    """Returns mapping of QBO Invoice Id -> DB Invoice id"""
    print("\n[3/7] Importing invoices...")
    invoices = qbo.query_since("Invoice", since) if since else qbo.query("Invoice")
    created = updated = skipped = 0
    qbo_to_db: dict[str, int] = {}

    for inv in invoices:
        qbo_id = str(inv["Id"])
        cust_qbo_id = str((inv.get("CustomerRef") or {}).get("value", ""))
        client_id = client_map.get(cust_qbo_id)

        if not client_id:
            skipped += 1
            continue

        invoice_number = inv.get("DocNumber") or f"QBO-{qbo_id}"
        total = d(inv.get("TotalAmt", 0))
        balance = d(inv.get("Balance", 0))
        amount_paid = total - balance
        created_date = parse_date(inv.get("TxnDate")) or date.today()
        due_date = parse_date(inv.get("DueDate")) or created_date
        status = derive_invoice_status(inv)

        existing = db.query(models.Invoice).filter_by(qbo_id=qbo_id).first()

        if existing:
            existing.invoice_number = invoice_number
            existing.client_id = client_id
            existing.created_date = created_date
            existing.due_date = due_date
            existing.total = total
            existing.subtotal = total
            existing.amount_paid = amount_paid
            existing.balance_due = balance
            existing.status = status
            existing.notes = inv.get("CustomerMemo", {}).get("value")
            updated += 1
            qbo_to_db[qbo_id] = existing.id

            # Rebuild line items
            if not dry_run:
                db.query(models.InvoiceLineItem).filter_by(invoice_id=existing.id).delete()
                _add_line_items(db, existing.id, inv.get("Line", []))
        else:
            if not dry_run:
                invoice = models.Invoice(
                    qbo_id=qbo_id,
                    invoice_number=invoice_number,
                    client_id=client_id,
                    created_date=created_date,
                    due_date=due_date,
                    total=total,
                    subtotal=total,
                    amount_paid=amount_paid,
                    balance_due=balance,
                    status=status,
                    notes=inv.get("CustomerMemo", {}).get("value"),
                )
                db.add(invoice)
                db.flush()
                qbo_to_db[qbo_id] = invoice.id
                _add_line_items(db, invoice.id, inv.get("Line", []))
            created += 1

        if (created + updated) % 200 == 0 and not dry_run:
            db.commit()

    if not dry_run:
        db.commit()
        for inv_rec in db.query(models.Invoice).filter(models.Invoice.qbo_id.isnot(None)):
            qbo_to_db[inv_rec.qbo_id] = inv_rec.id

    print(f"  Invoices: {created} created, {updated} updated, {skipped} skipped (unknown client)")
    return qbo_to_db


def _add_line_items(db: Session, invoice_id: int, lines: list):
    sort_order = 0
    for line in lines:
        detail_type = line.get("DetailType", "")
        if detail_type not in ("SalesItemLineDetail", "ServiceLineDetail"):
            continue
        detail = line.get(detail_type, {})
        qty = d(detail.get("Qty", 1))
        unit_price = d(detail.get("UnitPrice", 0))
        amount = d(line.get("Amount", 0))
        description = (line.get("Description") or "").strip() or (
            (detail.get("ItemRef") or {}).get("name") or "Service"
        )
        db.add(models.InvoiceLineItem(
            invoice_id=invoice_id,
            description=description[:255],
            quantity=qty,
            unit_amount=unit_price,
            amount=amount,
            sort_order=sort_order,
        ))
        sort_order += 1


def import_payments(qbo: QBOClient, db: Session, client_map: dict, invoice_map: dict, since: Optional[str], dry_run: bool):
    print("\n[4/7] Importing payments...")
    payments = qbo.query_since("Payment", since) if since else qbo.query("Payment")
    created = updated = skipped = 0

    for pmt in payments:
        qbo_id = str(pmt["Id"])
        cust_qbo_id = str((pmt.get("CustomerRef") or {}).get("value", ""))
        client_id = client_map.get(cust_qbo_id)

        if not client_id:
            skipped += 1
            continue

        # Find linked invoice via LinkedTxn
        invoice_id = None
        for linked in pmt.get("Line", []):
            for txn in linked.get("LinkedTxn", []):
                if txn.get("TxnType") == "Invoice":
                    inv_qbo_id = str(txn["TxnId"])
                    invoice_id = invoice_map.get(inv_qbo_id)
                    if invoice_id:
                        break
            if invoice_id:
                break

        if not invoice_id:
            skipped += 1
            continue

        payment_date = parse_date(pmt.get("TxnDate")) or date.today()
        amount = d(pmt.get("TotalAmt", 0))
        method_name = (pmt.get("PaymentMethodRef") or {}).get("name", "")
        method = map_payment_method(method_name)
        ref = pmt.get("PaymentRefNum") or None

        existing = db.query(models.Payment).filter_by(qbo_id=qbo_id).first()
        if existing:
            existing.payment_date = payment_date
            existing.amount = amount
            existing.method = method
            existing.reference_number = ref
            existing.client_id = client_id
            existing.invoice_id = invoice_id
            updated += 1
        else:
            if not dry_run:
                db.add(models.Payment(
                    qbo_id=qbo_id,
                    invoice_id=invoice_id,
                    client_id=client_id,
                    payment_date=payment_date,
                    amount=amount,
                    method=method,
                    reference_number=ref,
                ))
            created += 1

        if (created + updated) % 200 == 0 and not dry_run:
            db.commit()

    if not dry_run:
        db.commit()
    print(f"  Payments: {created} created, {updated} updated, {skipped} skipped (no linked invoice)")


def import_credit_memos(qbo: QBOClient, db: Session, client_map: dict, since: Optional[str], dry_run: bool):
    print("\n[5/7] Importing credit memos...")
    memos = qbo.query_since("CreditMemo", since) if since else qbo.query("CreditMemo")
    created = updated = skipped = 0

    for cm in memos:
        qbo_id = str(cm["Id"])
        cust_qbo_id = str((cm.get("CustomerRef") or {}).get("value", ""))
        client_id = client_map.get(cust_qbo_id)

        if not client_id:
            skipped += 1
            continue

        memo_number = cm.get("DocNumber") or f"CM-QBO-{qbo_id}"
        total = d(cm.get("TotalAmt", 0))
        created_date = parse_date(cm.get("TxnDate")) or date.today()
        status = models.CreditMemoStatus.applied if d(cm.get("RemainingCredit", 0)) == Decimal("0") else models.CreditMemoStatus.sent

        existing = db.query(models.CreditMemo).filter_by(qbo_id=qbo_id).first()
        if existing:
            existing.memo_number = memo_number
            existing.client_id = client_id
            existing.created_date = created_date
            existing.total = total
            existing.status = status
            updated += 1
        else:
            if not dry_run:
                db.add(models.CreditMemo(
                    qbo_id=qbo_id,
                    memo_number=memo_number,
                    client_id=client_id,
                    created_date=created_date,
                    total=total,
                    status=status,
                ))
            created += 1

    if not dry_run:
        db.commit()
    print(f"  Credit memos: {created} created, {updated} updated, {skipped} skipped")


def import_expenses(qbo: QBOClient, db: Session, since: Optional[str], dry_run: bool):
    print("\n[6/7] Importing expenses (purchases + bills)...")
    created = updated = 0

    def _upsert(qbo_id: str, expense_date: date, vendor: str, amount: Decimal, ref: Optional[str], note: Optional[str]):
        nonlocal created, updated
        existing = db.query(models.Expense).filter_by(qbo_id=qbo_id).first()
        if existing:
            existing.expense_date = expense_date
            existing.vendor = vendor
            existing.amount = amount
            existing.reference_number = ref
            existing.notes = note
            updated += 1
        else:
            if not dry_run:
                db.add(models.Expense(
                    qbo_id=qbo_id,
                    expense_date=expense_date,
                    vendor=vendor,
                    amount=amount,
                    reference_number=ref,
                    notes=note,
                ))
            created += 1

    # Purchases (credit card charges, cash, checks paid directly)
    for p in (qbo.query_since("Purchase", since) if since else qbo.query("Purchase")):
        entity = p.get("EntityRef") or {}
        vendor = entity.get("name") or "Unknown Vendor"
        _upsert(
            qbo_id=f"PUR-{p['Id']}",
            expense_date=parse_date(p.get("TxnDate")) or date.today(),
            vendor=vendor,
            amount=d(p.get("TotalAmt", 0)),
            ref=p.get("DocNumber"),
            note=p.get("PrivateNote"),
        )

    # Bills (AP items — vendor invoices owed)
    for b in (qbo.query_since("Bill", since) if since else qbo.query("Bill")):
        vendor_ref = b.get("VendorRef") or {}
        vendor = vendor_ref.get("name") or "Unknown Vendor"
        _upsert(
            qbo_id=f"BILL-{b['Id']}",
            expense_date=parse_date(b.get("TxnDate")) or date.today(),
            vendor=vendor,
            amount=d(b.get("TotalAmt", 0)),
            ref=b.get("DocNumber"),
            note=b.get("PrivateNote"),
        )

    if not dry_run:
        db.commit()
    print(f"  Expenses: {created} created, {updated} updated")


def import_journal_entries(qbo: QBOClient, db: Session, since: Optional[str], dry_run: bool):
    print("\n[7/7] Importing journal entries...")
    entries = qbo.query_since("JournalEntry", since) if since else qbo.query("JournalEntry")
    created = updated = 0

    for je in entries:
        txn_date = parse_date(je.get("TxnDate")) or date.today()
        ref = je.get("DocNumber")

        for i, line in enumerate(je.get("Line", [])):
            detail = line.get("JournalEntryLineDetail", {})
            account_ref = detail.get("AccountRef") or {}
            posting_type = detail.get("PostingType", "Debit")
            amount = d(line.get("Amount", 0))
            description = line.get("Description") or je.get("PrivateNote") or ""

            qbo_id = f"JE-{je['Id']}-{i}"
            existing = db.query(models.JournalEntry).filter_by(reference_number=qbo_id).first()

            debit = amount if posting_type == "Debit" else Decimal("0")
            credit = amount if posting_type == "Credit" else Decimal("0")
            gl_code = account_ref.get("value", "")[:10]
            gl_name = account_ref.get("name", "")[:255]

            if existing:
                existing.transaction_date = txn_date
                existing.debit = debit
                existing.credit = credit
                existing.description = description
                existing.gl_account_code = gl_code
                existing.gl_account_name = gl_name
                updated += 1
            else:
                if not dry_run:
                    db.add(models.JournalEntry(
                        transaction_date=txn_date,
                        gl_account_code=gl_code,
                        gl_account_name=gl_name,
                        debit=debit,
                        credit=credit,
                        description=description[:500] if description else None,
                        reference_number=qbo_id,
                        source="qbo_api",
                    ))
                created += 1

        if (created + updated) % 500 == 0 and not dry_run:
            db.commit()

    if not dry_run:
        db.commit()
    print(f"  Journal entries: {created} created, {updated} updated")


def truncate_all(db: Session):
    """Clear all business data tables, preserving users and company_info."""
    print("Truncating existing data...")
    tables = [
        models.JournalEntry, models.BankTransaction, models.BankReconciliation,
        models.CollectionsEvent, models.ActivityLog,
        models.Payment, models.CreditLineItem, models.CreditMemo,
        models.InvoiceLineItem, models.Invoice,
        models.BillingScheduleLineItem, models.BillingSchedule,
        models.Expense, models.ServiceCatalog, models.ChartOfAccount,
        models.Client, models.InvoiceSequence,
    ]
    for model in tables:
        db.query(model).delete()
    db.commit()
    print("  Tables cleared.")


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Import QBO data into PrecisionPros DB")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--full", action="store_true", help="Full historical import (truncates DB first)")
    mode.add_argument("--sync", action="store_true", help="Incremental sync (only new/changed records)")
    parser.add_argument("--dry-run", action="store_true", help="Read from QBO but write nothing to DB")
    parser.add_argument("--sandbox", action="store_true", help="Use QBO sandbox environment")
    args = parser.parse_args()

    dry_run = args.dry_run
    if dry_run:
        print("DRY RUN — no database writes will occur\n")

    since = None
    if args.sync:
        since = load_last_sync()
        if not since:
            print("ERROR: No previous sync found. Run --full first.")
            sys.exit(1)
        print(f"Incremental sync since: {since}\n")
    else:
        print("Full historical import\n")

    sync_start = datetime.utcnow().isoformat()

    print("Connecting to QBO API...")
    qbo = QBOClient(sandbox=args.sandbox)
    company = qbo.get_company_info()
    print(f"Connected to: {company.get('CompanyName', 'Unknown')} (Realm: {qbo.realm_id})\n")

    db = SessionLocal()
    try:
        if args.full and not dry_run:
            truncate_all(db)

        import_accounts(qbo, db, since, dry_run)
        client_map = import_clients(qbo, db, since, dry_run)
        invoice_map = import_invoices(qbo, db, client_map, since, dry_run)
        import_payments(qbo, db, client_map, invoice_map, since, dry_run)
        import_credit_memos(qbo, db, client_map, since, dry_run)
        import_expenses(qbo, db, since, dry_run)
        import_journal_entries(qbo, db, since, dry_run)

    finally:
        db.close()

    if not dry_run:
        save_last_sync(sync_start)
        print(f"\nSync timestamp saved: {sync_start}")

    print("\nImport complete.")


if __name__ == "__main__":
    main()
