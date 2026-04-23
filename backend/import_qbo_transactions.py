#!/usr/bin/env python3
"""Import QBO transaction data from CSV file."""

import csv
import sys
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models

def parse_amount(amount_str):
    """Parse amount string, handling parentheses for negatives."""
    if not amount_str:
        return Decimal("0.00")

    amount_str = amount_str.strip()
    if amount_str.startswith('(') and amount_str.endswith(')'):
        # Negative amount in parentheses
        return Decimal(amount_str[1:-1]) * -1

    # Remove commas
    amount_str = amount_str.replace(',', '')
    return Decimal(amount_str)


def infer_transaction_type(row_type, memo, check_number):
    """Infer transaction type from QBO data."""
    row_type = (row_type or "").lower().strip()
    memo = (memo or "").lower()

    # Check if there's an actual check number (numeric ref)
    if check_number and check_number.strip().isdigit():
        return models.TransactionType.check

    # Map common QBO transaction types
    if "check" in row_type:
        return models.TransactionType.check
    elif "deposit" in row_type or "deposit" in memo:
        return models.TransactionType.deposit
    elif "transfer" in row_type or "transfer" in memo:
        return models.TransactionType.transfer
    elif "payment" in row_type:
        # "Payment" is generic - could be check, ACH, wire, etc.
        return models.TransactionType.payment
    elif "journal" in row_type:
        # Journal entries are transfers between accounts
        return models.TransactionType.transfer
    elif "fee" in memo or "fee" in row_type:
        return models.TransactionType.fee
    elif "interest" in memo or "interest" in row_type:
        return models.TransactionType.interest
    else:
        return models.TransactionType.other


def import_qbo_csv(csv_path, account_name=None, import_batch=None):
    """Import transactions from QBO export CSV file."""

    if import_batch is None:
        import_batch = datetime.now().strftime("%Y%m%d_%H%M%S")

    db = SessionLocal()

    try:
        imported_count = 0
        skipped_count = 0
        current_account_name = account_name

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)

            # Skip header rows (first 5 rows)
            for _ in range(5):
                next(reader, None)

            for raw_row in reader:
                # Skip empty rows
                if not raw_row or not any(raw_row):
                    continue

                # Check if this is an account header (account name is in the first column)
                if len(raw_row) > 0 and raw_row[0] and not raw_row[1]:
                    # This is an account name row
                    potential_account = raw_row[0].strip()
                    if potential_account and "deleted" not in potential_account.lower():
                        current_account_name = potential_account
                    continue

                # Skip if we don't have an account name yet
                if not current_account_name:
                    continue

                # Expected: [empty, date, type, num, name, class, memo, split, amount, balance]
                if len(raw_row) < 10:
                    continue

                transaction_date_str = raw_row[1].strip()

                # Skip if not a date
                if not transaction_date_str or "/" not in transaction_date_str:
                    continue

                try:
                    # Get or create bank account
                    acct = db.query(models.BankAccount).filter_by(
                        account_name=current_account_name
                    ).first()

                    if not acct:
                        acct = models.BankAccount(
                            account_name=current_account_name,
                            account_type="Checking",
                            opening_balance=Decimal("0.00"),
                            is_active=True
                        )
                        db.add(acct)
                        db.flush()
                        print(f"Created bank account: {current_account_name}")

                    # Parse date
                    try:
                        transaction_date = datetime.strptime(transaction_date_str, "%m/%d/%Y").date()
                    except ValueError:
                        skipped_count += 1
                        continue

                    # Parse fields
                    txn_type = raw_row[2].strip()
                    txn_num = raw_row[3].strip() or None
                    name = raw_row[4].strip()
                    memo = raw_row[6].strip()
                    amount_str = raw_row[8].strip()
                    balance_str = raw_row[9].strip()

                    # Check if already imported
                    existing = db.query(models.BankTransaction).filter(
                        models.BankTransaction.bank_account_id == acct.id,
                        models.BankTransaction.transaction_date == transaction_date,
                        models.BankTransaction.description == (memo or name),
                        models.BankTransaction.amount == parse_amount(amount_str),
                    ).first()

                    if existing:
                        skipped_count += 1
                        continue

                    # Parse amounts
                    amount = parse_amount(amount_str)
                    balance = parse_amount(balance_str) if balance_str else None

                    # Create transaction
                    txn = models.BankTransaction(
                        bank_account_id=acct.id,
                        transaction_date=transaction_date,
                        transaction_type=infer_transaction_type(txn_type, memo or name, txn_num),
                        transaction_number=txn_num,
                        description=memo or name,
                        amount=amount,
                        balance=balance,
                        import_batch=import_batch
                    )

                    db.add(txn)
                    imported_count += 1

                    if imported_count % 100 == 0:
                        try:
                            db.commit()
                            print(f"Imported {imported_count} transactions...")
                        except Exception as e:
                            print(f"Error committing batch: {e}")
                            db.rollback()

                except Exception as e:
                    db.rollback()
                    skipped_count += 1
                    continue

        db.commit()
        print(f"\nImport completed:")
        print(f"  Imported: {imported_count}")
        print(f"  Skipped: {skipped_count}")
        print(f"  Batch ID: {import_batch}")

    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_qbo_transactions.py <csv_file> [account_name]")
        sys.exit(1)

    csv_file = sys.argv[1]
    account_name = sys.argv[2] if len(sys.argv) > 2 else "Main Account"

    import_qbo_csv(csv_file, account_name)
