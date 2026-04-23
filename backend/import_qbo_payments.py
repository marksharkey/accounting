#!/usr/bin/env python3
"""
Import QBO payments from Transaction List CSV and link to invoices
Matches payments by customer name and creates Payment records with payment dates
"""

import pandas as pd
import sys
from datetime import datetime
from decimal import Decimal
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
import models
from config import get_settings

settings = get_settings()


def clean_amount(amount_str):
    """Convert QBO amount string to Decimal"""
    if isinstance(amount_str, (int, float)):
        return Decimal(str(amount_str))
    # Remove commas and convert
    return Decimal(amount_str.replace(',', '').strip())


def import_qbo_payments(csv_path):
    """Import payments from QBO CSV and link to invoices"""

    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Read CSV file, skip first 4 rows
        df = pd.read_csv(csv_path, skiprows=4)

        print(f"Reading payments from: {csv_path}")
        print(f"Total rows: {len(df)}")

        # Filter for Payment transactions only
        payments_df = df[df['Transaction type'] == 'Payment'].copy()
        print(f"Payment transactions: {len(payments_df)}")

        # Parse date column
        payments_df['Date'] = pd.to_datetime(payments_df['Date'], format='%m/%d/%Y')

        # Clean amount (remove commas)
        payments_df['Amount'] = payments_df['Amount'].apply(clean_amount)

        # Get list of clients and invoices to match against
        clients = session.query(models.Client).all()
        client_map = {c.company_name: c for c in clients}

        invoices_by_client = {}
        for client_id, client in client_map.items():
            invoices_by_client[client_id] = session.query(models.Invoice).filter_by(
                client_id=client.id,
                status=models.InvoiceStatus.sent
            ).all()

        imported = 0
        unmatched = 0
        already_paid = 0

        print(f"\nProcessing {len(payments_df)} payment transactions...")

        for idx, row in payments_df.iterrows():
            customer_name = row['Name']
            payment_amount = row['Amount']
            payment_date = row['Date'].date()

            if not customer_name or pd.isna(payment_amount):
                continue

            # Find matching client
            client = client_map.get(customer_name)
            if not client:
                unmatched += 1
                continue

            # Find unpaid invoice for this client matching the amount
            invoices = invoices_by_client.get(customer_name, [])
            matching_invoice = None

            for inv in invoices:
                # Check if payment exactly matches balance due
                if float(inv.balance_due) == float(payment_amount):
                    matching_invoice = inv
                    break

            if not matching_invoice:
                # Try to find invoice with closest amount
                for inv in invoices:
                    if float(inv.balance_due) >= float(payment_amount):
                        matching_invoice = inv
                        break

            if matching_invoice:
                # Check if payment already exists
                existing_payment = session.query(models.Payment).filter_by(
                    invoice_id=matching_invoice.id
                ).first()

                if existing_payment:
                    already_paid += 1
                    continue

                # Create payment record
                payment = models.Payment(
                    invoice_id=matching_invoice.id,
                    client_id=matching_invoice.client_id,
                    amount=payment_amount,
                    payment_date=payment_date,
                    method=models.PaymentMethod.check,
                    notes=f'Imported from QBO on {datetime.now().strftime("%Y-%m-%d")}'
                )

                session.add(payment)
                imported += 1

                if imported % 100 == 0:
                    print(f"  Processed {imported} payments...")

        session.commit()

        print(f"\n{'='*70}")
        print(f"Imported:     {imported} payments")
        print(f"Already paid: {already_paid} invoices")
        print(f"Unmatched:    {unmatched} payments (customer not found)")
        print(f"Total new payments: {imported}")

    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    csv_path = "/Users/marksharkey/Downloads/PrecisionPros Network_Transaction List by Date.csv"
    import_qbo_payments(csv_path)
