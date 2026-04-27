#!/usr/bin/env python3
"""
QBO Full Invoice + Line Item Import Script — PrecisionPros Billing
Imports all invoices from 2023+ with line items from Sales by Product/Service Detail.

Also cross-references the AR Aging Detail to set correct open balances and statuses.

Usage:
    python3 import_invoices_full.py --dry-run
    python3 import_invoices_full.py --commit
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
parser.add_argument("--sales-csv",  default="PrecisionPros_Network_Sales_by_Product_Service_Detail.csv")
parser.add_argument("--ar-csv",     default="PrecisionPros_Network_A_R_Aging_Detail_Report.csv")
args = parser.parse_args()

DRY_RUN   = args.dry_run
SALES_CSV = args.sales_csv
AR_CSV    = args.ar_csv

# ── Client name mapping (QBO invoice name -> PrecisionPros company_name) ──────
NAME_MAP = {
    # Original mappings
    "Sommer, Eric":                  "Arkadia Konsulting",
    "autobenefit":                   "Concierge Coaches",
    "sancarlosproperty":             "sancarlosproperty.com",
    "ehappyhour.com, Inc.":          "Timus, Inc.",
    "Atlantis Travel Agency":        "Atlantis Travel Agency, Athens",
    "Contractors Parts and Supply":  "Contractors Crance Co. Inc.",
    "ImageTag, Inc.":                "Paymerang, LLC",
    "Net-Flow Corporation-":         "Net-Flow Corporation",
    "Lombardcompany.com":            "Lombard Architectural Precast Products",
    # Newly discovered mismatches
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
    "sonoranspaces.com":             "SteamworksAZ",
    "zhost":                         "Ponder and Assoc",
}

def resolve_name(name):
    name = name.replace("(deleted)", "").strip().rstrip(",").strip()
    return NAME_MAP.get(name, name)

def clean_decimal(val):
    if not val: return Decimal("0.00")
    try:
        return Decimal(str(val).replace(",", "").replace('"', "").strip() or "0")
    except:
        return Decimal("0.00")

def parse_date(val):
    if not val or not val.strip(): return None
    try:
        return datetime.strptime(val.strip(), "%m/%d/%Y").date()
    except:
        return None

print(f"\n{'='*60}")
print(f"  QBO Full Invoice Import — {'DRY RUN (no changes)' if DRY_RUN else '*** LIVE COMMIT ***'}")
print(f"{'='*60}\n")

# ── Step 1: Parse Sales Detail ─────────────────────────────────────────────────
print("Parsing Sales by Product/Service Detail...")
current_product = None
invoices = defaultdict(lambda: {"customer": "", "date": None, "lines": []})

with open(SALES_CSV, newline="", encoding="utf-8-sig") as f:
    for row in csv.reader(f):
        if not row: continue
        first = row[0].strip()
        txn   = row[2].strip() if len(row) > 2 else ""

        if first and txn == "" and not any(first.startswith(x) for x in
                ["Sales", "PrecisionPros", "January", "Total", "Cash Basis", "TOTAL"]):
            current_product = first
            continue

        if first != "" or txn != "Invoice": continue
        if len(row) < 9: continue

        _, date_val, _, inv_num, customer, memo, qty, price, amount, *_ = (row + [""] * 5)[:10]
        inv_num = inv_num.strip()
        if not inv_num: continue

        inv_date = parse_date(date_val)
        if not inv_date: continue

        if invoices[inv_num]["date"] is None:
            invoices[inv_num]["customer"] = customer.strip()
            invoices[inv_num]["date"]     = inv_date

        invoices[inv_num]["lines"].append({
            "product":     current_product,
            "description": memo.strip() or current_product,
            "quantity":    clean_decimal(qty),
            "unit_price":  clean_decimal(price),
            "amount":      clean_decimal(amount),
        })

print(f"  Parsed {len(invoices)} invoices with line items")

# ── Step 2: Parse AR Aging Detail ─────────────────────────────────────────────
print("Parsing AR Aging Detail for open balances...")
open_balances = {}

with open(AR_CSV, newline="", encoding="utf-8-sig") as f:
    for row in csv.reader(f):
        if not row or len(row) < 8: continue
        blank, date_val, txn_type, num, customer, due_date, amount, open_bal = row[:8]
        if blank.strip() != "" or txn_type.strip() != "Invoice": continue
        num = num.strip()
        bal = clean_decimal(open_bal)
        if num and bal > 0:
            open_balances[num] = {"open_balance": bal, "due_date": parse_date(due_date)}

print(f"  Found {len(open_balances)} invoices with open balances\n")

# ── Step 3: Build final invoice list ──────────────────────────────────────────
records = []
skipped_deleted = 0

for inv_num, inv in sorted(invoices.items(), key=lambda x: x[1]["date"] or date.min):
    customer_raw = inv["customer"]

    if "(deleted)" in customer_raw:
        skipped_deleted += 1
        continue

    customer = resolve_name(customer_raw)
    inv_date = inv["date"]
    lines    = inv["lines"]
    subtotal = sum(l["amount"] for l in lines)
    if subtotal <= 0:
        continue

    if inv_num in open_balances:
        open_bal    = open_balances[inv_num]["open_balance"]
        due_date    = open_balances[inv_num]["due_date"] or (inv_date + timedelta(days=12))
        amount_paid = subtotal - open_bal
        status      = "sent" if amount_paid <= 0 else "partially_paid"
    else:
        open_bal    = Decimal("0.00")
        amount_paid = subtotal
        due_date    = inv_date + timedelta(days=12)
        status      = "paid"

    records.append({
        "invoice_number": inv_num,
        "customer":       customer,
        "customer_raw":   customer_raw,
        "date":           inv_date,
        "due_date":       due_date,
        "subtotal":       subtotal,
        "amount_paid":    amount_paid,
        "balance_due":    open_bal,
        "status":         status,
        "lines":          lines,
    })

from collections import Counter
status_counts = Counter(r["status"] for r in records)
year_counts   = Counter(r["date"].year for r in records)

print(f"Invoices to import:   {len(records)}")
print(f"Skipped (deleted):    {skipped_deleted}")
print()
print("── By status ─────────────────────────────────────────────")
for s, c in sorted(status_counts.items()):
    print(f"  {s:<20} {c:>5}")
print()
print("── By year ───────────────────────────────────────────────")
for y, c in sorted(year_counts.items()):
    print(f"  {y}:  {c} invoices")
print()
print(f"Total open A/R:   ${sum(r['balance_due'] for r in records):,.2f}")
print(f"Total line items: {sum(len(r['lines']) for r in records):,}")
print()

if DRY_RUN:
    print("✅ DRY RUN complete — no changes made.")
    print("   Run with --commit to import into the database.\n")
    sys.exit(0)

# ── Live commit ────────────────────────────────────────────────────────────────
print("── Connecting to database ────────────────────────────────")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Client, Invoice, InvoiceLineItem, ServiceCatalog, ActivityLog

db = SessionLocal()

try:
    inserted    = 0
    skipped_dup = 0
    skipped_nm  = 0
    not_found   = set()

    all_clients = db.query(Client).all()
    client_cache  = {c.company_name: c for c in all_clients}
    client_ilike  = {c.company_name.lower(): c for c in all_clients}
    client_display_ilike = {c.display_name.lower(): c for c in all_clients}
    client_full_ilike = {c.full_name.lower(): c for c in all_clients if c.full_name}
    service_cache = {s.name.lower(): s for s in db.query(ServiceCatalog).all()}

    for r in records:
        customer_lower = r["customer"].lower()
        client = client_cache.get(r["customer"]) or \
                 client_ilike.get(customer_lower) or \
                 client_display_ilike.get(customer_lower) or \
                 client_full_ilike.get(customer_lower)

        if not client:
            not_found.add(r["customer"])
            skipped_nm += 1
            continue

        if db.query(Invoice).filter(Invoice.invoice_number == r["invoice_number"]).first():
            skipped_dup += 1
            continue

        inv_obj = Invoice(
            invoice_number   = r["invoice_number"],
            client_id        = client.id,
            created_date     = r["date"],
            due_date         = r["due_date"],
            status           = r["status"],
            subtotal         = r["subtotal"],
            total            = r["subtotal"],
            amount_paid      = r["amount_paid"],
            balance_due      = r["balance_due"],
            previous_balance = Decimal("0.00"),
            notes            = "Imported from QuickBooks Online",
        )
        db.add(inv_obj)
        db.flush()

        # Create activity log entry for the imported invoice
        log = ActivityLog(
            entity_type="invoice",
            entity_id=inv_obj.id,
            client_id=client.id,
            action="created",
            performed_by_id=None,
            performed_by_name="QBO Import",
            timestamp=datetime.combine(inv_obj.created_date, datetime.min.time()),
            notes="Imported from QuickBooks Online"
        )
        db.add(log)

        for sort_order, line in enumerate(r["lines"]):
            svc = service_cache.get(line["product"].lower())
            db.add(InvoiceLineItem(
                invoice_id  = inv_obj.id,
                service_id  = svc.id if svc else None,
                description = line["description"][:255],
                quantity    = line["quantity"],
                unit_amount = line["unit_price"],
                amount      = line["amount"],
                sort_order  = sort_order,
            ))

        if r["balance_due"] > 0:
            client.account_balance = (client.account_balance or Decimal("0.00")) + r["balance_due"]

        inserted += 1
        if inserted % 200 == 0:
            db.commit()
            print(f"  ... {inserted} invoices committed")

    db.commit()

    print(f"\n✅ Import complete!")
    print(f"   Inserted:              {inserted}")
    print(f"   Skipped (duplicates):  {skipped_dup}")
    print(f"   Skipped (no client):   {skipped_nm}")

    if not_found:
        print(f"\n   ⚠  Clients not matched ({len(not_found)}):")
        for n in sorted(not_found):
            print(f"     ✗ '{n}'")

except Exception as ex:
    db.rollback()
    print(f"\n❌ Import FAILED — rolled back.")
    print(f"   Error: {ex}")
    import traceback; traceback.print_exc()
    raise

finally:
    db.close()

print()
