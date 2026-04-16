#!/usr/bin/env python3
"""
QBO Recurring Transactions Import Script — PrecisionPros Billing
Imports billing schedules from pasted QBO recurring transactions data.

Usage:
    python3 import_billing_schedules.py --dry-run
    python3 import_billing_schedules.py --commit
"""

import sys
import os
import argparse
from datetime import datetime
from decimal import Decimal

parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--dry-run", action="store_true")
group.add_argument("--commit", action="store_true")
args = parser.parse_args()

DRY_RUN = args.dry_run

# ── QBO Recurring Transactions (pasted from QBO UI) ──────────────────────────
# Format: customer, interval, next_date, amount
RAW_DATA = [
    ("Actuarial Work Products, Inc.",       "Every Month",    "05/01/2026", 111.50),
    ("Advanced Media Technologies",         "Every Month",    "05/01/2026",  80.00),
    ("advantage-autorepair.com",            "Every Month",    "05/01/2026",  14.95),
    ("aemi.org",                            "Every Month",    "05/01/2026", 390.00),
    ("agroresources.com",                   "Every Month",    "05/01/2026",  15.00),
    ("Alan Hoffberg",                       "Every Month",    "04/10/2026",   9.95),
    ("AMECO",                               "Every Month",    "05/01/2026",  30.00),
    ("Amir Garrison",                       "Every Month",    "05/01/2026",  20.95),
    ("antecessor.org",                      "Every Month",    "05/01/2026",  30.00),
    ("Architectural Visual Inc.",           "Every Month",    "05/01/2026",  35.00),
    ("Astrella and Rice",                   "Every Month",    "05/01/2026",  20.00),
    ("Atlantis Travel Agency",              "Every Month",    "05/01/2026", 178.00),
    ("Beach House Management LLC",          "Every Month",    "05/01/2026",  15.00),
    ("Brad Stone",                          "Every Month",    "05/01/2026",  35.00),
    ("Coin Finders",                        "Every Month",    "05/01/2026",  34.00),
    ("CreativeStartsHere.com",              "Every Month",    "05/01/2026",  24.95),
    ("criminaljusticeclub.net",             "Every Year",     "03/10/2026", 175.45),
    ("CTdiveCenter.com",                    "Every 3 Months", "06/01/2026", 145.00),
    ("CVISION Technologies",                "Every Month",    "05/01/2026", 1349.85),
    ("CYoungConsulting.com",                "Every Month",    "05/01/2026",  30.00),
    ("David Toledo",                        "Every 3 Months", "07/01/2026",  30.00),
    ("DesignGate Pte. Ltd.",                "Every Month",    "05/01/2026",  19.00),
    ("dott communications llc.",            "Every Month",    "05/01/2026",  30.00),
    ("edgepowersolutions.net",              "Every Year",     "03/10/2026", 180.00),
    ("ehappyhour.com, Inc.",                "Every Month",    "04/10/2026", 160.00),
    ("Emerge Inc.",                         "Every Month",    "03/10/2026", 1149.99),
    ("eWareness Inc.",                      "Every Month",    "03/10/2026", 639.45),
    ("Fine Design Interiors",               "Every Month",    "05/01/2026",  30.00),
    ("Fish and Game",                       "Every Month",    "04/10/2026", 179.95),
    ("Foxy Construction",                   "Every Month",    "05/01/2026",  15.00),
    ("Galaxy Photography",                  "Every Month",    "05/01/2026",  10.00),
    ("Get Green Earth(2)",                  "Every Month",    "05/01/2026",  50.00),
    ("Global Tax and Accounting",           "Every Month",    "05/01/2026",  10.00),
    ("Great Strides",                       "Every Month",    "05/01/2026",  75.00),
    ("Guardian Republic",                   "Every Month",    "05/01/2026",  76.45),
    ("Harms Historical Percussion",         "Every Month",    "05/01/2026",  25.00),
    ("Hawaii Health Guide",                 "Every Month",    "05/10/2026", 245.00),
    ("Heet Sound Products",                 "Every 3 Months", "07/01/2026", 315.00),
    ("Historical Enterprises",              "Every Month",    "05/01/2026", 128.00),
    ("Hostage Records",                     "Every Month",    "05/01/2026",  29.00),
    ("Integrated Test Corporation",         "Every Month",    "05/01/2026", 549.60),
    ("International Fishing Devices",       "Every Month",    "05/01/2026",  20.00),
    ("Koolit Truck Sales, Inc",             "Every 3 Months", "03/10/2026", 102.00),
    ("L F Rothchild",                       "Every 3 Months", "03/10/2026", 124.85),
    ("Lambert, Bernadette",                 "Every Month",    "03/10/2026", 120.00),
    ("Linda's Gourmet Latkes",              "Every Month",    "05/01/2026",  39.95),
    ("Lombard Architectural Precast Products", "Every Month", "03/10/2026",  79.95),
    ("Louisiana, LLC",                      "Every Month",    "05/01/2026",  39.95),
    ("M&R & Sons",                          "Every Month",    "05/01/2026",  24.95),
    ("Marsha Henkin",                       "Every Month",    "03/10/2026",  75.00),
    ("MEDAxiom, LLC",                       "Every 3 Months", "06/01/2026", 1919.70),
    ("Meryl Deutsch & Associates",          "Every Month",    "05/01/2026",  15.00),
    ("Michael Ahner",                       "Every Month",    "05/01/2026",  35.00),
    ("Michael Armstrong",                   "Every Month",    "05/01/2026",  38.00),
    ("Michael Legeros",                     "Every Month",    "05/01/2026", 110.00),
    ("Mike Lorts",                          "Every Month",    "03/10/2026", 830.37),
    ("Ned Freeman",                         "Every Month",    "05/01/2026", 886.00),
    ("Net-Flow Corporation",                "Every Month",    "03/10/2026", 704.45),
    ("Outer Banks Internet, Inc.",          "Every Month",    "05/01/2026",  60.00),
    ("Pacific Holidays, Inc.",              "Every Month",    "05/01/2026", 105.00),
    ("Paul Brahaney",                       "Every Month",    "05/01/2026",  78.00),
    ("psgraphics",                          "Every Month",    "05/01/2026", 168.00),
    ("Purrfurdots Ocicats",                 "Every Month",    "03/10/2026",  14.95),
    ("RE/MAX Advance Realty, Inc.",         "Every 3 Months", "07/01/2026",  68.85),
    ("Real Time Solutions of America Inc.", "Every Month",    "05/01/2026", 143.00),
    ("Relevant Arts",                       "Every Month",    "05/01/2026", 105.00),
    ("REMAX First Choice Realty",           "Every Month",    "05/10/2026", 204.95),
    ("Rich King Info. Corp. Ltd.",          "Every Month",    "05/01/2026",  65.00),
    ("Rich Masterson",                      "Every Month",    "05/01/2026",  16.25),
    ("Rick Long",                           "Every Month",    "05/01/2026",  24.95),
    ("Rocky Mountain",                      "Every 3 Months", "06/01/2026", 615.00),
    ("Rodrigue and Sons Company",           "Every Month",    "05/01/2026",  76.45),
    ("Rus Berrett",                         "Every Month",    "05/01/2026",  85.50),
    ("sancarlosproperty.com",               "Every Month",    "03/10/2026", 244.95),
    ("Service Ware Inc",                    "Every Month",    "05/01/2026", 113.97),
    ("Sharkey, Keith",                      "Every Year",     "03/10/2026",  36.00),
    ("Skiboards Superstore",                "Every Month",    "05/01/2026", 251.72),
    ("sonoranspaces.com",                   "Every Month",    "05/01/2026",  15.00),
    ("Southern Maryland Dental Society",    "Every Month",    "05/01/2026",  10.00),
    ("Sparle 'n Dazzle",                    "Every Month",    "05/01/2026", 300.00),
    ("SteamworksAZ",                        "Every Month",    "05/01/2026",  29.90),
    ("SteelRep",                            "Every Month",    "05/01/2026", 100.00),
    ("Summitt, Dave",                       "Every Month",    "05/01/2026",  61.50),
    ("Suntrans International",              "Every Month",    "05/01/2026", 124.95),
    ("Svestka, Lura",                       "Every Month",    "05/01/2026", 165.00),
    ("Target Coding",                       "Every Month",    "05/01/2026",  35.00),
    ("The Pension Studio",                  "Every Month",    "05/01/2026", 169.95),
    ("The Safety Expert",                   "Every Month",    "05/01/2026",  24.95),
    ("unionparkfresno",                     "Every Year",     "04/01/2027", 349.40),
    ("Windsor Woodworking",                 "Every 12 Months","03/01/2027", 204.40),
    ("X-Tel Communications",               "Every 3 Months", "06/01/2026", 135.00),
    ("zhost",                               "Every Month",    "05/01/2026", 310.00),
]

