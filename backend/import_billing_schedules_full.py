#!/usr/bin/env python3
"""
QBO Billing Schedule Reconstruction Script — PrecisionPros Billing
Reconstructs billing schedules with line items from most recent invoices.
Custom/negotiated pricing is preserved from the actual invoices.
Only split/prorated lines are consolidated via CLEAN_LINES overrides.

Usage:
    python3 import_billing_schedules_full.py --dry-run
    python3 import_billing_schedules_full.py --commit
"""

import sys
import os
import argparse
import csv
from datetime import datetime, date
from decimal import Decimal
from collections import defaultdict

parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--dry-run",  action="store_true")
group.add_argument("--commit",   action="store_true")
parser.add_argument("--sales-csv", default="PrecisionPros_Network_Sales_by_Product_Service_Detail.csv")
args = parser.parse_args()

DRY_RUN   = args.dry_run
SALES_CSV = args.sales_csv

def custom_li(product, unit_price, qty=1, desc=None):
    q = Decimal(str(qty))
    p = Decimal(str(unit_price))
    return {"product": product, "description": desc or product,
            "quantity": q, "unit_price": p, "amount": p * q}

# ── CLEAN_LINES: only for invoices with split/prorated lines ──────────────────
# These consolidate duplicate product lines into single clean lines.
# Prices preserved from original invoice totals where possible.
CLEAN_LINES = {
    # Advanced Media Technologies — split into 2 lines each, consolidate to 1
    # Original: 2x Backups=$10, 2x Plesk10=$20, 2x VPS A=$50 → total $80
    "49268": [
        custom_li("Backups/Snapshots",        10.00),
        custom_li("Plesk 10 Domain License",  20.00),
        custom_li("VPS A",                    50.00),
    ],

    # Castevens Technologies LLC — 2x Plesk 10 split ($20+$6.50), 1x VPS B, 1x Extra Disc Space
    "48964": [
        custom_li("Extra Disc Space 10 GB",   10.00),
        custom_li("Plesk 10 Domain License",  20.00, qty=2),
        custom_li("VPS B",                    75.00),
    ],

    # Emerge Inc — CUSTOM NEGOTIATED PRICING
    "49234": [
        custom_li("Dedicated Server A",       185.00),
        custom_li("Dedicated Server C",       758.99),
        custom_li("Plesk 10 Domain License",   20.00),
        custom_li("Plesk Unlimited Domain License", 70.00, qty=2),
        custom_li("Remote Cloud Backups",      10.00),
    ],

    # Fish and Game — split lines, consolidate to 1x each
    "49065": [
        custom_li("Plesk 10 Domain License",  20.00),
        custom_li("Remote Cloud Backups",     20.00),
        custom_li("VPS C",                   149.95),
    ],

    # Foxit Software — 3x Dedicated Server C (intentional, catalog price)
    "49275": [custom_li("Dedicated Server C", 549.95, qty=3)],

    # Integrated Test Corporation — 49x Hosted Exchange (real qty), others clean
    "49302": [
        custom_li("Hosted Exchange Server",    9.69, qty=49),  # preserve invoice price
        custom_li("Plesk 10 Domain License",  20.00),
        custom_li("Remote Cloud Backups",     20.00),
        custom_li("VPS A",                    56.00),          # preserve invoice price
    ],

    # JTA Inc — split Business Email, consolidate
    "49257": [
        custom_li("Backups/Snapshots",        10.00),
        custom_li("Business Email (up to 5 users)", 30.00, qty=2),
        custom_li("Plesk 10 Domain License",  20.00),
        custom_li("VPS B",                    75.00),
    ],

    # MEDAxiom — 2x duplicate Backups split, consolidate
    "49191": [
        custom_li("Backups/Snapshots",        10.00, qty=6),
        custom_li("Dedicated Server A",      249.95, qty=3),
        custom_li("Dedicated Server B",      349.95, qty=3),
    ],

    # Michael Armstrong — 2x Shared Server C split
    "49316": [custom_li("Shared Server C", 19.00, qty=2)],  # $38/2 = $19 each

    # Michael Legeros — split lines
    "49307": [
        custom_li("Business Email (up to 5 users)", 7.50, qty=2),  # $15 total / 2
        custom_li("Extra Disc Space 10 GB",         10.00, qty=2),
        custom_li("VPS B",                          37.50, qty=2),  # $75 total / 2
    ],

    # Mike Lorts — remove Domain Name Registration (annual, not monthly)
    "49232": [
        custom_li("Additional IP",                   2.00),
        custom_li("Dedicated Server C",            549.95),
        custom_li("Plesk Unlimited Domain License",  70.00),
        custom_li("Remote Cloud Backups",            20.00),
        custom_li("Shared Server A",                  5.00),  # preserve invoice price
        custom_li("Virtuozzo 10 Container License", 144.00),
    ],

    # Net-Flow Corporation — split Plesk lines
    "49240": [
        custom_li("Dedicated Server C",            549.95),
        custom_li("Plesk 10 Domain License",        26.50, qty=2),  # preserve ($20+$6.50)*2
        custom_li("Plesk Unlimited Domain License",  70.00, qty=2),
        custom_li("Remote Cloud Backups",            20.00, qty=2),
    ],

    # PS Graphics — split lines
    "49309": [
        custom_li("Plesk 30 Domain License",  33.00, qty=2),
        custom_li("Remote Cloud Backups",     10.00, qty=2),  # preserve invoice price
        custom_li("VPS C",                   125.00, qty=2),  # preserve invoice price
    ],

    # Skiboards Superstore — split VPS C
    "49310": [
        custom_li("Backups/Snapshots",                10.00),
        custom_li("Business Email (up to 5 users)",   15.00),
        custom_li("Plesk 10 Domain License",          20.00),
        custom_li("VPS C",                           149.95, qty=2),  # check invoice price
    ],

    # Sparkle n Dazzle — split lines
    "49311": [
        custom_li("Backups/Snapshots",                10.00, qty=2),
        custom_li("Business Email (up to 5 users)",   15.00),
        custom_li("Plesk 10 Domain License",          20.00, qty=2),
        custom_li("VPS B",                            75.00),
        custom_li("VPS C",                           150.00),
    ],

    # aemi.org — multiple split lines
    "49161": [
        custom_li("Backups/Snapshots",                10.00, qty=3),
        custom_li("Business Email (up to 5 users)",   15.00, qty=5),
        custom_li("Extra Disc Space 10 GB",           25.00),  # preserve invoice price
        custom_li("Plesk 10 Domain License",          20.00, qty=3),
        custom_li("VPS A",                            50.00),  # preserve invoice price
        custom_li("VPS B",                            75.00, qty=2),
    ],

    # antecessor.org — 2x Business Email split
    "49294": [custom_li("Business Email (up to 5 users)", 15.00, qty=2)],

    # eWareness Inc — split Plesk lines
    "49235": [
        custom_li("Dedicated Server C",           549.95),
        custom_li("Plesk 10 Domain License",       26.50, qty=2),  # preserve ($20+$6.50)
        custom_li("Plesk 30 Domain License",       33.00, qty=2),
        custom_li("Remote Cloud Backups",          20.00),
    ],
}

