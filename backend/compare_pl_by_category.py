#!/usr/bin/env python3
"""
Compare P&L by category between QBO Journal export and accounting database.
Aggregates journal entries by GL account name and shows differences.
"""

import sys
import csv
from datetime import datetime
from decimal import Decimal
from collections import defaultdict

from database import SessionLocal
import models


def clean_money(val):
    if not val or val.strip() == "":
        return Decimal("0.00")
    cleaned = val.strip().replace("$", "").replace(",", "").replace('"', '')
    try:
        return Decimal(cleaned)
    except:
        return Decimal("0.00")


def parse_date(val):
    if not val or val.strip() == "":
        return None
    try:
        return datetime.strptime(val.strip(), "%m/%d/%Y").date()
    except:
        return None


def parse_qbo_journal(csv_path):
    """Parse QBO Journal CSV and aggregate by GL account."""
    categories = defaultdict(lambda: {"debit": Decimal("0.00"), "credit": Decimal("0.00")})

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)

        # Skip header rows (first 4 rows)
        for _ in range(4):
            next(reader, None)

        for raw_row in reader:
            if not raw_row or not any(raw_row):
                continue

            # Data row: [empty, date, txn_type, num, name, memo, full_name (GL account), debit, credit]
            if len(raw_row) < 9:
                continue

            # Skip total rows
            if raw_row[0] and not raw_row[1]:
                continue

            gl_account = raw_row[6].strip() if len(raw_row) > 6 else ""
            debit_str = raw_row[7].strip() if len(raw_row) > 7 else ""
            credit_str = raw_row[8].strip() if len(raw_row) > 8 else ""

            if not gl_account or (not debit_str and not credit_str):
                continue

            debit = clean_money(debit_str)
            credit = clean_money(credit_str)

            categories[gl_account]["debit"] += debit
            categories[gl_account]["credit"] += credit

    return categories


def get_db_categories():
    """Get P&L categories from database and aggregate."""
    db = SessionLocal()
    categories = defaultdict(lambda: {"debit": Decimal("0.00"), "credit": Decimal("0.00")})

    try:
        for entry in db.query(models.JournalEntry).all():
            categories[entry.gl_account_name]["debit"] += entry.debit
            categories[entry.gl_account_name]["credit"] += entry.credit
    finally:
        db.close()

    return categories


def main(csv_path):
    """Compare QBO Journal to database P&L."""
    print("\n" + "="*100)
    print("  P&L RECONCILIATION: QBO Journal vs Database")
    print("="*100)

    # Parse QBO
    qbo_cats = parse_qbo_journal(csv_path)
    print(f"\n✓ Parsed {len(qbo_cats)} categories from QBO Journal")

    # Get database
    db_cats = get_db_categories()
    print(f"✓ Loaded {len(db_cats)} categories from database\n")

    # Get all unique categories
    all_cats = sorted(set(list(qbo_cats.keys()) + list(db_cats.keys())))

    # Filter out balance sheet accounts (focus on P&L)
    # Balance sheet account keywords to skip
    bs_keywords = [
        "checking", "bank", "savings", "cash", "accounts receivable",
        "owner", "draw", "loan", "equity", "liability", "payable",
        "reconciliation", "accounts payable", "accrued", "deposit",
        "advance"
    ]

    # Find differences
    differences = []
    for cat in all_cats:
        # Skip balance sheet accounts
        cat_lower = cat.lower()
        if any(kw in cat_lower for kw in bs_keywords):
            continue

        qbo_debit = qbo_cats[cat]["debit"]
        qbo_credit = qbo_cats[cat]["credit"]
        db_debit = db_cats[cat]["debit"]
        db_credit = db_cats[cat]["credit"]

        # P&L perspective: show net balance
        qbo_net = qbo_credit - qbo_debit  # Revenue positive, expenses positive
        db_net = db_credit - db_debit

        diff = abs(db_net - qbo_net)

        if diff > 0:
            differences.append({
                "category": cat,
                "qbo_debit": qbo_debit,
                "qbo_credit": qbo_credit,
                "db_debit": db_debit,
                "db_credit": db_credit,
                "qbo_net": qbo_net,
                "db_net": db_net,
                "diff": db_net - qbo_net,
            })

    # Sort by largest difference
    differences.sort(key=lambda x: abs(x["diff"]), reverse=True)

    # Print summary
    print("="*100)
    print("DIFFERENCES (Database vs QBO):")
    print("="*100)
    print()

    if not differences:
        print("✅ All categories match perfectly!")
    else:
        print(f"❌ Found {len(differences)} categories with differences:\n")

        for item in differences:
            cat = item["category"]
            qbo_net = item["qbo_net"]
            db_net = item["db_net"]
            diff = item["diff"]

            print(f"Category: {cat}")
            print(f"  QBO:      ${qbo_net:>12.2f} (Dr: ${item['qbo_debit']:.2f}, Cr: ${item['qbo_credit']:.2f})")
            print(f"  Database: ${db_net:>12.2f} (Dr: ${item['db_debit']:.2f}, Cr: ${item['db_credit']:.2f})")
            print(f"  Diff:     ${diff:>12.2f}  {'✗' if abs(diff) > 0.01 else '✓'}")
            print()

    # Print summary stats
    total_qbo_net = sum(qbo_cats[cat]["credit"] - qbo_cats[cat]["debit"] for cat in qbo_cats)
    total_db_net = sum(db_cats[cat]["credit"] - db_cats[cat]["debit"] for cat in db_cats)

    print("="*100)
    print("TOTALS:")
    print("="*100)
    print(f"QBO Total (Net):  ${total_qbo_net:>12.2f}")
    print(f"DB Total (Net):   ${total_db_net:>12.2f}")
    print(f"Total Diff:       ${total_db_net - total_qbo_net:>12.2f}")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 compare_pl_by_category.py <journal_csv_file>")
        print("Example: python3 compare_pl_by_category.py PrecisionPros_Network_Journal.csv")
        sys.exit(1)

    csv_path = sys.argv[1]

    try:
        main(csv_path)
    except FileNotFoundError:
        print(f"❌ File not found: {csv_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
