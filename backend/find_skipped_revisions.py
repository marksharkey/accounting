#!/usr/bin/env python3
"""
Detect invoices in the CSV that appear multiple times (revisions) but weren't properly
imported or updated in the database.

This script:
1. Parses the journal CSV and finds all invoices with duplicates (revisions)
2. Compares them to the database
3. Reports any where the database has outdated data
"""

import csv
import sys
from collections import defaultdict
from decimal import Decimal
from datetime import datetime

sys.path.insert(0, '.')
from database import SessionLocal
from models import Invoice, Client

# Parse journal CSV to find all invoice revisions
csv_path = "PrecisionPros_Network_Journal.csv"
invoices_in_csv = defaultdict  # (invoice_num, customer) -> [amounts]

print(f"\n{'='*80}")
print(f"  Scanning for Skipped Revisions in Journal CSV")
print(f"{'='*80}\n")

print(f"Loading Journal CSV: {csv_path}\n")

csv_invoices = defaultdict(list)  # (inv_num, customer) -> list of amounts

try:
    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        row_num = 0
        for row in reader:
            row_num += 1
            if row_num < 7:  # Skip headers
                continue

            if not row or len(row) < 9:
                continue

            txn_type = (row[2] if len(row) > 2 else "").strip()
            inv_num = (row[3] if len(row) > 3 else "").strip()
            customer = (row[4] if len(row) > 4 else "").strip()
            account = (row[6] if len(row) > 6 else "").strip()
            debit = (row[7] if len(row) > 7 else "").strip()
            credit = (row[8] if len(row) > 8 else "").strip()

            # Only look at Invoice transactions for AR (Accounts Receivable)
            if txn_type != "Invoice" or account != "Accounts Receivable":
                continue

            if not inv_num or not customer:
                continue

            # Clean customer name
            customer = customer.replace("(deleted)", "").strip().rstrip(",").strip()

            # Get amount - parse carefully
            try:
                if debit and debit.strip():
                    amount = Decimal(debit.replace(",", ""))
                elif credit and credit.strip():
                    amount = Decimal(credit.replace(",", ""))
                else:
                    continue
                amount = abs(amount)
            except:
                continue

            csv_invoices[(inv_num, customer)].append(amount)

    print(f"Parsed {row_num} rows from Journal CSV\n")

    # Find invoices with multiple entries (revisions)
    revisions = {k: v for k, v in csv_invoices.items() if len(v) > 1}

    if not revisions:
        print("✓ No revisions found in CSV (each invoice appears only once)")
        sys.exit(0)

    print(f"Found {len(revisions)} invoices with revisions:\n")

    # Check each against the database
    db = SessionLocal()

    problems = []

    for (inv_num, customer_name), amounts in sorted(revisions.items()):
        amounts_unique = sorted(set(amounts), reverse=True)
        latest_amount = amounts_unique[0]
        previous_amounts = amounts_unique[1:]

        print(f"Invoice #{inv_num} ({customer_name})")
        print(f"  CSV shows: {' → '.join(f'${a:.2f}' for a in amounts_unique)}")

        # Check database
        db_inv = db.query(Invoice).filter(Invoice.invoice_number == inv_num).first()

        if not db_inv:
            print(f"  ❌ DATABASE: Invoice not found (wasn't imported)")
            problems.append((inv_num, customer_name, "missing", latest_amount))
        elif abs(db_inv.total - latest_amount) > Decimal("0.01"):
            print(f"  ❌ DATABASE: total=${db_inv.total:.2f} (outdated, should be ${latest_amount:.2f})")
            problems.append((inv_num, customer_name, "outdated", latest_amount, db_inv.total))
        elif db_inv.balance_due > db_inv.total:
            print(f"  ⚠️  DATABASE: data integrity issue (balance_due=${db_inv.balance_due:.2f} > total=${db_inv.total:.2f})")
            problems.append((inv_num, customer_name, "integrity", latest_amount, db_inv.total))
        else:
            print(f"  ✓ DATABASE: up to date (${db_inv.total:.2f})")

        print()

    db.close()

    # Summary
    if problems:
        print(f"{'='*80}")
        print(f"  ⚠️  PROBLEMS FOUND: {len(problems)} invoice(s) need attention")
        print(f"{'='*80}\n")

        for inv_num, customer, issue, latest, *db_info in problems:
            if issue == "missing":
                print(f"❌ #{inv_num} ({customer}): NOT IN DATABASE")
                print(f"   → Latest amount from CSV: ${latest:.2f}")
            elif issue == "outdated":
                db_total = db_info[0]
                print(f"❌ #{inv_num} ({customer}): OUTDATED")
                print(f"   → Database has: ${db_total:.2f}")
                print(f"   → Should be: ${latest:.2f}")
            elif issue == "integrity":
                db_total = db_info[0]
                print(f"⚠️  #{inv_num} ({customer}): DATA INTEGRITY ISSUE")
                print(f"   → Database shows: total=${db_total:.2f}, balance_due=??? (check manually)")
            print()

        print(f"\nRun fix_invoice_revisions.py to fix these issues.")
    else:
        print(f"\n✓ All revisions are properly updated in the database!")

    print(f"\n{'='*80}\n")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
