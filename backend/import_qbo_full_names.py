#!/usr/bin/env python3
"""
Import QBO Customer Contact List to populate full_name field.
Matches clients by email and updates full_name from the contact list.

Usage:
    python3 import_qbo_full_names.py --dry-run <csv_path>      # Preview only
    python3 import_qbo_full_names.py --commit <csv_path>       # Actually update
"""

import sys
import argparse
import pandas as pd
from database import SessionLocal
import models

parser = argparse.ArgumentParser(description="Import full names from QBO Customer Contact List")
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--dry-run", action="store_true", help="Preview changes, no DB writes")
group.add_argument("--commit", action="store_true", help="Actually write to database")
parser.add_argument("csv", help="Path to Customer Contact List CSV")
args = parser.parse_args()

DRY_RUN = args.dry_run
CSV_PATH = args.csv

print(f"\n{'='*70}")
print(f"  QBO Customer Contact List Import — {'DRY RUN (no changes)' if DRY_RUN else '*** LIVE COMMIT ***'}")
print(f"{'='*70}\n")

# Load CSV, skip first 2 rows (metadata)
df = pd.read_csv(CSV_PATH, skiprows=2)
print(f"Loaded {len(df)} customers from {CSV_PATH}")
print(f"Columns: {df.columns.tolist()}\n")

db = SessionLocal()

try:
    updated = 0
    skipped = 0
    not_matched = 0
    no_fullname = 0
    changes_log = []

    for idx, row in df.iterrows():
        email = str(row.get("Email", "")).strip() if pd.notna(row.get("Email")) else ""
        customer_full_name = str(row.get("Customer full name", "")).strip() if pd.notna(row.get("Customer full name")) else ""
        full_name = str(row.get("Full name", "")).strip() if pd.notna(row.get("Full name")) else ""

        # Skip if no email
        if not email:
            skipped += 1
            continue

        # Skip if neither field has data
        if not customer_full_name and not full_name:
            no_fullname += 1
            continue

        # Match by email
        client = db.query(models.Client).filter_by(email=email).first()

        if not client:
            not_matched += 1
            continue

        # Track changes
        changes = []

        # Update display_name from Customer full name if available
        if customer_full_name and client.display_name != customer_full_name:
            old_display = client.display_name or '(empty)'
            client.display_name = customer_full_name
            changes.append(f"Display: '{old_display}' → '{customer_full_name}'")

        # Update full_name if it's different or currently empty
        if full_name and client.full_name != full_name:
            old_fullname = client.full_name or '(empty)'
            client.full_name = full_name
            changes.append(f"Full name: '{old_fullname}' → '{full_name}'")

        if changes:
            updated += 1
            changes_log.append((client.id, email, "; ".join(changes)))

    # Print summary
    print(f"Customers processed: {len(df)}")
    print(f"Updates needed:      {updated}")
    print(f"Skipped (no email):  {skipped}")
    print(f"Skipped (no name):   {no_fullname}")
    print(f"Not matched in DB:   {not_matched}\n")

    if changes_log:
        print("── Updates to be applied ────────────────────────────────────")
        for client_id, email, changes in changes_log[:15]:
            print(f"  [{client_id}] {email}")
            print(f"      {changes}")
        if len(changes_log) > 15:
            print(f"  ... and {len(changes_log) - 15} more\n")
        else:
            print()

    if DRY_RUN:
        print("✅ DRY RUN complete — no changes made.")
        print("   Run with --commit to apply these updates.\n")
        sys.exit(0)

    # Commit changes
    print("── Applying updates to database ────────────────────────────────")
    db.commit()
    print(f"\n✅ Import complete!")
    print(f"   Updated: {updated} clients\n")

except Exception as ex:
    db.rollback()
    print(f"\n❌ Import FAILED — rolled back.")
    print(f"   Error: {ex}")
    raise

finally:
    db.close()
