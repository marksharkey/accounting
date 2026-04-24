#!/usr/bin/env python3
"""
Compare QBO exports to accounting database.
Shows invoices and transactions in QBO that aren't in the database yet.
"""

import sys
import csv
from datetime import datetime
from decimal import Decimal
import argparse

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


def compare_invoices(csv_path):
    """Compare QBO invoices to database invoices."""
    print("\n" + "="*70)
    print("  INVOICES: QBO vs Database")
    print("="*70)

    db = SessionLocal()

    try:
        # Read QBO invoices
        qbo_invoices = {}
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 8:
                    continue
                blank, date_val, txn_type, num, customer, due_date, amount, open_bal = row[:8]

                if blank.strip() != "" or txn_type.strip() != "Invoice":
                    continue

                open_balance = clean_money(open_bal)
                if open_balance <= 0:
                    continue

                inv_date = parse_date(date_val)
                if not inv_date or inv_date.year < 2023:
                    continue

                qbo_invoices[num.strip()] = {
                    "date": inv_date,
                    "customer": customer.strip(),
                    "due_date": parse_date(due_date),
                    "open_balance": open_balance,
                    "total_amount": clean_money(amount),
                }

        # Get database invoices
        db_invoices = {
            inv.invoice_number: inv
            for inv in db.query(models.Invoice).all()
        }

        # Find missing
        missing = []
        for inv_num, qbo_inv in sorted(qbo_invoices.items()):
            if inv_num not in db_invoices:
                missing.append((inv_num, qbo_inv))

        if missing:
            print(f"\n❌ MISSING FROM DATABASE: {len(missing)} invoices\n")
            for inv_num, inv in missing:
                print(f"  #{inv_num}")
                print(f"     Customer:  {inv['customer']}")
                print(f"     Date:      {inv['date']}")
                print(f"     Due:       {inv['due_date']}")
                print(f"     Amount:    ${inv['total_amount']:.2f}")
                print(f"     Open:      ${inv['open_balance']:.2f}")
                print()
        else:
            print(f"\n✅ All QBO invoices are in the database!")

        print(f"\nSummary:")
        print(f"  QBO invoices (2023+):     {len(qbo_invoices)}")
        print(f"  Database invoices:        {len(db_invoices)}")
        print(f"  Missing from DB:          {len(missing)}")

    finally:
        db.close()


def compare_transactions(csv_path, account_name="Main Account"):
    """Compare QBO transactions to database transactions."""
    print("\n" + "="*70)
    print("  TRANSACTIONS: QBO vs Database")
    print("="*70)

    db = SessionLocal()

    try:
        # Read QBO transactions
        qbo_txns = []
        current_account = account_name

        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)

            # Skip header
            for _ in range(5):
                next(reader, None)

            for raw_row in reader:
                if not raw_row or not any(raw_row):
                    continue

                # Account header row
                if len(raw_row) > 0 and raw_row[0] and not raw_row[1]:
                    current_account = raw_row[0].strip()
                    continue

                if len(raw_row) < 10:
                    continue

                txn_date_str = raw_row[1].strip()
                if not txn_date_str or "/" not in txn_date_str:
                    continue

                try:
                    txn_date = datetime.strptime(txn_date_str, "%m/%d/%Y").date()
                    description = raw_row[6].strip() or raw_row[4].strip()
                    amount = clean_money(raw_row[8].strip())

                    qbo_txns.append({
                        "date": txn_date,
                        "description": description,
                        "amount": amount,
                        "account": current_account,
                    })
                except:
                    continue

        # Get database account and transactions
        acct = db.query(models.BankAccount).filter_by(
            account_name=account_name
        ).first()

        db_txns = set()
        if acct:
            for txn in db.query(models.BankTransaction).filter_by(
                bank_account_id=acct.id
            ).all():
                db_txns.add((txn.transaction_date, txn.description, txn.amount))

        # Find missing
        missing = []
        for qbo_txn in qbo_txns:
            key = (qbo_txn["date"], qbo_txn["description"], qbo_txn["amount"])
            if key not in db_txns:
                missing.append(qbo_txn)

        if missing:
            print(f"\n❌ MISSING FROM DATABASE: {len(missing)} transactions\n")
            for txn in missing:
                print(f"  {txn['date']} | ${txn['amount']:>10.2f} | {txn['description']}")
        else:
            print(f"\n✅ All QBO transactions are in the database!")

        print(f"\nSummary:")
        print(f"  QBO transactions:        {len(qbo_txns)}")
        print(f"  Database transactions:   {len(db_txns)}")
        print(f"  Missing from DB:         {len(missing)}")

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compare QBO exports to accounting database"
    )
    parser.add_argument(
        "csv_file",
        help="Path to QBO export CSV (AR Aging or transaction export)"
    )
    parser.add_argument(
        "--type",
        choices=["invoices", "transactions", "both"],
        default="both",
        help="What to compare (default: both)"
    )
    parser.add_argument(
        "--account",
        default="Main Account",
        help="Bank account name for transaction comparison (default: 'Main Account')"
    )

    args = parser.parse_args()

    if args.type in ["invoices", "both"]:
        try:
            compare_invoices(args.csv_file)
        except FileNotFoundError:
            print(f"❌ File not found: {args.csv_file}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error comparing invoices: {e}")
            sys.exit(1)

    if args.type in ["transactions", "both"]:
        try:
            compare_transactions(args.csv_file, args.account)
        except FileNotFoundError:
            print(f"❌ File not found: {args.csv_file}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error comparing transactions: {e}")
            sys.exit(1)

    print("\n")