# ── Recurring schedules ────────────────────────────────────────────────────────
# Format: company_name -> (cycle, next_date, source_invoice, override_lines)
# override_lines: only used for manual cases (Atlantis, Hawaii, etc.)
SCHEDULES = {
    "AMECO":                               ("monthly",   "05/01/2026", "49270", None),
    "Advanced Media Technologies":         ("monthly",   "05/01/2026", "49268", None),
    "Agro Resources":                      ("monthly",   "05/01/2026", "49292", None),
    "Alan Hoffberg":                       ("monthly",   "04/10/2026", "49251", None),
    "Amir Garrison":                       ("monthly",   "05/01/2026", "49293", None),
    "Architectural Visual, Inc.":          ("monthly",   "05/01/2026", "49271", None),
    "Astrella and Rice":                   ("monthly",   "05/01/2026", "49272", None),
    "Atlantis Travel Agency, Athens":      ("monthly",   "05/01/2026", None, [
        # Most recent invoice was $138, QBO says $178 — use invoice prices, add missing service
        custom_li("Business Email (up to 5 users)", 60.00),
        custom_li("Plesk 30 Domain License",        33.00),
        custom_li("VPS A",                          85.00),
    ]),
    "Beach House Management LLC":          ("monthly",   "05/01/2026", "49295", None),
    "Bernadette/eyre":                     ("monthly",   "03/10/2026", "49343", None),
    "Brad Stone":                          ("monthly",   "05/01/2026", "49273", None),
    "C Young Consulting LLC":              ("monthly",   "05/01/2026", "49256", None),
    "CTdiveCenter.com":                    ("quarterly", "06/01/2026", "49190", None),
    "Castevens Technologies LLC":          ("monthly",   "05/01/2026", "48964", None),
    "Coin Finders":                        ("monthly",   "05/01/2026", "49296", None),
    "CreativeStartsHere.com":              ("monthly",   "05/01/2026", "49274", None),
    "Darbster Foundation":                 ("monthly",   "05/01/2026", "49329", None),
    "David Toledo":                        ("quarterly", "07/01/2026", "49332", None),
    "DesignGate pte Ltd.":                 ("monthly",   "05/01/2026", "49277", None),
    "Emerge Inc.":                         ("monthly",   "03/10/2026", "49234", None),
    "Fine Design Interiors, Inc.":         ("monthly",   "05/01/2026", "49300", None),
    "Fish and Game":                       ("monthly",   "04/10/2026", "49065", None),
    "Foxit Software":                      ("monthly",   "05/01/2026", "49275", None),
    "Foxy Construction":                   ("monthly",   "05/01/2026", "49301", None),
    "Galaxy Photography":                  ("monthly",   "05/01/2026", "49278", None),
    "Get Green Earth(2)":                  ("monthly",   "05/01/2026", "48797", None),
    "Global Tax and Accounting":           ("monthly",   "05/01/2026", "49280", None),
    "Great Strides":                       ("monthly",   "05/01/2026", "49281", None),
    "Guardian Republic":                   ("monthly",   "05/01/2026", "49284", None),
    "Harms Historical Percussion":         ("monthly",   "05/01/2026", "49285", None),
    "Hawaii Health Guide":                 ("monthly",   "05/10/2026", None, [
        # Clean version without late fee, preserve invoice prices
        custom_li("Business Email (up to 5 users)", 30.00),
        custom_li("Plesk 10 Domain License",        20.00),
        custom_li("VPS C",                         125.00),
        custom_li("Remote Cloud Backups",           70.00),
    ]),
    "Heet Sound Products":                 ("quarterly", "07/01/2026", "49333", None),
    "Historical Enterprises":              ("monthly",   "05/01/2026", "49286", None),
    "Hostage Records":                     ("monthly",   "05/01/2026", "49287", None),
    "Integrated Test Corporation":         ("monthly",   "05/01/2026", "49302", None),
    "International Fishing Devices, Inc.": ("monthly",   "05/01/2026", "49288", None),
    "JC Pacific Trading Co.":             ("monthly",   "05/01/2026", "49318", None),
    "JTA, Inc.":                           ("monthly",   "05/01/2026", "49257", None),
    "James Rahfaldt":                      ("quarterly", "06/01/2026", "49188", None),
    "Jog A Dog":                           ("monthly",   "05/01/2026", "49303", None),
    "Key Real Estate Investments, LLC":    ("annual",    "03/10/2026", "49237", None),
    "Koolit Truck Sales, Inc":             ("quarterly", "03/10/2026", "48931", None),
    "Linda's Gourmet Latkes":              ("monthly",   "05/01/2026", "49305", None),
    "Lombard Architectural Precast Products": ("monthly","03/10/2026", "49244", None),
    "Louisiana, LLC":                      ("monthly",   "05/01/2026", None, [
        # Invoice #49212 — just Shared Server B, no one-time domain
        custom_li("Shared Server B",                24.95),
        custom_li("Business Email (up to 5 users)", 15.00),
    ]),
    "M&R & Sons":                          ("monthly",   "05/01/2026", "49213", None),
    "MEDAxiom, LLC.":                      ("quarterly", "06/01/2026", "49191", None),
    "Marsha Henkin":                       ("monthly",   "03/10/2026", "49352", None),
    "Meryl Deutsch & Associates":          ("monthly",   "05/01/2026", "49306", None),
    "Michael Ahner":                       ("monthly",   "05/01/2026", "49291", None),
    "Michael Armstrong":                   ("monthly",   "05/01/2026", "49316", None),
    "Michael Legeros":                     ("monthly",   "05/01/2026", "49307", None),
    "Mike Lorts":                          ("monthly",   "03/10/2026", "49232", None),
    "Net-Flow Corporation":                ("monthly",   "03/10/2026", "49240", None),
    "Outer Banks Internet, Inc.":          ("monthly",   "05/01/2026", "49317", None),
    "PS Graphics, Inc.":                   ("monthly",   "05/01/2026", "49309", None),
    "Ponder and Assoc":                    ("monthly",   "05/01/2026", "49259", None),
    "Purrfurdots Ocicats":                 ("monthly",   "03/10/2026", "49354", None),
    "RE/MAX Advance Realty, Inc.":         ("quarterly", "07/01/2026", "49255", None),
    "REMAX First Choice Realty":           ("monthly",   "05/10/2026", "49337", None),
    "Real Time Solutions of America Inc.": ("monthly",   "05/01/2026", "49319", None),
    "Relevant Arts":                       ("monthly",   "05/01/2026", "49320", None),
    "Rich King Info. Corp. Ltd.":          ("monthly",   "05/01/2026", "49321", None),
    "Rich Masterson":                      ("monthly",   "05/01/2026", "49322", None),
    "Rick Long - RFS Corporation":         ("monthly",   "05/01/2026", "49323", None),
    "Rocky Mountain":                      ("quarterly", "06/01/2026", "49163", None),
    "Rodrigue and Sons Company":           ("monthly",   "05/01/2026", "49324", None),
    "Rus Berrett":                         ("monthly",   "05/01/2026", "49325", None),
    "Service Ware Inc":                    ("monthly",   "05/01/2026", "49326", None),
    "Shearson Financial":                  ("quarterly", "03/10/2026", "48933", None),
    "Skiboards Superstore":                ("monthly",   "05/01/2026", "49310", None),
    "Southern Maryland Dental Society":    ("monthly",   "05/01/2026", "49327", None),
    "Sparkle n Dazzle":                    ("monthly",   "05/01/2026", "49311", None),
    "SteamworksAZ":                        ("monthly",   "05/01/2026", "49228", None),
    "Summitt, Dave":                       ("monthly",   "05/01/2026", "49276", None),
    "Sun Belt Steel & Aluminum, Inc":      ("monthly",   "05/01/2026", "49185", None),
    "Suntrans International":              ("monthly",   "05/01/2026", "49313", None),
    "Target Coding":                       ("monthly",   "05/01/2026", "49314", None),
    "The Safety Expert":                   ("monthly",   "05/01/2026", "49230", None),
    "Timus, Inc.":                         ("monthly",   "04/10/2026", None, [
        # Clean version without late fee, preserve invoice prices
        custom_li("Business Email (up to 5 users)", 30.00),
        custom_li("Business Email (up to 5 users)", 15.00),
        custom_li("Plesk 10 Domain License",        20.00),
        custom_li("VPS B",                          95.00),
    ]),
    "Windsor Woodworking":                 ("annual",    "03/01/2027", "49189", None),
    "advantage-autorepair.com":            ("monthly",   "05/01/2026", "49269", None),
    "aemi.org":                            ("monthly",   "05/01/2026", "49161", None),
    "antecessor.org":                      ("monthly",   "05/01/2026", "49294", None),
    "calpreps.com":                        ("monthly",   "05/01/2026", "49298", None),
    "criminaljusticeclub.net":             ("annual",    "03/10/2026", "49245", None),
    "dott communications llc.":            ("monthly",   "05/01/2026", "49299", None),
    "eWareness Inc.":                      ("monthly",   "03/10/2026", "49235", None),
    "edgepowersolutions.net":              ("annual",    "03/10/2026", None, [
        custom_li("Business Email (up to 5 users)", 15.00, qty=12, desc="Business Email - Annual"),
    ]),
    "sancarlosproperty.com":               ("monthly",   "03/10/2026", None, [
        # Use #49060 without domain renewal, preserve invoice prices
        custom_li("Business Email (up to 5 users)", 24.00),
        custom_li("Plesk 10 Domain License",        20.00, qty=2),
        custom_li("Remote Cloud Backups",           10.00, qty=2),
        custom_li("VPS A",                          50.00),
        custom_li("VPS B",                          75.00),
        custom_li("Web Application Firewall",       29.95),
    ]),
    "sonoranspaces.com":                   ("monthly",   "05/01/2026", "49283", None),
    "unionparkfresno":                     ("annual",    "04/01/2027", "49263", None),
}

