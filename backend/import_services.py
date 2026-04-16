#!/usr/bin/env python3
"""
QBO Product/Service List Import Script — PrecisionPros Billing
Imports services from QBO ProductServiceList CSV into the service_catalog table.

Usage:
    python3 import_services.py --dry-run
    python3 import_services.py --commit
"""

import sys
import os
import argparse
import csv
from decimal import Decimal

parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--dry-run", action="store_true")
group.add_argument("--commit", action="store_true")
parser.add_argument("--csv", default="ProductServiceList__9341456449516862_04_13_2026.csv")
args = parser.parse_args()

DRY_RUN = args.dry_run
CSV_PATH = args.csv

# ── Map QBO Income Account -> PrecisionPros category ─────────────────────────
CATEGORY_MAP = {
    "Web Hosting":               "Web Hosting",
    "Managed Servers":           "Managed Servers",
    "Email Hosting":             "Email Hosting",
    "Domain Name Registrations": "Domain Registrations",
    "Web Programming":           "Programming",
    "Services":                  "General",
    "Uncategorized Income {23}": "General",
}

# Skip these — internal QBO payment discount items, not real services
SKIP_PREFIXES = ["PmntDiscount_"]
SKIP_NAMES    = ["credit", "migration", "Services"]  # zero-value placeholders

print(f"\n{'='*60}")
print(f"  QBO Service Catalog Import — {'DRY RUN (no changes)' if DRY_RUN else '*** LIVE COMMIT ***'}")
print(f"{'='*60}\n")

def clean_price(val):
    if not val or val.strip() == "":
        return Decimal("0.00")
    try:
        return Decimal(val.strip().replace(",", ""))
    except:
        return Decimal("0.00")

# ── Parse CSV (has "Table 1" header row to skip) ──────────────────────────────
services_raw = []
skipped      = []

with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f, fieldnames=[
        "name", "sales_description", "sku", "type",
        "price", "income_account", "purchase_description",
        "purchase_cost", "expense_account"
    ])
    for i, row in enumerate(reader):
        if i == 0:  # "Table 1"
            continue
        if i == 1:  # header row
            continue

        name = row["name"].strip()
        price = clean_price(row["price"])
        income_account = row["income_account"].strip()

        # Skip internal/junk entries
        if any(name.startswith(p) for p in SKIP_PREFIXES):
            skipped.append(f"  (internal)  {name}")
            continue
        if name in SKIP_NAMES:
            skipped.append(f"  (placeholder) {name}")
            continue

        description = row["sales_description"].strip() or None
        category = CATEGORY_MAP.get(income_account, "General")

        services_raw.append({
            "name":        name,
            "description": description,
            "price":       price,
            "category":    category,
            "income_acct": income_account,
        })

print(f"Services to import: {len(services_raw)}")
print(f"Skipped:            {len(skipped)}\n")

if skipped:
    print("── Skipped ──────────────────────────────────────────────")
    for s in skipped:
        print(s)
    print()

print("── Services to import ───────────────────────────────────")
for s in services_raw:
    print(f"  {s['name']:<45} ${s['price']:>8.2f}   [{s['category']}]")
print()

if DRY_RUN:
    print("✅ DRY RUN complete — no changes made.")
    print("   Run with --commit to import into the database.\n")
    sys.exit(0)

# ── Live commit ───────────────────────────────────────────────────────────────
print("── Connecting to database ────────────────────────────────")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import ServiceCatalog, ChartOfAccount

db = SessionLocal()

try:
    inserted = 0
    skipped_db = 0

    # Cache chart of accounts
    coa_cache = {c.name.lower(): c for c in db.query(ChartOfAccount).all()}

    for s in services_raw:
        # Skip duplicates
        from models import ServiceCatalog as SC
        existing = db.query(SC).filter(SC.name == s["name"]).first()
        if existing:
            skipped_db += 1
            continue

        # Try to find matching income account
        coa = coa_cache.get(s["income_acct"].lower())
        if not coa:
            for key, val in coa_cache.items():
                if s["income_acct"].lower() in key:
                    coa = val
                    break

        svc = ServiceCatalog(
            name              = s["name"],
            description       = s["description"],
            default_amount    = s["price"],
            default_cycle     = "monthly",
            category          = s["category"],
            income_account_id = coa.id if coa else None,
            is_active         = True,
        )
        db.add(svc)
        inserted += 1

    db.commit()
    print(f"\n✅ Import complete!")
    print(f"   Inserted: {inserted}")
    print(f"   Skipped (duplicates): {skipped_db}\n")

except Exception as ex:
    db.rollback()
    print(f"\n❌ Import FAILED — rolled back.")
    print(f"   Error: {ex}")
    raise

finally:
    db.close()
