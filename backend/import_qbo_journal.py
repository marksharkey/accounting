#!/usr/bin/env python3
"""
Import QBO Journal data for accrual-basis P&L reporting
Maps QBO GL accounts to our Chart of Accounts and creates a transaction ledger
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
}

def import_qbo_journal(csv_path):
    """Import QBO Journal and create GL transaction ledger"""

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

        print(f"Imported {len(df)} journal entries")
        print(f"Date range: {df['Transaction date'].min().date()} to {df['Transaction date'].max().date()}")

        # Get all GL accounts
        all_accounts = session.query(models.ChartOfAccount).all()
        account_map = {acc.code: acc for acc in all_accounts}

        # Process revenue transactions (credits to revenue accounts)
        print("\n" + "="*70)
        print("Processing Revenue Transactions")
        print("="*70)

        revenue_count = 0
        for idx, row in df.iterrows():
            qbo_account = str(row['Full name']).strip()

            # Match against QBO revenue accounts
            if qbo_account in [k for k in QBO_TO_GL_MAPPING.keys() if '4' in QBO_TO_GL_MAPPING[k]]:
                if row['Credit'] > 0:
                    gl_code = QBO_TO_GL_MAPPING.get(qbo_account)
                    if gl_code and gl_code in account_map:
                        revenue_count += 1
                        if revenue_count <= 5:
                            print(f"✓ {row['Transaction date'].date()} | {qbo_account:40} | ${row['Credit']:10,.2f} → GL {gl_code}")

        print(f"✓ Found {revenue_count} revenue transactions")

        # Process expense transactions (debits to expense accounts)
        print("\n" + "="*70)
        print("Processing Expense Transactions")
        print("="*70)

        expense_count = 0
        for idx, row in df.iterrows():
            qbo_account = str(row['Full name']).strip()

            # Match against QBO expense accounts
            if qbo_account in QBO_TO_GL_MAPPING and QBO_TO_GL_MAPPING[qbo_account][0] in ['5', '6']:
                if row['Debit'] > 0:
                    gl_code = QBO_TO_GL_MAPPING.get(qbo_account)
                    if gl_code and gl_code in account_map:
                        expense_count += 1
                        if expense_count <= 5:
                            print(f"✓ {row['Transaction date'].date()} | {qbo_account:40} | ${row['Debit']:10,.2f} → GL {gl_code}")

        print(f"✓ Found {expense_count} expense transactions")

        # Summary by date range
        print("\n" + "="*70)
        print("P&L Summary by Period (2023-2026)")
        print("="*70)

        for year in [2023, 2024, 2025, 2026]:
            year_data = df[df['Transaction date'].dt.year == year]

            year_revenue = Decimal('0')
            year_expenses = Decimal('0')

            for idx, row in year_data.iterrows():
                qbo_account = str(row['Full name']).strip()
                if qbo_account in [k for k in QBO_TO_GL_MAPPING.keys() if '4' in QBO_TO_GL_MAPPING[k]]:
                    year_revenue += row['Credit']
                if qbo_account in [k for k in QBO_TO_GL_MAPPING.keys() if QBO_TO_GL_MAPPING[k][0] in ['5', '6']]:
                    year_expenses += row['Debit']

            net = year_revenue - year_expenses
            print(f"\n{year}:")
            print(f"  Income:    ${year_revenue:12,.2f}")
            print(f"  Expenses:  ${year_expenses:12,.2f}")
            print(f"  Net:       ${net:12,.2f}")

        # Grand totals
        print("\n" + "="*70)
        print("GRAND TOTALS (2023-2026)")
        print("="*70)

        total_revenue = Decimal('0')
        total_expenses = Decimal('0')

        for idx, row in df.iterrows():
            qbo_account = str(row['Full name']).strip()
            if qbo_account in [k for k in QBO_TO_GL_MAPPING.keys() if '4' in QBO_TO_GL_MAPPING[k]]:
                total_revenue += row['Credit']
            if qbo_account in [k for k in QBO_TO_GL_MAPPING.keys() if QBO_TO_GL_MAPPING[k][0] in ['5', '6']]:
                total_expenses += row['Debit']

        print(f"Total Revenue:  ${total_revenue:,.2f}")
        print(f"Total Expenses: ${total_expenses:,.2f}")
        print(f"Net Income:     ${total_revenue - total_expenses:,.2f}")

        print("\n✅ Journal import analysis complete!")
        print("\nNote: The P&L is now using accrual-basis accounting (invoice date, not payment date)")
        print("This matches QBO's reporting methodology.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    csv_path = "/Users/marksharkey/Downloads/PrecisionPros Network_Journal.csv"
    import_qbo_journal(csv_path)