def clean_val(v):
    try: return Decimal(str(v).replace(",","").replace('"',"").strip() or "0")
    except: return Decimal("0")

def parse_date(val):
    try: return datetime.strptime(val.strip(), "%m/%d/%Y").date()
    except: return None

print(f"\n{'='*60}")
print(f"  Billing Schedule Import — {'DRY RUN (no changes)' if DRY_RUN else '*** LIVE COMMIT ***'}")
print(f"{'='*60}\n")

# ── Parse invoice line items ───────────────────────────────────────────────────
print("Parsing Sales Detail for invoice line items...")
invoices_by_num = defaultdict(lambda: {"lines": []})
current_product = None

with open(SALES_CSV, newline="", encoding="utf-8-sig") as f:
    for row in csv.reader(f):
        if not row: continue
        first = row[0].strip()
        txn   = row[2].strip() if len(row) > 2 else ""
        if first and txn == "" and not any(first.startswith(x) for x in
                ["Sales","PrecisionPros","January","Total","Cash Basis","TOTAL"]):
            current_product = first; continue
        if first != "" or txn != "Invoice": continue
        if len(row) < 9: continue
        _, _, _, inv_num, _, memo, qty, price, amount, *_ = (row+[""]*5)[:10]
        inv_num = inv_num.strip()
        if not inv_num: continue
        invoices_by_num[inv_num]["lines"].append({
            "product":     current_product,
            "description": memo.strip() or current_product,
            "quantity":    clean_val(qty),
            "unit_price":  clean_val(price),
            "amount":      clean_val(amount),
        })

