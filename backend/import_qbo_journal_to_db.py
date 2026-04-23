#!/usr/bin/env python3
"""
Import QBO Journal data into journal_entries table for accrual-basis P&L reporting
Maps QBO GL accounts to our Chart of Accounts and creates a journal entry ledger
"""

import pandas as pd
import sys
from datetime import datetime
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import models
from config import get_settings

settings = get_settings()

# Mapping from QBO account names to our GL account codes
QBO_TO_GL_MAPPING = {
    # Revenue accounts
    'Managed Servers': '4200',
    'Web Hosting': '4100',
    'Email Hosting': '4020',
    'Web Programming': '4300',
    'Domain Name Registrations': '4010',
    'Uncategorized Income {23}': '4040',
    'Services': '4030',

    # Expense accounts - A&G
    'A&G:Bank Fees': '5010',
    'A&G:credit card Fees': '5020',
    'A&G:Dial Up': '5030',
    'A&G:dues and subcriptions': '5040',
    'A&G:dues and subscriptions': '5040',
    'A&G:Telephone': '5050',
    'A&G:Postage': '5050',

    # Expense accounts - Server Management
    'Server Management Fees:servers': '6030',
    'Server Management Fees:Email Hosting': '6020',
    'Server Management Fees:domain registrations': '6010',

    # Other expense accounts
    'Marketing': '6300',
    'Supplies': '6040',
    'Purchased Services': '6100',
    'Meals': '6100',
    'TAXES - 2004': '6060',
    'taxex2023': '6060',
    'taxes 2024': '6060',
    'Taxes 2022': '6060',
    'TA': '6060',  # Tax Allowance/Additional Tax (maps to Taxes)
}

def import_qbo_journal(csv_path):
    """Import QBO Journal and create GL journal entry ledger"""

    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Read journal file
        df = pd.read_csv(csv_path, skiprows=3)

        # Clean up
        df = df[df['Transaction date'].notna()].copy()
        df['Transaction date'] = pd.to_datetime(df['Transaction date'], format='%m/%d/%Y', errors='coerce')

        # Convert currency columns
        def to_decimal(val):
            if pd.isna(val) or val == '':
                return Decimal('0')
            return Decimal(str(val).replace(',', '').replace('$', ''))

        df['Debit'] = df['Debit'].apply(to_decimal)
        df['Credit'] = df['Credit'].apply(to_decimal)

        print(f"Imported {len(df)} journal entries from {csv_path}")
        print(f"Date range: {df['Transaction date'].min().date()} to {df['Transaction date'].max().date()}")

        # Process all journal entries
        print("\n" + "="*70)
        print("Importing Journal Entries to Database")
        print("="*70)

        imported = 0
        skipped = 0

        for idx, row in df.iterrows():
            qbo_account = str(row['Full name']).strip()
            transaction_date = row['Transaction date'].date()
            debit = row['Debit']
            credit = row['Credit']

            # Skip if no amount
            if debit == 0 and credit == 0:
                skipped += 1
                continue

            # Get GL code from mapping
            gl_code = QBO_TO_GL_MAPPING.get(qbo_account)

            # Only import if we have a mapping for this account
            if not gl_code:
                skipped += 1
                continue

            # Create journal entry
            entry = models.JournalEntry(
                transaction_date=transaction_date,
                gl_account_code=gl_code,
                gl_account_name=qbo_account,
                debit=debit,
                credit=credit,
                description=f"QBO Import: {qbo_account}",
                source="qbo_journal"
            )

            session.add(entry)
            imported += 1

            if imported <= 5 or imported % 1000 == 0:
                print(f"✓ {transaction_date} | {qbo_account:40} | Debit: ${debit:10,.2f} | Credit: ${credit:10,.2f}")

        session.commit()

        print(f"\n{'='*70}")
        print(f"Imported:    {imported} journal entries")
        print(f"Skipped:     {skipped} entries (no mapping or no amount)")
        print(f"Total rows:  {len(df)}")

        # Summary by account code
        print("\n" + "="*70)
        print("Summary by GL Account")
        print("="*70)

        accounts = session.query(
            models.JournalEntry.gl_account_code,
            models.JournalEntry.gl_account_name
        ).distinct().order_by(models.JournalEntry.gl_account_code).all()

        for acc_code, acc_name in accounts:
            entries = session.query(models.JournalEntry).filter(
                models.JournalEntry.gl_account_code == acc_code
            ).all()

            total_debit = sum(e.debit for e in entries)
            total_credit = sum(e.credit for e in entries)

            print(f"{acc_code}: {acc_name:40} | Debit: ${total_debit:12,.2f} | Credit: ${total_credit:12,.2f}")

        print("\n✅ Journal import complete!")

    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    csv_path = "/Users/marksharkey/Downloads/PrecisionPros Network_Journal.csv"
    import_qbo_journal(csv_path)
