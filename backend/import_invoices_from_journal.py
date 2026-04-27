#!/usr/bin/env python3
"""
QBO Journal-Based Invoice + Line Item Import Script — PrecisionPros Billing
Imports all invoices from the Journal report, which captures complete invoice
and line item data that the Sales by Product/Service Detail report misses.

This is more reliable than import_invoices_full.py because:
- Journal report has ALL invoices (including those missing from Sales Detail)
- Line items are captured directly from accounting entries
- No filtering by report type that excludes certain invoices

Usage:
    python3 import_invoices_from_journal.py --dry-run
    python3 import_invoices_from_journal.py --commit
"""

import sys
import os
import argparse
import csv
from datetime import datetime, date, timedelta
from decimal import Decimal
from collections import defaultdict

parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--dry-run",  action="store_true")
group.add_argument("--commit",   action="store_true")
parser.add_argument("--journal-csv", default="PrecisionPros_Network_Journal.csv")
parser.add_argument("--ar-csv",      default="PrecisionPros_Network_A_R_Aging_Detail_Report.csv")
args = parser.parse_args()

DRY_RUN      = args.dry_run
JOURNAL_CSV  = args.journal_csv
AR_CSV       = args.ar_csv

# ── Client name mapping (QBO name -> PrecisionPros company_name) ──────────────
NAME_MAP = {
    "Sommer, Eric":                  "Arkadia Konsulting",
    "autobenefit":                   "Concierge Coaches",
    "sancarlosproperty":             "sancarlosproperty.com",
    "ehappyhour.com, Inc.":          "Timus, Inc.",
    "Atlantis Travel Agency":        "Atlantis Travel Agency, Athens",
    "Contractors Parts and Supply":  "Contractors Crance Co. Inc.",
    "ImageTag, Inc.":                "Paymerang, LLC",
    "Net-Flow Corporation-":         "Net-Flow Corporation",
    "Lombardcompany.com":            "Lombard Architectural Precast Products",
    "Actuarial Work Products, Inc.": "Castevens Technologies LLC",
    "Architectural Visual Inc.":     "Architectural Visual, Inc.",
    "B Factor Group":                "1SEO Digital Agency",
    "CVISION Technologies":          "Foxit Software",
    "CYoungConsulting.com":          "C Young Consulting LLC",
    "ChristopherAugustine.com":      "Christopher Augustine, LTD",
    "DesignGate Pte. Ltd.":          "DesignGate pte Ltd.",
    "Dr. Adams":                     "Dr. D.B. Adams",
    "Eternallygreen.com":            "Integrity Landscaping",
    "Fine Design Interiors":         "Fine Design Interiors, Inc.",
    "Hearnelake":                    "Hearne Lake Operations Ltd",
    "International Fishing Devices": "International Fishing Devices, Inc.",
    "L F Rothchild":                 "Shearson Financial",
    "Lambert, Bernadette":           "Bernadette/eyre",
    "MEDAxiom, LLC":                 "MEDAxiom, LLC.",
    "Ned Freeman":                   "calpreps.com",
    "Newmedia":                      "New Media Sales & Management Co. Ltd.",
    "Pacific Holidays, Inc.":        "JC Pacific Trading Co.",
    "Paul Brahaney":                 "Jog A Dog",
    "Peterson-mfg.com":              "Peterson Manufacturing Co.",
    "Preserve  Resort HOA?":         "Preserve Resort HOA?",
    "Rick Long":                     "Rick Long - RFS Corporation",
    "Robyn":                         "Robyn Glazner",
    "Sanson Financial Solutions, LLC": "Sanson Insurance & Financial Services, LL",
    "Serenity Canine Retreat":       "Serentiy Canine Retreat",
    "Sharkey, Keith":                "Key Real Estate Investments, LLC",
    "Sparle 'n Dazzle":              "Sparkle n Dazzle",
    "SteelRep":                      "Sun Belt Steel & Aluminum, Inc",
    "Svestka, Lura":                 "JTA, Inc.",
    "The Pension Studio":            "Darbster Foundation",
    "Tires to Go":                   "Tires2go Inc.",
    "Whatwatt.com/service lamp":     "Whatwatt LLC",
    "Whiteent":                      "White Enterprises",
    "Worldfamouscomics.com":         "WF Comics",
    "X-Tel Communications":          "James Rahfaldt",
    "Zhongwen":                      "Zhongwen.com",
    "aeroware":                      "Aero Wear",
    "agroresources.com":             "Agro Resources",
    "bingobuddies":                  "Soleau software",
    "druckers.com":                  "Druckers",
    "kimm.org":                      "David Kimm Fesler LTD",
    "peoplesourceonline":            "Peoplesource LLC",
    "platypuscreative":              "Platypus Creative",
    "psgraphics":                    "PS Graphics, Inc.",
    "zhost":                         "Ponder and Assoc",
}

