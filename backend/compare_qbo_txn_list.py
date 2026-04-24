#!/usr/bin/env python3
"""
Compare QBO Transaction List by Customer to accounting database.
Shows what invoices and payments are in QBO but not yet in the accounting DB.
"""

import sys
import csv
from datetime import datetime
from decimal import Decimal

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


def compare_qbo_txn_list(csv_path):
    """Parse QBO transaction list and compare to database."""
    print("\n" + "="*80)
    print("  QBO INVOICES & PAYMENTS vs DATABASE")
    print("="*80)

    db = SessionLocal()

    try:
        # Parse CSV
        qbo_invoices = []
        qbo_payments = []
        current_customer = None

        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)

            for row in reader:
                if not row or not any(row):
                    continue

                # Customer header row (first column has name, rest empty)
                if row[0] and not row[1]:
                    current_customer = row[0].strip()
                    # Skip subtotal rows
                    if "total for" in current_customer.lower():
                        current_customer = None
                    continue

                # Skip if we don't have a customer
                if not current_customer or "total for" in current_customer.lower():
                    continue

                # Data row: [empty, date, txn_type, num, posting, memo, account, amount]
                if len(row) < 8:
                    continue

                date_str = row[1].strip()
                txn_type = row[2].strip()
                inv_num = row[3].strip()
                amount_str = row[7].strip()

                if not date_str or not txn_type:
                    continue

                try:
                    txn_date = datetime.strptime(date_str, "%m/%d/%Y").date()
                    amount = clean_money(amount_str)

                    if txn_type.lower() == "invoice":
                        qbo_invoices.append({
                            "date": txn_date,
                            "invoice_num": inv_num,
                            "customer": current_customer,
                            "amount": amount,
                        })
                    elif txn_type.lower() == "payment":
                        qbo_payments.append({
                            "date": txn_date,
                            "customer": current_customer,
                            "amount": amount,
                        })
                except:
                    continue

        # Get database invoices
        db_invoices = {
            inv.invoice_number: inv
            for inv in db.query(models.Invoice).all()
        }

        # Get database bank transactions
        db_txns = set()
        for txn in db.query(models.BankTransaction).all():
            db_txns.add((txn.transaction_date, txn.amount))

        # Find missing invoices
        missing_invoices = []
        for qbo_inv in qbo_invoices:
            if qbo_inv["invoice_num"] not in db_invoices:
                missing_invoices.append(qbo_inv)

        # Find missing payments
        missing_payments = []
        for qbo_pmt in qbo_payments:
            key = (qbo_pmt["date"], qbo_pmt["amount"])
            if key not in db_txns:
                missing_payments.append(qbo_pmt)

        # Print invoices
        print("\n" + "-"*80)
        print("INVOICES")
        print("-"*80)

        if missing_invoices:
            print(f"\n❌ MISSING FROM DATABASE: {len(missing_invoices)} invoices\n")
            for inv in sorted(missing_invoices, key=lambda x: x["date"]):
                print(f"  #{inv['invoice_num']:<8} {inv['date']} | ${inv['amount']:>10.2f} | {inv['customer']}")
        else:
            print(f"\n✅ All QBO invoices are in the database!")

        print(f"\nSummary:")
        print(f"  QBO invoices:        {len(qbo_invoices)}")
        print(f"  Database invoices:   {len(db_invoices)}")
        print(f"  Missing from DB:     {len(missing_invoices)}")

        # Print payments
        print("\n" + "-"*80)
        print("PAYMENTS")
        print("-"*80)

        if missing_payments:
            print(f"\n❌ MISSING FROM DATABASE: {len(missing_payments)} payments\n")
            for pmt in sorted(missing_payments, key=lambda x: x["date"]):
                print(f"  {pmt['date']} | ${pmt['amount']:>10.2f} | {pmt['customer']}")
        else:
            print(f"\n✅ All QBO payments are in the database!")

        print(f"\nSummary:")
        print(f"  QBO payments:           {len(qbo_payments)}")
        print(f"  Database transactions:  {len(db_txns)}")
        print(f"  Missing from DB:        {len(missing_payments)}")

    finally:
        db.close()

    print("\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 compare_qbo_txn_list.py <csv_file>")
        sys.exit(1)

    csv_path = sys.argv[1]

    try:
        compare_qbo_txn_list(csv_path)
    except FileNotFoundError:
        print(f"❌ File not found: {csv_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