# ── Map QBO interval -> PrecisionPros BillingCycle ────────────────────────────
CYCLE_MAP = {
    "Every Month":     "monthly",
    "Every 3 Months":  "quarterly",
    "Every Year":      "annual",
    "Every 12 Months": "annual",
}

# ── Also map QBO customer names that differ from imported company_name ─────────
NAME_MAP = {
    "Atlantis Travel Agency":    "Atlantis Travel Agency, Athens",
    "ehappyhour.com, Inc.":      "Timus, Inc.",
    "Emerge Inc.":               "Emerge Inc.",
    "Net-Flow Corporation-":     "Net-Flow Corporation",
    "Lombardcompany.com":        "Lombard Architectural Precast Products",
    "sancarlosproperty":         "sancarlosproperty.com",
}

def resolve_name(name):
    return NAME_MAP.get(name, name)

def parse_date(val):
    try:
        return datetime.strptime(val.strip(), "%m/%d/%Y").date()
    except:
        return None

print(f"\n{'='*60}")
print(f"  QBO Billing Schedule Import — {'DRY RUN (no changes)' if DRY_RUN else '*** LIVE COMMIT ***'}")
print(f"{'='*60}\n")

schedules = []
for customer, interval, next_date, amount in RAW_DATA:
    schedules.append({
        "customer":   resolve_name(customer),
        "customer_raw": customer,
        "cycle":      CYCLE_MAP.get(interval, "monthly"),
        "next_date":  parse_date(next_date),
        "amount":     Decimal(str(amount)),
    })