def resolve_name(name):
    name = name.replace("(deleted)", "").strip().rstrip(",").strip()
    return NAME_MAP.get(name, name)

def extract_quantity_from_description(description, amount):
    """
    Try to extract quantity from description patterns.
    Returns (quantity, unit_amount) or (Decimal("1"), amount) if no pattern found.

    Patterns:
    - "12 months" → qty=12, unit_amount=amount/12
    - "$X/month - 5/1-7/31/2023" → qty=3 (months), unit_amount=$X
    - "X users" → qty=X, unit_amount=amount/X
    - "$X/month" (assume 12 months for annual) → qty=12, unit_amount=$X
    """
    import re

    desc = description.lower()
    amount_decimal = Decimal(str(amount))

    # Pattern: "X months" or "X month"
    match = re.search(r'(\d+)\s*months?', desc)
    if match:
        qty = Decimal(match.group(1))
        unit_amt = (amount_decimal / qty).quantize(Decimal("0.01"))
        return qty, unit_amt

    # Pattern: "$X/month - start_date-end_date" → calculate months from dates
    date_match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})\s*-\s*(\d{1,2})/(\d{1,2})/(\d{4})', desc)
    if date_match:
        from datetime import date as date_type
        try:
            start = date_type(int(date_match.group(3)), int(date_match.group(1)), int(date_match.group(2)))
            end = date_type(int(date_match.group(6)), int(date_match.group(4)), int(date_match.group(5)))
            days = (end - start).days
            months = max(1, round(days / 30))  # Approximate months

            # Extract price per month
            price_match = re.search(r'\$([0-9.]+)\s*(?:/|per)\s*month', desc)
            if price_match:
                unit_amt = Decimal(price_match.group(1))
                return Decimal(months), unit_amt
        except:
            pass

    # Pattern: "X users" or "X seats"
    match = re.search(r'(\d+)\s*(?:users?|seats?|mailboxes?)', desc)
    if match:
        qty = Decimal(match.group(1))
        unit_amt = (amount_decimal / qty).quantize(Decimal("0.01")) if qty > 0 else amount_decimal
        return qty, unit_amt

    # Pattern: "$X/month" (assume 12 months for annual)
    match = re.search(r'\$([0-9.]+)\s*(?:/|per)\s*month', desc)
    if match:
        unit_amt = Decimal(match.group(1))
        qty = (amount_decimal / unit_amt).quantize(Decimal("0.0001")) if unit_amt > 0 else Decimal("1")
        # Only use this if qty makes sense (not > 36 months)
        if 0 < qty <= 36:
            return qty, unit_amt

    # No pattern found, use default
    return Decimal("1"), amount_decimal

def clean_decimal(val):
    if not val:
        return Decimal("0.00")
    try:
        return Decimal(str(val).replace(",", "").replace('"', "").strip() or "0")
    except:
        return Decimal("0.00")

def parse_date(val):
    if not val:
        return None
    try:
        return datetime.strptime(str(val).strip(), "%m/%d/%Y").date()
    except:
        return None

