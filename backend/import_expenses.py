#!/usr/bin/env python3
"""
QBO Transaction Detail Import Script — PrecisionPros Billing
Imports expenses from QBO Transaction Detail by Account CSV into the expenses table.

Usage:
    python3 import_expenses.py --dry-run      # Preview only, no DB changes
    python3 import_expenses.py --commit       # Actually insert into DB

Place this script in ~/accounting/backend/ and run from there.
"""

import sys
import os
import argparse
import csv
from datetime import datetime
from decimal import Decimal

# ── Parse args ────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Import QBO expenses into PrecisionPros")
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--dry-run", action="store_true", help="Preview import, no DB writes")
group.add_argument("--commit",  action="store_true", help="Actually write to database")
parser.add_argument("--csv", default="PrecisionPros_Network_Transaction_Detail_by_Account.csv",
                    help="Path to Transaction Detail CSV")
args = parser.parse_args()

DRY_RUN = args.dry_run
CSV_PATH = args.csv

# ── Expense accounts to import (maps QBO account name -> chart_of_accounts code/name)
# These are the expense-side accounts from the report.
EXPENSE_ACCOUNTS = {
    "Marketing":               "Marketing",
    "Meals":                   "Meals",
    "Purchased Services":      "Purchased Services",
    "Supplies":                "Supplies",
    "TA":                      "Travel & Auto",
    "Taxes 2022":              "Taxes",
    "taxes 2024":              "Taxes",
    "TAXES-2025":              "Taxes",
    "taxex2023":               "Taxes",
    "Web Hosting Expenses":    "Web Hosting Expenses",
    "A&G":                     "Administrative & General",
    "Bank Fees":               "Bank Fees",
    "credit card Fees":        "Credit Card Fees",
    "Dial Up":                 "Dial Up",
    "dues and subcriptions":   "Dues & Subscriptions",
    "Postage":                 "Postage",
    "Telephone":               "Telephone",
    "Server Management Fees":  "Server Management Fees",
    "domain registrations":    "Domain Registrations",
    "Email Hosting":           "Email Hosting",
    "servers":                 "Servers",
    "Bad Debt":                "Bad Debt",
    "Reconciliation Discrepancies": "Reconciliation Discrepancies",
}

# Transaction types to import as expenses (skip Payments, Invoices etc.)
EXPENSE_TXN_TYPES = {"Expense", "Check", "Bill", "Bill Payment", "Journal Entry", "Credit Card Credit"}

print(f"\n{'='*60}")
print(f"  QBO Expense Import — {'DRY RUN (no changes)' if DRY_RUN else '*** LIVE COMMIT ***'}")
print(f"{'='*60}\n")

# ── Helpers ───────────────────────────────────────────────────────────────────
def clean_money(val):
    if not val or val.strip() == "":
        return Decimal("0.00")
    cleaned = val.strip().replace("$", "").replace(",", "").replace('"', "")
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

# ── Parse CSV ─────────────────────────────────────────────────────────────────
with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
    reader = csv.reader(f)
    rows = list(reader)

expenses_raw   = []
current_account = None
skipped_accounts = {}
skipped_txn_types = {}

for row in rows:
    if not row or len(row) < 2:
        continue

    first = row[0].strip()

    # Detect account section headers (non-blank first col, not a total/header row)
    if first and not first.startswith("Transaction") and not first.startswith("PrecisionPros") \
            and not first.startswith("January") and not first.startswith("Total") \
            and not first.startswith("Cash Basis") and first != "TOTAL":
        current_account = first
        continue

    # Skip non-data rows
    if first != "":
        continue

    if len(row) < 9:
        continue

    _, date_val, txn_type, num, name, _, memo, split, amount, *_ = row + [""] * 5

    txn_type = txn_type.strip()
    if not txn_type or txn_type == "Transaction type":
        continue

    # Only process rows in expense accounts
    if current_account not in EXPENSE_ACCOUNTS:
        skipped_accounts[current_account] = skipped_accounts.get(current_account, 0) + 1
        continue

    # Only import expense-type transactions (skip payments received, etc.)
    if txn_type not in EXPENSE_TXN_TYPES:
        skipped_txn_types[txn_type] = skipped_txn_types.get(txn_type, 0) + 1
        continue

    amt = clean_money(amount)
    # Expenses are typically negative in this report (money going out)
    # We store as positive amounts in our expenses table
    expense_amount = abs(amt)
    if expense_amount == 0:
        continue

    exp_date = parse_date(date_val)
    if not exp_date:
        continue

    expenses_raw.append({
        "date":        exp_date,
        "account":     current_account,
        "category":    EXPENSE_ACCOUNTS[current_account],
        "vendor":      name.strip() or memo.strip() or "Unknown",
        "description": memo.strip() or txn_type,
        "amount":      expense_amount,
        "ref_number":  num.strip() or None,
        "txn_type":    txn_type,
    })

print(f"Found {len(expenses_raw)} expense transactions\n")

# Summary by account
print("── By account ───────────────────────────────────────────")
by_account = {}
for e in expenses_raw:
    by_account.setdefault(e["account"], []).append(e)
for acct, items in sorted(by_account.items()):
    total = sum(i["amount"] for i in items)
    print(f"  {acct:<35} {len(items):>4} transactions   ${total:>10,.2f}")

total_all = sum(e["amount"] for e in expenses_raw)
print(f"\n  TOTAL EXPENSES: ${total_all:,.2f}\n")

print("── Sample transactions (first 10) ──────────────────────")
for e in expenses_raw[:10]:
    print(f"  {str(e['date']):<12} {e['account']:<30} {e['vendor']:<30} ${e['amount']:>8.2f}")
print("  ...\n")

if DRY_RUN:
    print("✅ DRY RUN complete — no changes made.")
    print("   Run with --commit to import into the database.\n")
    sys.exit(0)

# ── Live commit ───────────────────────────────────────────────────────────────
print("── Connecting to database ────────────────────────────────")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Expense, ChartOfAccount

db = SessionLocal()

try:
    inserted = 0
    skipped  = 0

    # Cache chart of accounts by name
    coa_cache = {}
    all_coa = db.query(ChartOfAccount).all()
    for coa in all_coa:
        coa_cache[coa.name.lower()] = coa

    for e in expenses_raw:
        # Look up chart of accounts category
        cat_name = e["category"].lower()
        coa = coa_cache.get(cat_name)
        # If not found, try partial match
        if not coa:
            for key, val in coa_cache.items():
                if cat_name in key or key in cat_name:
                    coa = val
                    break

        exp_obj = Expense(
            expense_date     = e["date"],
            vendor           = e["vendor"][:150],
            description      = e["description"][:255] if e["description"] else None,
            amount           = e["amount"],
            category_id      = coa.id if coa else None,
            reference_number = e["ref_number"],
            notes            = f"Imported from QBO — {e['account']} / {e['txn_type']}",
            reconciled       = False,
        )
        db.add(exp_obj)
        inserted += 1

    db.commit()
    print(f"\n✅ Import complete!")
    print(f"   Inserted: {inserted}")
    print(f"   Skipped:  {skipped}\n")

except Exception as ex:
    db.rollback()
    print(f"\n❌ Import FAILED — rolled back.")
    print(f"   Error: {ex}")
    raise

finally:
    db.close()
