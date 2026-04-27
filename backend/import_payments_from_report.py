#!/usr/bin/env python3
"""
Import payments from QBO "Invoices and Received Payments" report
Matches payments to invoices and updates invoice status.

Usage:
    python3 import_payments_from_report.py --dry-run <csv_path>
    python3 import_payments_from_report.py --commit <csv_path>
"""

import csv
import sys
import argparse
from datetime import datetime
from decimal import Decimal
from database import SessionLocal
from models import Invoice, Client, Payment, PaymentMethod, ActivityLog

# Parse arguments
parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--dry-run", action="store_true")
group.add_argument("--commit", action="store_true")
parser.add_argument("csv_path", help="Path to Invoices and Received Payments CSV export")
args = parser.parse_args()

DRY_RUN = args.dry_run
CSV_PATH = args.csv_path

def parse_date(date_str):
    if not date_str or not date_str.strip():
        return None
    try:
        return datetime.strptime(date_str.strip(), "%m/%d/%Y").date()
    except:
        return None

def clean_decimal(val):
    if not val: return Decimal("0.00")
    try:
        return Decimal(str(val).replace(",", "").strip() or "0")
    except:
        return Decimal("0.00")

def resolve_customer_name(name):
    """Map QBO customer names to accounting system names"""
    NAME_MAP = {
        "Sommer, Eric": "Arkadia Konsulting",
        "autobenefit": "Concierge Coaches",
        "sancarlosproperty": "sancarlosproperty.com",
        "ehappyhour.com, Inc.": "Timus, Inc.",
        "Atlantis Travel Agency": "Atlantis Travel Agency, Athens",
        "Contractors Parts and Supply": "Contractors Crance Co. Inc.",
        "ImageTag, Inc.": "Paymerang, LLC",
        "Net-Flow Corporation-": "Net-Flow Corporation",
        "Lombardcompany.com": "Lombard Architectural Precast Products",
        "Actuarial Work Products, Inc.": "Castevens Technologies LLC",
        "Architectural Visual Inc.": "Architectural Visual, Inc.",
        "B Factor Group": "1SEO Digital Agency",
        "CVISION Technologies": "Foxit Software",
        "CYoungConsulting.com": "C Young Consulting LLC",
        "ChristopherAugustine.com": "Christopher Augustine, LTD",
        "DesignGate Pte. Ltd.": "DesignGate pte Ltd.",
        "Dr. Adams": "Dr. D.B. Adams",
        "Fine Design Interiors": "Fine Design Interiors, Inc.",
        "International Fishing Devices": "International Fishing Devices, Inc.",
        "L F Rothchild": "Shearson Financial",
        "Lambert, Bernadette": "Bernadette/eyre",
        "MEDAxiom, LLC": "MEDAxiom, LLC.",
        "Ned Freeman": "calpreps.com",
        "Pacific Holidays, Inc.": "JC Pacific Trading Co.",
        "Paul Brahaney": "Jog A Dog",
        "Rick Long": "Rick Long - RFS Corporation",
        "Sanson Financial Solutions, LLC": "Sanson Insurance & Financial Services, LL",
        "Sparle 'n Dazzle": "Sparkle n Dazzle",
        "SteelRep": "Sun Belt Steel & Aluminum, Inc",
        "Svestka, Lura": "JTA, Inc.",
        "The Pension Studio": "Darbster Foundation",
        "Whatwatt.com/service lamp": "Whatwatt LLC",
        "Whiteent": "White Enterprises",
        "Worldfamouscomics.com": "WF Comics",
        "X-Tel Communications": "James Rahfaldt",
        "psgraphics": "PS Graphics, Inc.",
        "sonoranspaces.com": "SteamworksAZ",
        "zhost": "Ponder and Assoc",
    }

    name = name.replace("(deleted)", "").strip().rstrip(",").strip()
    return NAME_MAP.get(name, name)

# Parse the report
print(f"\nParsing Invoices and Received Payments report: {CSV_PATH}...")

payments_to_import = {}  # (customer_name, invoice_num) -> {payment_date, amount}
invoices_by_customer = {}  # customer_name -> {invoice_num: amount}

