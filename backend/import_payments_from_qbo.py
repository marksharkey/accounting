#!/usr/bin/env python3
"""
Import Payment records from QBO Transaction_List_by_Customer.csv
Matches payments to invoices by: customer + amount + date proximity
"""

import csv
from datetime import datetime, date, timedelta
from decimal import Decimal
from collections import defaultdict

from database import SessionLocal
from models import Invoice, Payment, Client, PaymentMethod, User, ActivityLog

# Parse Transaction List by Customer
print("Parsing QBO Transaction List by Customer...\n")

transactions_by_customer = defaultdict(list)

with open("PrecisionPros_Network_Transaction_List_by_Customer.csv", encoding="utf-8-sig") as f:
    reader = csv.reader(f)
    current_customer = None
    
    for row in reader:
        if not row or len(row) < 8:
            continue
            
        first_col = row[0].strip()
        
        # Customer header
        if first_col and not row[1].strip():
            current_customer = first_col
            continue
        
        # Total row
        if first_col.startswith("Total for"):
            current_customer = None
            continue
            
        # Transaction row
        if current_customer and row[1].strip():
            try:
                txn_date = datetime.strptime(row[1].strip(), "%m/%d/%Y").date()
                txn_type = row[2].strip()
                num = row[3].strip()
                account = row[6].strip()
                amount_str = row[7].strip().replace("$", "").replace(",", "")
                amount = Decimal(amount_str) if amount_str else Decimal("0")
                
                transactions_by_customer[current_customer].append({
                    "date": txn_date,
                    "type": txn_type,
                    "num": num,
                    "account": account,
                    "amount": amount,
                })
            except (ValueError, IndexError):
                continue

print(f"Parsed {len(transactions_by_customer)} customers")

# Match payments to invoices
db = SessionLocal()
system_user = db.query(User).first()

created_count = 0
skipped_customers = 0
no_matching_invoices = 0

for customer_name, transactions in sorted(transactions_by_customer.items()):
    # Get customer
    client = db.query(Client).filter_by(company_name=customer_name).first()
    if not client:
        skipped_customers += 1
        continue
    
    # Separate invoices and payments, sorted by date
    invoices = sorted([t for t in transactions if t["type"] == "Invoice"], key=lambda x: x["date"])
    payments = sorted([t for t in transactions if t["type"] == "Payment"], key=lambda x: x["date"])
    
    if not payments:
        continue
    
    # For each payment, find the invoice it matches
    for pmt in payments:
        pmt_amount = pmt["amount"]
        pmt_date = pmt["date"]
        
        # Look for invoices within 30 days before payment that match the amount
        matching_invoice = None
        for inv in invoices:
            inv_num = inv["num"]
            inv_date = inv["date"]
            inv_amount = inv["amount"]
            
            # Payment must be within 30 days after invoice
            if inv_date <= pmt_date <= inv_date + timedelta(days=30):
                # Match by exact amount
                if inv_amount == pmt_amount:
                    # Check if invoice exists in DB and doesn't already have this payment
                    db_invoice = db.query(Invoice).filter_by(invoice_number=inv_num).first()
                    if db_invoice:
                        existing = db.query(Payment).filter_by(
                            invoice_id=db_invoice.id,
                            payment_date=pmt_date,
                            amount=float(pmt_amount)
                        ).first()
                        if not existing:
                            matching_invoice = db_invoice
                            break
        
        if matching_invoice:
            # Determine payment method
            account = pmt["account"].lower()
            if "credit" in account:
                method = PaymentMethod.credit_card
            elif "checking" in account or "checking" in pmt["account"].lower():
                method = PaymentMethod.check
            elif "cash" in account:
                method = PaymentMethod.cash
            else:
                method = PaymentMethod.check
            
            payment = Payment(
                invoice_id=matching_invoice.id,
                client_id=client.id,
                payment_date=pmt_date,
                amount=float(pmt_amount),
                method=method,
                reference_number=pmt["num"] if pmt["num"] else None,
                recorded_by_id=system_user.id,
            )
            db.add(payment)
            db.flush()

            # Create activity log entry for the imported payment
            log = ActivityLog(
                entity_type="payment",
                entity_id=payment.id,
                client_id=client.id,
                action="created",
                performed_by_id=None,
                performed_by_name="QBO Import",
                timestamp=datetime.combine(pmt_date, datetime.min.time()),
                notes="Imported from QuickBooks Online"
            )
            db.add(log)
            created_count += 1
        else:
            no_matching_invoices += 1

db.commit()
db.close()

print(f"\n{'='*60}")
print(f"Created: {created_count} payment records")
print(f"Skipped customers: {skipped_customers} (not found in DB)")
print(f"Payments with no matching invoice: {no_matching_invoices}")
print(f"{'='*60}")
