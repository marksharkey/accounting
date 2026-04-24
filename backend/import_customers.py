#!/usr/bin/env python3
"""
QBO Customer Import Script — PrecisionPros Billing
Imports Customers.csv (converted from QBO Customers.xls) into the clients table.

Usage:
    python3 import_customers.py --dry-run      # Preview only, no DB changes
    python3 import_customers.py --commit       # Actually insert into DB
"""

import sys
import argparse
import pandas as pd

# ── Parse args ────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Import QBO customers into PrecisionPros")
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--dry-run", action="store_true", help="Preview import, no DB writes")
group.add_argument("--commit",  action="store_true", help="Actually write to database")
parser.add_argument("--csv", default="Customers.csv", help="Path to exported CSV (default: Customers.csv)")
args = parser.parse_args()

DRY_RUN = args.dry_run
CSV_PATH = args.csv

# ── Load CSV ──────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"  QBO Customer Import — {'DRY RUN (no changes)' if DRY_RUN else '*** LIVE COMMIT ***'}")
print(f"{'='*60}\n")

df = pd.read_csv(CSV_PATH)
print(f"Loaded {len(df)} rows from {CSV_PATH}")
print(f"Columns: {df.columns.tolist()}\n")


# ── Field mapping & cleaning ──────────────────────────────────────────────────
def clean_address(raw):
    if pd.isna(raw):
        return None
    return str(raw).replace("\n", " ").replace("\r", " ").strip()

def split_email(raw):
    if pd.isna(raw):
        return None, None
    parts = [e.strip() for e in str(raw).split(",") if e.strip()]
    if not parts:
        return None, None
    return parts[0], ", ".join(parts[1:]) if len(parts) > 1 else None

def determine_company_name(row):
    name = str(row["Name"]).strip() if not pd.isna(row["Name"]) else ""
    company = str(row["Company name"]).strip() if not pd.isna(row["Company name"]) else ""
    return company if company and company != name else name

def clean_phone(raw):
    if pd.isna(raw):
        return None
    phone = str(raw).strip()
    return phone if phone else None

def clean_zip(raw):
    if pd.isna(raw):
        return None
    z = str(raw).strip()
    if z.endswith(".0"):
        z = z[:-2]
    return z if z else None

def clean_balance(raw):
    """Handle balances like '1,149.99' or '0.00'."""
    if pd.isna(raw):
        return 0.0
    return float(str(raw).replace(",", "").strip() or 0)


# ── Build client records ──────────────────────────────────────────────────────
clients_to_insert = []
warnings = []

for idx, row in df.iterrows():
    email, email_cc = split_email(row.get("Email"))
    company_name = determine_company_name(row)
    address_line1 = clean_address(row.get("Street Address"))
    open_balance = clean_balance(row.get("Open balance", 0))

    client = {
        "company_name":         company_name,
        "display_name":         str(row["Name"]).strip() if not pd.isna(row["Name"]) else None,
        "first_name":           None,
        "last_name":            None,
        "email":                email or "",
        "email_cc":             email_cc,
        "phone":                clean_phone(row.get("Phone")),
        "address_line1":        address_line1,
        "address_line2":        None,
        "city":                 str(row["City"]).strip() if not pd.isna(row.get("City")) else None,
        "state":                str(row["State"]).strip() if not pd.isna(row.get("State")) else None,
        "zip_code":             clean_zip(row.get("Zip")),
        "autocc_recurring":    False,
        "account_status":       "active",
        "account_balance":      round(open_balance, 2),
        "late_fee_type":        "none",
        "late_fee_amount":      0.00,
        "late_fee_grace_days":  0,
        "collections_exempt":   False,
        "collections_paused":   False,
        "auto_send_invoices":   False,
        "is_active":            True,
    }

    clients_to_insert.append(client)

    if not email:
        warnings.append(f"  ⚠  Row {idx+2}: '{company_name}' has no email address")
    if open_balance > 0:
        warnings.append(f"  💰 Row {idx+2}: '{company_name}' has open balance ${open_balance:.2f} — will import as account_balance")


# ── Print preview ─────────────────────────────────────────────────────────────
print(f"Records to import: {len(clients_to_insert)}")
print(f"Warnings:          {len(warnings)}\n")

if warnings:
    print("── Warnings ─────────────────────────────────────────────")
    for w in warnings:
        print(w)
    print()

print("── Sample records (first 5) ─────────────────────────────")
for c in clients_to_insert[:5]:
    print(f"  {c['company_name']:<40} email={c['email'] or 'MISSING':<35} balance=${c['account_balance']:.2f}")
print("  ...\n")


# ── Dry run stops here ────────────────────────────────────────────────────────
if DRY_RUN:
    print("✅ DRY RUN complete — no changes made.")
    print("   Run with --commit to import into the database.\n")
    sys.exit(0)


# ── Live commit ───────────────────────────────────────────────────────────────
print("── Connecting to database ────────────────────────────────")

import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Client, ActivityLog

db = SessionLocal()

try:
    inserted = 0
    skipped  = 0

    for c in clients_to_insert:
        existing = db.query(Client).filter(
            Client.company_name == c["company_name"]
        ).first()

        if existing:
            skipped += 1
            continue

        client = Client(**c)
        db.add(client)
        db.flush()  # Flush to get the client.id before creating activity log

        # Create activity log entry for the imported client
        log = ActivityLog(
            entity_type="client",
            entity_id=client.id,
            client_id=client.id,
            action="created",
            performed_by_id=None,
            performed_by_name="QBO Import",
            notes="Imported from QBO Customers export"
        )
        db.add(log)
        inserted += 1

    db.commit()
    print(f"\n✅ Import complete!")
    print(f"   Inserted: {inserted}")
    print(f"   Skipped (already exist): {skipped}\n")

except Exception as ex:
    db.rollback()
    print(f"\n❌ Import FAILED — rolled back.")
    print(f"   Error: {ex}")
    raise

finally:
    db.close()