try:
    with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        next(reader)  # Skip company name
        next(reader)  # Skip date range
        next(reader)  # Skip blank

        current_customer = None
        for row in reader:
            if not row or len(row) < 2:
                continue

            # New customer section (has text in first column, no date)
            if row[0].strip() and not row[1].strip():
                current_customer = row[0].strip().rstrip(",")
                continue

            if not current_customer or not row[1].strip():
                continue

            txn_date = row[1].strip()
            txn_type = row[2].strip() if len(row) > 2 else ""
            inv_num = row[4].strip() if len(row) > 4 else ""
            amount = clean_decimal(row[5] if len(row) > 5 else "0")

            if amount <= 0:
                continue

            if txn_type == "Invoice" and inv_num:
                if current_customer not in invoices_by_customer:
                    invoices_by_customer[current_customer] = {}
                invoices_by_customer[current_customer][inv_num] = amount

            elif txn_type == "Payment":
                pmt_date = parse_date(txn_date)
                key = (current_customer, inv_num)
                if key not in payments_to_import:
                    payments_to_import[key] = {"date": pmt_date, "amount": amount}

    print(f"Found {len(payments_to_import)} payments\n")

except FileNotFoundError:
    print(f"Error: CSV file not found: {CSV_PATH}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Error reading CSV: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Match payments to invoices and create Payment records
db = SessionLocal()

try:
    inserted = 0
    skipped = 0
    not_found = {}

    for (customer_name, inv_num), pmt_data in sorted(payments_to_import.items()):
        # Resolve customer name
        resolved_name = resolve_customer_name(customer_name)

        # Find client
        client = db.query(Client).filter(Client.company_name == resolved_name).first()
        if not client:
            client = db.query(Client).filter(Client.company_name.ilike(resolved_name.lower())).first()
        if not client:
            client = db.query(Client).filter(Client.display_name.ilike(resolved_name.lower())).first()

        if not client:
            if customer_name not in not_found:
                not_found[customer_name] = []
            not_found[customer_name].append((inv_num, pmt_data["amount"]))
            skipped += 1
            continue

        # Find invoice
        invoice = None
        if inv_num:
            invoice = db.query(Invoice).filter(Invoice.invoice_number == inv_num).first()

        if not invoice:
            # Match by amount if no invoice number or invoice not found
            # Look for any invoice (even paid) that matches the amount
            invoice = db.query(Invoice).filter(
                Invoice.client_id == client.id,
                Invoice.subtotal == pmt_data["amount"]
            ).order_by(Invoice.created_date).first()

        if not invoice:
            if customer_name not in not_found:
                not_found[customer_name] = []
            not_found[customer_name].append((inv_num, pmt_data["amount"]))
            skipped += 1
            continue

        # Check if payment already exists
        existing = db.query(Payment).filter(
            Payment.invoice_id == invoice.id,
            Payment.payment_date == pmt_data["date"],
            Payment.amount == pmt_data["amount"]
        ).first()

        if existing:
            skipped += 1
            continue

        # Create payment record
        payment = Payment(
            invoice_id=invoice.id,
            client_id=client.id,
            payment_date=pmt_data["date"],
            amount=pmt_data["amount"],
            method=PaymentMethod.credit_card,  # Default to credit_card for QBO payments
            notes="Imported from QBO"
        )
        db.add(payment)

        # Update invoice status
        new_amount_paid = (invoice.amount_paid or Decimal("0.00")) + pmt_data["amount"]
        invoice.amount_paid = new_amount_paid
        invoice.balance_due = max(Decimal("0.00"), invoice.subtotal - new_amount_paid)

        if invoice.balance_due == 0:
            old_status = invoice.status
            invoice.status = "paid"

            # Log status change
            log = ActivityLog(
                entity_type="invoice",
                entity_id=invoice.id,
                client_id=client.id,
                action="status_changed",
                performed_by_id=None,
                performed_by_name="Payment Import",
                timestamp=pmt_data["date"],
                notes=f"Invoice marked as paid. Payment received: ${pmt_data['amount']}"
            )
            db.add(log)
        elif new_amount_paid > 0:
            invoice.status = "partially_paid"

        inserted += 1
        if inserted % 50 == 0 and not DRY_RUN:
            db.commit()
            print(f"  ... {inserted} payments processed")

    if DRY_RUN:
        db.rollback()
        print(f"\n📋 DRY RUN (no changes committed)")
    else:
        db.commit()
        print(f"\n✅ Import complete!")

    print(f"   Inserted: {inserted}")
    print(f"   Skipped: {skipped}")

    if not_found:
        print(f"\n   ⚠  Payments not matched ({len(not_found)}):")
        for customer in sorted(not_found.keys()):
            for inv_num, amount in not_found[customer]:
                print(f"     {customer} / {inv_num}: ${amount}")

except Exception as e:
    db.rollback()
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    raise
finally:
    db.close()

print()