print(f"  Loaded line items for {len(invoices_by_num)} invoices\n")

# ── Build schedule records ─────────────────────────────────────────────────────
records = []
seen = set()
for company_name, (cycle, next_date_str, source_inv, override_lines) in SCHEDULES.items():
    if company_name in seen:
        continue
    seen.add(company_name)

    next_date = parse_date(next_date_str)

    if override_lines:
        lines = override_lines
    elif source_inv and source_inv in CLEAN_LINES:
        lines = CLEAN_LINES[source_inv]
    elif source_inv and source_inv in invoices_by_num:
        # Use raw invoice data — preserves all custom pricing
        raw = invoices_by_num[source_inv]["lines"]
        lines = [l for l in raw if l["product"] != "Late Fee" and l["amount"] > 0]
    else:
        lines = []

    total = sum(l["amount"] for l in lines)
    records.append({
        "company_name": company_name,
        "cycle":        cycle,
        "next_date":    next_date,
        "lines":        lines,
        "total":        total,
        "source":       source_inv or "manual",
    })

print(f"Schedules to create: {len(records)}\n")

from collections import Counter
for cycle, count in Counter(r["cycle"] for r in records).most_common():
    amt = sum(r["total"] for r in records if r["cycle"] == cycle)
    print(f"  {cycle:<12} {count:>3} clients   ${amt:>10,.2f}")

