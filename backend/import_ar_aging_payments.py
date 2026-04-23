#!/usr/bin/env python3
"""
Import payments from QBO A/R Aging Detail Report
Matches payments to unpaid invoices by customer name and amount
"""

import csv
import sys
from datetime import datetime
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import models
from config import get_settings

settings = get_settings()


def parse_amount(amount_str):
    """Convert QBO amount string to Decimal"""
    if not amount_str or not isinstance(amount_str, str):
        return Decimal('0')
    amount_str = amount_str.strip().replace(',', '').replace('$', '')
    if amount_str.startswith('-'):
        return -Decimal(amount_str[1:])
    return Decimal(amount_str)


def clean_customer_name(name):
    """Clean customer name (remove domain/contact info after colon)"""
    if ':' in name:
        return name.split(':')[0].strip()
    return name.strip()


def import_ar_aging_payments(csv_path):
    """Import payments from A/R Aging Detail Report"""

    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Read CSV file
        with open(csv_path) as f:
            reader = csv.reader(f)
            # Skip header rows (first 5 lines)
            for _ in range(5):
                next(reader)

            rows = list(reader)

        # Parse rows
        data_rows = []
        for row in rows:
            if len(row) < 3 or not row[1].strip():
                continue
            # Skip category headers
            if row[1].lower() in ['date', 'current', 'not yet due', '1 - 30 days',
                                  '31 - 60 days', '61 - 90 days', '91 or more days past due']:
                continue

            try:
                date = datetime.strptime(row[1].strip(), '%m/%d/%Y')
                data_rows.append({
                    'date': date.date(),
                    'type': row[2].strip() if len(row) > 2 else '',
                    'num': row[3].strip() if len(row) > 3 else '',
                    'customer': clean_customer_name(row[4]) if len(row) > 4 else '',
                    'amount': parse_amount(row[6]) if len(row) > 6 else Decimal('0'),
                })
            except:
                pass

        print(f"Parsed {len(data_rows)} data rows")

        # Filter for payments from 2024+ and payments only
        payments = [r for r in data_rows if r['type'] == 'Payment' and r['date'].year >= 2024]
        print(f"Found {len(payments)} payments from 2024+")

        # Get clients and invoices
        clients = session.query(models.Client).all()
        client_map = {c.company_name: c for c in clients}

        # Get unpaid invoices
        unpaid_invoices = session.query(models.Invoice).filter(
            models.Invoice.status.in_([
                models.InvoiceStatus.sent,
                models.InvoiceStatus.partially_paid
            ])
        ).all()

        imported = 0
        unmatched = []

        print(f"\nProcessing {len(payments)} payments...")

        for payment in payments:
            customer_name = payment['customer']
            payment_amount = abs(payment['amount'])  # Make positive
            payment_date = payment['date']

            if not customer_name or payment_amount == 0:
                continue

            # Find matching client
            client = client_map.get(customer_name)
            if not client:
                unmatched.append(f"{customer_name} (${payment_amount})")
                continue

            # Find unpaid invoice for this customer with matching amount
            matching_invoice = None
            for inv in unpaid_invoices:
                if inv.client_id == client.id:
                    # Try exact match on balance_due
                    if float(inv.balance_due) == float(payment_amount):
                        matching_invoice = inv
                        break

            # If no exact match, find closest invoice
            if not matching_invoice:
                for inv in unpaid_invoices:
                    if inv.client_id == client.id:
                        # Find invoice with balance within 10% of payment
                        inv_balance = float(inv.balance_due)
                        if inv_balance > 0 and abs(inv_balance - float(payment_amount)) / inv_balance < 0.10:
                            matching_invoice = inv
                            break

            if matching_invoice:
                # Check if payment already exists
                existing = session.query(models.Payment).filter_by(
                    invoice_id=matching_invoice.id
                ).first()

                if existing:
                    continue

                # Create payment
                payment_record = models.Payment(
                    invoice_id=matching_invoice.id,
                    client_id=client.id,
                    amount=payment_amount,
                    payment_date=payment_date,
                    method=models.PaymentMethod.check,
                    notes=f'Imported from A/R Aging on {datetime.now().strftime("%Y-%m-%d")}'
                )

                session.add(payment_record)
                imported += 1

                if imported <= 10 or imported % 20 == 0:
                    print(f"  ✓ {payment_date} | {customer_name[:30]:30} | ${payment_amount:8.2f}")

        session.commit()

        print(f"\n{'='*70}")
        print(f"Imported:    {imported} payments")
        print(f"Unmatched:   {len(unmatched)} payments")
        if unmatched:
            print(f"\nUnmatched customers (first 10):")
            for um in unmatched[:10]:
                print(f"  - {um}")

    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    csv_path = "/Users/marksharkey/Downloads/PrecisionPros Network_A_R Aging Detail Report (1).csv"
    import_ar_aging_payments(csv_path)