def parse_journal_csv(csv_path):
    """
    Parse the Journal CSV to extract invoices and line items.

    Format:
    - Row 1-3: Headers
    - Row 4: blank
    - Data rows with blank first column
    - Rows with non-blank first column = section headers/totals

    Each invoice appears as:
    - AR line: blank, date, Invoice, num, customer, blank, Accounts Receivable, amount, blank
    - Item lines: blank, date, Invoice, num, customer, description, account, blank, amount
    - Total line: (non-blank first col), blank...

    Note: Handles duplicate invoice numbers from QB Desktop + QBO (different customers).
    Uses (invoice_number, customer) as composite key during parsing.
    """
    invoices = {}  # (invoice_number, customer) -> {customer, date, amount, line_items: []}
    current_invoice_key = None

    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        for row_num, row in enumerate(reader):
            if row_num < 4:  # Skip headers
                continue

            if not row or not any(row):  # Skip empty rows
                continue

            first_col = (row[0] if row else "").strip()

            # Skip section headers (non-blank first column that aren't invoice data)
            if first_col and first_col != "":
                current_invoice_key = None
                continue

            # Check if this is an invoice row (blank first column, has Num in col 4)
            if len(row) < 5:
                continue

            txn_type = (row[2] if len(row) > 2 else "").strip()
            inv_num = (row[3] if len(row) > 3 else "").strip()
            customer = (row[4] if len(row) > 4 else "").strip()
            memo = (row[5] if len(row) > 5 else "").strip()
            account = (row[6] if len(row) > 6 else "").strip()
            debit = (row[7] if len(row) > 7 else "").strip()
            credit = (row[8] if len(row) > 8 else "").strip()
            txn_date = (row[1] if len(row) > 1 else "").strip()

            # Skip non-invoices
            if txn_type != "Invoice":
                continue

            if not inv_num:
                continue

            # AR line (has "Accounts Receivable" in account field)
            if account == "Accounts Receivable":
                amount = clean_decimal(debit) if debit else clean_decimal(credit)
                resolved_customer = resolve_name(customer)
                # Use composite key to handle duplicate invoice numbers (QB Desktop + QBO)
                current_invoice_key = (inv_num, resolved_customer)
                invoices[current_invoice_key] = {
                    "customer": resolved_customer,
                    "date": parse_date(txn_date),
                    "amount": amount,
                    "line_items": [],
                }
            # Line item (has description/account, amount in debit/credit)
            elif current_invoice_key and (memo or account) and (debit or credit):
                # Skip zero-amount lines and empty descriptions
                # In Journal format:
                # - Debit = amount to subtract (e.g., discounts, credits)
                # - Credit = amount to add
                if debit:
                    amount = -clean_decimal(debit)  # Negative for debits
                else:
                    amount = clean_decimal(credit)  # Positive for credits

                if amount == 0:
                    continue
                if not memo and not account:
                    continue

                description = memo if memo else account

                invoices[current_invoice_key]["line_items"].append({
                    "description": description,
                    "amount": amount,
                    "account": account,
                })

    return invoices

def parse_ar_aging_csv(csv_path):
    """Parse A/R Aging Detail to get open balances and due dates."""
    ar_data = {}  # invoice_number -> {due_date, open_balance}

    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        for row_num, row in enumerate(reader):
            if row_num < 6:  # Skip headers
                continue

            if not row or len(row) < 8:
                continue

            blank = (row[0] if row else "").strip()
            txn_type = (row[2] if len(row) > 2 else "").strip()
            inv_num = (row[3] if len(row) > 3 else "").strip()
            due_date = (row[5] if len(row) > 5 else "").strip()
            open_balance = (row[7] if len(row) > 7 else "").strip()

            # Only process Invoice rows
            if blank.strip() != "" or txn_type != "Invoice":
                continue

            if not inv_num:
                continue

            ar_data[inv_num] = {
                "due_date": parse_date(due_date),
                "open_balance": clean_decimal(open_balance),
            }

    return ar_data

def parse_invoice_list_csv(csv_path):
    """Parse Invoice List to get due dates for ALL invoices (open and closed)."""
    invoice_list_data = {}  # invoice_number -> {due_date}

    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        for row_num, row in enumerate(reader):
            # Skip header rows (0-3)
            if row_num < 4:
                continue

            if not row or len(row) < 6:
                continue

            txn_type = (row[1] if len(row) > 1 else "").strip()
            inv_num = (row[2] if len(row) > 2 else "").strip()
            due_date_str = (row[5] if len(row) > 5 else "").strip()

            # Only process Invoice rows
            if txn_type != "Invoice" or not inv_num:
                continue

            due_date = parse_date(due_date_str)
            if due_date:
                invoice_list_data[inv_num] = {"due_date": due_date}

    return invoice_list_data

print(f"\n{'='*70}")
print(f"  QBO Journal-Based Invoice Import")
print(f"  {'DRY RUN (no changes)' if DRY_RUN else '*** LIVE COMMIT ***'}")
print(f"{'='*70}\n")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
from models import Invoice, InvoiceLineItem, Client, ActivityLog
from datetime import datetime

db = SessionLocal()

