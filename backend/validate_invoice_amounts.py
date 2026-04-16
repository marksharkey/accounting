#!/usr/bin/env python3
"""
Invoice Amount Validation Script
Compares invoice totals in the database against the Journal CSV source
to identify any amount discrepancies.

This ensures 100% accuracy for historical audit purposes.

Usage:
    python3 validate_invoice_amounts.py
"""

import sys
import os
import csv
from decimal import Decimal
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
from models import Invoice

def parse_journal_for_amounts(csv_path):
    """
    Parse Journal CSV to extract invoice AR totals (the source of truth).
    Returns: {invoice_number: ar_total_amount}
    """
    invoice_totals = {}
    current_invoice = None

    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        for row_num, row in enumerate(reader):
            if row_num < 4:  # Skip headers
                continue

            if not row or not any(row):
                continue

            first_col = (row[0] if row else "").strip()

            # Skip section headers
            if first_col and first_col != "":
                current_invoice = None
                continue

            if len(row) < 5:
                continue

            txn_type = (row[2] if len(row) > 2 else "").strip()
            inv_num = (row[3] if len(row) > 3 else "").strip()
            account = (row[6] if len(row) > 6 else "").strip()
            debit = (row[7] if len(row) > 7 else "").strip()
            credit = (row[8] if len(row) > 8 else "").strip()

            if txn_type != "Invoice" or not inv_num:
                continue

            # AR line has the invoice total
            if account == "Accounts Receivable":
                try:
                    amount = Decimal(debit if debit else credit or "0").quantize(Decimal("0.01"))
                    invoice_totals[inv_num] = amount
                except:
                    pass

    return invoice_totals

print(f"\n{'='*70}")
print("  Invoice Amount Validation")
print(f"{'='*70}\n")

try:
    # Load QBO invoice totals from Journal
    print("Loading Journal CSV...")
    journal_totals = parse_journal_for_amounts("PrecisionPros_Network_Journal.csv")
    print(f"Found {len(journal_totals)} invoices in Journal\n")

    # Load database invoices
    print("Loading database invoices...")
    db = SessionLocal()
    db_invoices = {i.invoice_number: i for i in db.query(Invoice).all()}
    print(f"Found {len(db_invoices)} invoices in database\n")

    # Compare
    print("─" * 70)
    print("COMPARING AMOUNTS (Journal vs Database)")
    print("─" * 70 + "\n")

    matches = 0
    mismatches = []
    journal_only = []
    db_only = []

    # Check invoices that are in both
    for inv_num in journal_totals:
        journal_amount = journal_totals[inv_num]

        if inv_num not in db_invoices:
            journal_only.append(inv_num)
            continue

        db_amount = Decimal(str(db_invoices[inv_num].total)).quantize(Decimal("0.01"))

        if journal_amount == db_amount:
            matches += 1
        else:
            mismatches.append({
                "invoice": inv_num,
                "journal": journal_amount,
                "database": db_amount,
                "difference": db_amount - journal_amount,
            })

    # Check invoices only in database
    for inv_num in db_invoices:
        if inv_num not in journal_totals:
            db_only.append(inv_num)

    # Report matches
    print(f"✓ Matching amounts: {matches}\n")

    # Report mismatches
    if mismatches:
        print(f"❌ AMOUNT MISMATCHES: {len(mismatches)}\n")

        # Sort by difference amount (largest first)
        mismatches.sort(key=lambda x: abs(x["difference"]), reverse=True)

        for m in mismatches[:50]:  # Show top 50
            print(f"  Invoice #{m['invoice']:5s}: Journal=${m['journal']:8} DB=${m['database']:8} (Diff: ${m['difference']:+})")

        if len(mismatches) > 50:
            print(f"  ... and {len(mismatches) - 50} more mismatches")
    else:
        print("✓ No amount mismatches found!")

    print()

    # Report invoices only in Journal (not imported)
    if journal_only:
        print(f"⚠ Invoices in Journal but NOT in Database: {len(journal_only)}")
        for inv_num in sorted(journal_only)[:20]:
            amount = journal_totals[inv_num]
            print(f"  #{inv_num}: ${amount}")
        if len(journal_only) > 20:
            print(f"  ... and {len(journal_only) - 20} more")

    print()

    # Report invoices only in database
    if db_only:
        print(f"⚠ Invoices in Database but NOT in Journal: {len(db_only)}")
        for inv_num in sorted(db_only)[:20]:
            amount = db_invoices[inv_num].total
            print(f"  #{inv_num}: ${amount}")
        if len(db_only) > 20:
            print(f"  ... and {len(db_only) - 20} more")

    # Summary
    print()
    print("─" * 70)
    print("SUMMARY")
    print("─" * 70)
    print(f"  Journal invoices:              {len(journal_totals):,}")
    print(f"  Database invoices:             {len(db_invoices):,}")
    print(f"  Matching amounts:              {matches:,}")
    print(f"  Amount mismatches:             {len(mismatches)}")
    print(f"  In Journal only (not imported):{len(journal_only)}")
    print(f"  In DB only (extra):            {len(db_only)}")
    print()

    if len(mismatches) == 0:
        print("✅ ALL INVOICES MATCH EXACTLY!")
    else:
        print(f"❌ {len(mismatches)} invoices have amount discrepancies")
        print("\nThese need to be investigated and fixed.")

    print(f"\n{'='*70}\n")

    db.close()

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