print(f"Schedules to import: {len(schedules)}\n")

# Count by cycle
from collections import Counter
cycles = Counter(s["cycle"] for s in schedules)
for cycle, count in cycles.most_common():
    print(f"  {cycle:<15} {count}")
print()

print("── Schedule list ────────────────────────────────────────")
total_mrr = Decimal("0")
for s in schedules:
    mapped = f" -> {s['customer']}" if s['customer'] != s['customer_raw'] else ""
    print(f"  {s['customer_raw']:<45} {s['cycle']:<12} next={s['next_date']}  ${s['amount']:>8.2f}{mapped}")
    if s['cycle'] == 'monthly':
        total_mrr += s['amount']

print(f"\n  Monthly recurring total (MRR): ${total_mrr:,.2f}/month\n")

if DRY_RUN:
    print("✅ DRY RUN complete — no changes made.")
    print("   Run with --commit to import into the database.\n")
    sys.exit(0)

# ── Live commit ───────────────────────────────────────────────────────────────
print("── Connecting to database ────────────────────────────────")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Client, BillingSchedule, ActivityLog

db = SessionLocal()

try:
    inserted  = 0
    skipped   = 0
    not_found = []

    for s in schedules:
        client = db.query(Client).filter(
            Client.company_name == s["customer"]
        ).first()

        if not client:
            client = db.query(Client).filter(
                Client.company_name.ilike(s["customer"])
            ).first()

        if not client:
            not_found.append(f"  ✗ '{s['customer_raw']}'")
            skipped += 1
            continue

        # Skip if schedule already exists for this client
        existing = db.query(BillingSchedule).filter(
            BillingSchedule.client_id == client.id
        ).first()
        if existing:
            skipped += 1
            continue

        sched = BillingSchedule(
            client_id      = client.id,
            amount         = s["amount"],
            cycle          = s["cycle"],
            next_bill_date = s["next_date"],
            autocc_recurring = False,
            is_active      = True,
            notes          = "Imported from QuickBooks Online",
        )
        db.add(sched)
        db.flush()  # Flush to get the schedule.id

        # Create activity log entry for the imported billing schedule
        log = ActivityLog(
            entity_type="billing_schedule",
            entity_id=sched.id,
            client_id=client.id,
            action="created",
            performed_by_id=None,
            performed_by_name="QBO Import",
            notes="Imported from QuickBooks Online recurring transactions"
        )
        db.add(log)
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