try:
    # Parse CSV files
    print(f"Loading Journal CSV: {JOURNAL_CSV}")
    invoices = parse_journal_csv(JOURNAL_CSV)
    print(f"Found {len(invoices)} invoices\n")

    # Invoice List is the primary source for due dates (has all invoices, not just open ones)
    print(f"Loading Invoice List CSV for due dates...")
    import glob
    invoice_list_files = glob.glob("PrecisionPros_Network_Invoice_List*.csv")
    invoice_list_data = {}
    if invoice_list_files:
        invoice_list_csv = invoice_list_files[0]
        print(f"Using: {invoice_list_csv}")
        invoice_list_data = parse_invoice_list_csv(invoice_list_csv)
        print(f"Found {len(invoice_list_data)} invoices with due dates\n")
    else:
        print("  ⚠ Invoice List CSV not found, will fall back to AR Aging\n")

    print(f"Loading AR Aging CSV: {AR_CSV}")
    ar_data = parse_ar_aging_csv(AR_CSV)
    print(f"Found {len(ar_data)} open invoices\n")

    # Get all existing clients with multiple lookup keys
    all_clients = db.query(Client).all()
    clients = {c.company_name: c for c in all_clients}
    clients_by_display = {c.display_name: c for c in all_clients}
    clients_by_display_lower = {c.display_name.lower(): c for c in all_clients}
    clients_by_full_lower = {c.full_name.lower(): c for c in all_clients if c.full_name}
    print(f"Loaded {len(all_clients)} clients from database\n")

    # Import invoices
    print("─" * 70)
    print("IMPORTING INVOICES")
    print("─" * 70 + "\n")

    imported = 0
    skipped = 0
    errors = 0
    unmatched_customers = set()
    duplicate_invoices = []  # Track duplicate invoice numbers for logging

    for (inv_num, customer_name) in sorted(invoices.keys(), key=lambda x: (int(x[0]) if x[0].isdigit() else 0, x[1])):
        inv_data = invoices[(inv_num, customer_name)]

        # Check if customer exists (try multiple lookup methods)
        customer_lower = customer_name.lower()
        client = (clients.get(customer_name) or
                  clients_by_display.get(customer_name) or
                  clients_by_display_lower.get(customer_lower) or
                  clients_by_full_lower.get(customer_lower))

        if not client:
            unmatched_customers.add(customer_name)
            skipped += 1
            continue

        # Get due date: Primary source is Invoice List (has all invoices)
        # Fallback: AR Aging (only has open invoices), then default +12 days
        due_date = None
        if inv_num in invoice_list_data:
            due_date = invoice_list_data[inv_num].get("due_date")

        # If not in Invoice List, try AR Aging
        if not due_date:
            ar = ar_data.get(inv_num, {})
            due_date = ar.get("due_date")
            open_balance = ar.get("open_balance", Decimal("0.00"))
        else:
            ar = ar_data.get(inv_num, {})
            open_balance = ar.get("open_balance", Decimal("0.00"))

        # Set status based on open balance
        if open_balance > 0:
            status = "sent"  # Unpaid
        else:
            status = "paid"  # No open balance

        amount_paid = inv_data["amount"] - open_balance

        # Create invoice
        invoice = Invoice(
            invoice_number=inv_num,
            client_id=client.id,
            created_date=inv_data["date"] or date.today(),
            due_date=due_date or (inv_data["date"] + timedelta(days=12)) if inv_data["date"] else date.today(),
            subtotal=inv_data["amount"],
            total=inv_data["amount"],
            amount_paid=max(Decimal("0"), amount_paid),
            balance_due=open_balance,
            status=status,
        )

        # Track if this is a duplicate invoice number (different customer)
        existing = db.query(Invoice).filter(Invoice.invoice_number == inv_num).first()
        if existing:
            duplicate_invoices.append(f"  #{inv_num}: {existing.client.company_name} → {customer_name}")

        # Add line items
        for line in inv_data["line_items"]:
            # Extract quantity from description if possible
            qty, unit_amt = extract_quantity_from_description(line["description"], line["amount"])

            line_item = InvoiceLineItem(
                invoice=invoice,
                description=line["description"][:255],  # Truncate to field length
                quantity=qty,
                unit_amount=unit_amt,
                amount=line["amount"],
            )
            invoice.line_items.append(line_item)

        if not DRY_RUN:
            db.add(invoice)
            db.flush()

            # Create activity log entry for the imported invoice
            log = ActivityLog(
                entity_type="invoice",
                entity_id=invoice.id,
                client_id=client.id,
                action="created",
                performed_by_id=None,
                performed_by_name="QBO Import",
                timestamp=datetime.combine(invoice.created_date, datetime.min.time()),
                notes="Imported from QuickBooks Online Journal"
            )
            db.add(log)
            db.commit()

        imported += 1

        # Batch commit every 200 invoices
        if imported % 200 == 0:
            print(f"  Imported {imported} invoices...")

    print(f"\n✓ Imported {imported} invoices")
    print(f"✓ Skipped {skipped} invoices (customer not found)")

    if duplicate_invoices:
        print(f"\n⚠ Duplicate invoice numbers detected (QB Desktop + QBO):")
        for info in duplicate_invoices[:10]:
            print(info)
        if len(duplicate_invoices) > 10:
            print(f"  ... and {len(duplicate_invoices) - 10} more")

    if unmatched_customers:
        print(f"\nClients not matched ({len(unmatched_customers)}):")
        for name in sorted(unmatched_customers)[:20]:
            print(f"  - {name}")
        if len(unmatched_customers) > 20:
            print(f"  ... and {len(unmatched_customers) - 20} more")

    print(f"\n{'='*70}\n")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

finally:
    db.close()