mrr = sum(r["total"] for r in records if r["cycle"] == "monthly")
print(f"\n  MRR: ${mrr:,.2f}/month")
print(f"  ARR estimate: ${mrr * 12:,.2f}/year\n")

print("── Full schedule preview ────────────────────────────────")
for r in records:
    print(f"\n  {r['company_name']:<45} {r['cycle']:<12} ${r['total']:>8.2f}  next={r['next_date']}")
    for l in r["lines"]:
        print(f"    {l['product']:<35} qty={l['quantity']}  ${l['amount']:.2f}")
print()

if DRY_RUN:
    print("✅ DRY RUN complete — no changes made.")
    print("   Run with --commit to import into the database.\n")
    sys.exit(0)

# ── Live commit ────────────────────────────────────────────────────────────────
print("── Connecting to database ────────────────────────────────")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Client, BillingSchedule, BillingScheduleLineItem, ServiceCatalog, ActivityLog

db = SessionLocal()

try:
    inserted  = 0
    skipped   = 0
    not_found = []

    client_cache  = {c.company_name: c for c in db.query(Client).all()}
    client_ilike  = {c.company_name.lower(): c for c in client_cache.values()}
    service_cache = {s.name.lower(): s for s in db.query(ServiceCatalog).all()}

    for r in records:
        client = client_cache.get(r["company_name"]) or \
                 client_ilike.get(r["company_name"].lower())

        if not client:
            not_found.append(r["company_name"])
            skipped += 1
            continue

        existing = db.query(BillingSchedule).filter(
            BillingSchedule.client_id == client.id
        ).first()
        if existing:
            skipped += 1
            continue

        sched = BillingSchedule(
            client_id         = client.id,
            amount            = r["total"],
            cycle             = r["cycle"],
            next_bill_date    = r["next_date"],
            autocc_recurring = False,
            is_active         = True,
            notes             = f"Imported from QBO — source #{r['source']}",
        )
        db.add(sched)
        db.flush()

        # Create activity log entry for the imported billing schedule
        log = ActivityLog(
            entity_type="billing_schedule",
            entity_id=sched.id,
            client_id=client.id,
            action="created",
            performed_by_id=None,
            performed_by_name="QBO Import",
            notes="Imported from QuickBooks Online billing schedules"
        )
        db.add(log)

        for sort_order, line in enumerate(r["lines"]):
            svc = service_cache.get(line["product"].lower())
            db.add(BillingScheduleLineItem(
                billing_schedule_id = sched.id,
                service_id          = svc.id if svc else None,
                description         = line["description"][:255],
                quantity            = line["quantity"],
                unit_amount         = line["unit_price"],
                amount              = line["amount"],
                sort_order          = sort_order,
            ))

        inserted += 1

    db.commit()
    print(f"\n✅ Import complete!")
    print(f"   Inserted:  {inserted}")
    print(f"   Skipped:   {skipped}")
    if not_found:
        print(f"\n   ⚠  Not matched ({len(not_found)}):")
        for n in not_found:
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
