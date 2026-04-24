#!/usr/bin/env python3
"""
Fix client name fields to match QBO data.
Reads Customers.csv and corrects existing DB records using email as match key.
Updates company_name and display_name to align with QBO.

Usage:
    python3 fix_client_names.py --dry-run      # Preview only, no DB changes
    python3 fix_client_names.py --commit       # Actually update DB
"""

import sys
import argparse
import pandas as pd
from database import SessionLocal
import models

parser = argparse.ArgumentParser(description="Fix client name fields from QBO Customers.csv")
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--dry-run", action="store_true", help="Preview changes, no DB writes")
group.add_argument("--commit", action="store_true", help="Actually write to database")
parser.add_argument("--csv", default="Customers.csv", help="Path to Customers.csv (default: Customers.csv)")
args = parser.parse_args()

DRY_RUN = args.dry_run
CSV_PATH = args.csv

print(f"\n{'='*70}")
print(f"  QBO Customer Name Fix — {'DRY RUN (no changes)' if DRY_RUN else '*** LIVE COMMIT ***'}")
print(f"{'='*70}\n")

# Load CSV
df = pd.read_csv(CSV_PATH)
print(f"Loaded {len(df)} customers from {CSV_PATH}\n")

db = SessionLocal()

try:
    updated = 0
    skipped = 0
    not_matched = 0
    changes_log = []

    for idx, row in df.iterrows():
        email = str(row.get("Email", "")).strip() if pd.notna(row.get("Email")) else ""
        qbo_display_name = str(row["Name"]).strip() if pd.notna(row["Name"]) else ""
        qbo_company_name = str(row["Company name"]).strip() if pd.notna(row["Company name"]) else ""

        # Skip rows with no email
        if not email:
            skipped += 1
            continue

        # Find matching client by email (most reliable match key)
        client = db.query(models.Client).filter_by(email=email).first()

        if not client:
            not_matched += 1
            continue

        # Determine what changed
        company_changed = False
        display_changed = False
        old_company = client.company_name
        old_display = client.display_name

        # Update company_name: prefer QBO company_name if it exists and differs from Name
        new_company = qbo_company_name if (qbo_company_name and qbo_company_name != qbo_display_name) else qbo_display_name
        if new_company and client.company_name != new_company:
            company_changed = True
            client.company_name = new_company

        # Update display_name from QBO Name field
        if qbo_display_name and client.display_name != qbo_display_name:
            display_changed = True
            client.display_name = qbo_display_name

        if company_changed or display_changed:
            updated += 1
            change_desc = []
            if company_changed:
                change_desc.append(f"Company: '{old_company}' → '{new_company}'")
            if display_changed:
                change_desc.append(f"Display: '{old_display or '(empty)'}' → '{qbo_display_name}'")
            changes_log.append((client.id, client.email, client.company_name, "; ".join(change_desc)))

    # Print summary
    print(f"Customers processed: {len(df)}")
    print(f"Updates needed:      {updated}")
    print(f"Skipped (no email):  {skipped}")
    print(f"Not matched in DB:   {not_matched}\n")

    if changes_log:
        print("── Updates to be applied ────────────────────────────────────")
        for client_id, email, company, changes in changes_log[:10]:  # Show first 10
            print(f"  [{client_id}] {email}")
            print(f"      Company: {company}")
            print(f"      {changes}")
            print()
        if len(changes_log) > 10:
            print(f"  ... and {len(changes_log) - 10} more\n")

    if DRY_RUN:
        print("✅ DRY RUN complete — no changes made.")
        print("   Run with --commit to apply these updates.\n")
        sys.exit(0)

    # Commit changes
    print("── Applying updates to database ────────────────────────────────")
    db.commit()
    print(f"\n✅ Update complete!")
    print(f"   Updated: {updated} clients\n")

except Exception as ex:
    db.rollback()
    print(f"\n❌ Update FAILED — rolled back.")
    print(f"   Error: {ex}")
    raise

finally:
    db.close()
