#!/usr/bin/env python3
"""
QBO A/R Aging Detail Import Script — PrecisionPros Billing
Imports open invoices from QBO A/R Aging Detail CSV into the invoices table.

Usage:
    python3 import_invoices.py --dry-run      # Preview only, no DB changes
    python3 import_invoices.py --commit       # Actually insert into DB

Place this script in ~/accounting/backend/ and run from there.
"""

import sys
import os
import argparse
import csv
from datetime import datetime, date
from decimal import Decimal

# ── Parse args ────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Import QBO open invoices into PrecisionPros")
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--dry-run", action="store_true", help="Preview import, no DB writes")
group.add_argument("--commit",  action="store_true", help="Actually write to database")
parser.add_argument("--csv", default="PrecisionPros_Network_A_R_Aging_Detail_Report.csv",
                    help="Path to AR Aging Detail CSV")
args = parser.parse_args()

DRY_RUN = args.dry_run
CSV_PATH = args.csv

# Only import invoices from this year onward
CUTOFF_YEAR = 2023

# ── Name mapping: QBO invoice name -> PrecisionPros company_name ──────────────
# These are clients where QBO used a different name on invoices than the
# company name we imported from the customer list.
NAME_MAP = {
    "Sommer, Eric":               "Arkadia Konsulting",
    "autobenefit":                "Concierge Coaches",
    "sancarlosproperty":          "sancarlosproperty.com",
    "ehappyhour.com, Inc.":       "Timus, Inc.",
    "Atlantis Travel Agency":     "Atlantis Travel Agency, Athens",
    "Contractors Parts and Supply": "Contractors Crance Co. Inc.",
    "ImageTag, Inc.":             "Paymerang, LLC",
    "Net-Flow Corporation-":      "Net-Flow Corporation",
    "Lombardcompany.com":         "Lombard Architectural Precast Products",
}

print(f"\n{'='*60}")
print(f"  QBO Invoice Import — {'DRY RUN (no changes)' if DRY_RUN else '*** LIVE COMMIT ***'}")
print(f"  Importing invoices from {CUTOFF_YEAR} onward only")
print(f"{'='*60}\n")

# ── Helpers ───────────────────────────────────────────────────────────────────
def clean_money(val):
    if not val or val.strip() == "":
        return Decimal("0.00")
    cleaned = val.strip().replace("$", "").replace(",", "").replace('"', "")
    try:
        return Decimal(cleaned)
    except:
        return Decimal("0.00")

def parse_date(val):
    if not val or val.strip() == "":
        return None
    try:
        return datetime.strptime(val.strip(), "%m/%d/%Y").date()
    except:
        return None

def resolve_customer(name):
    """Map QBO customer name to PrecisionPros company_name."""
    return NAME_MAP.get(name, name)

# ── Parse CSV ─────────────────────────────────────────────────────────────────
with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
    reader = csv.reader(f)
    rows = list(reader)

invoices_raw = []
skipped_old  = []
skipped_types = {}

for row in rows:
    if len(row) < 8:
        continue
    blank, date_val, txn_type, num, customer, due_date, amount, open_bal = row[:8]

    if blank.strip() != "":
        continue

    txn_type = txn_type.strip()
    if not txn_type:
        continue

    if txn_type != "Invoice":
        skipped_types[txn_type] = skipped_types.get(txn_type, 0) + 1
        continue

    open_balance = clean_money(open_bal)
    if open_balance <= 0:
        continue

    inv_date = parse_date(date_val)

    if inv_date and inv_date.year < CUTOFF_YEAR:
        skipped_old.append(f"  #{num:<8} {customer:<40} due={parse_date(due_date)}  open=${open_balance:.2f}")
        continue

    invoices_raw.append({
        "date":         inv_date,
        "invoice_num":  num.strip(),
        "customer_raw": customer.strip(),
        "customer":     resolve_customer(customer.strip()),
        "due_date":     parse_date(due_date),
        "amount":       clean_money(amount),
        "open_balance": open_balance,
    })

print(f"Importing: {len(invoices_raw)} invoices (2023+)")
print(f"Skipping:  {len(skipped_old)} invoices (pre-{CUTOFF_YEAR})\n")

print("── Invoices to import ───────────────────────────────────")
total_open = Decimal("0.00")
for inv in invoices_raw:
    mapped = f" -> {inv['customer']}" if inv['customer'] != inv['customer_raw'] else ""
    age = (date.today() - inv["due_date"]).days if inv["due_date"] else "?"
    print(f"  #{inv['invoice_num']:<8} {inv['customer_raw']:<40}{mapped}")
    print(f"           due={inv['due_date']}  open=${inv['open_balance']:>10.2f}  ({age} days)")
    total_open += inv["open_balance"]

print(f"\n  TOTAL OPEN A/R: ${total_open:,.2f}\n")

if DRY_RUN:
    print("✅ DRY RUN complete — no changes made.")
    print("   Run with --commit to import into the database.\n")
    sys.exit(0)

# ── Live commit ───────────────────────────────────────────────────────────────
print("── Connecting to database ────────────────────────────────")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Client, Invoice, ActivityLog
from datetime import datetime

db = SessionLocal()

try:
    inserted  = 0
    skipped   = 0
    not_found = []

    for inv in invoices_raw:
        # Find matching client
        client = db.query(Client).filter(
            Client.company_name == inv["customer"]
        ).first()

        if not client:
            client = db.query(Client).filter(
                Client.company_name.ilike(inv["customer"])
            ).first()

        if not client:
            not_found.append(f"  ✗ #{inv['invoice_num']} — client not found: '{inv['customer']}' (QBO: '{inv['customer_raw']}')")
            skipped += 1
            continue

        # Skip duplicates
        existing = db.query(Invoice).filter(
            Invoice.invoice_number == inv["invoice_num"]
        ).first()
        if existing:
            skipped += 1
            continue

        invoice_obj = Invoice(
            invoice_number   = inv["invoice_num"],
            client_id        = client.id,
            created_date     = inv["date"] or date.today(),
            due_date         = inv["due_date"] or date.today(),
            status           = "sent",
            subtotal         = inv["amount"],
            total            = inv["amount"],
            amount_paid      = inv["amount"] - inv["open_balance"],
            balance_due      = inv["open_balance"],
            previous_balance = Decimal("0.00"),
            notes            = "Imported from QuickBooks Online",
        )

        db.add(invoice_obj)
        db.flush()  # Flush to get the invoice.id

        # Create activity log entry for the imported invoice
        log = ActivityLog(
            entity_type="invoice",
            entity_id=invoice_obj.id,
            client_id=client.id,
            action="created",
            performed_by_id=None,
            performed_by_name="QBO Import",
            timestamp=datetime.combine(invoice_obj.created_date, datetime.min.time()),
            notes="Imported from QuickBooks Online"
        )
        db.add(log)

        # Update client account_balance
        client.account_balance = (client.account_balance or Decimal("0.00")) + inv["open_balance"]

        inserted += 1

    db.commit()

    print(f"\n✅ Import complete!")
    print(f"   Inserted:  {inserted}")
    print(f"   Skipped:   {skipped}")

    if not_found:
        print(f"\n   ⚠  Clients not matched ({len(not_found)}):")
        for m in not_found:
            print(m)

except Exception as ex:
    db.rollback()
    print(f"\n❌ Import FAILED — rolled back.")
    print(f"   Error: {ex}")
    raise

finally:
    db.close()

print()
