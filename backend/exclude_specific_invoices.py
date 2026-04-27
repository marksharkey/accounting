#!/usr/bin/env python3
"""
Exclude specific invoices by client and amount.
"""

import sys
sys.path.insert(0, '.')
from database import SessionLocal
import models
from decimal import Decimal

# Invoices to exclude: (client_name, amount)
INVOICES_TO_EXCLUDE = [
    ("cyberabbi.com", 50.61),
    ("Get Green Earth(2)", 50.00),
    ("Get Green Earth(2)", 200.00),
    ("KATZ", 0.40),
    ("Rescate de San Carlos A.C.", 9.27),
    ("Sommer, Eric", 664.05),
    ("Terriann Muller", 135.00),
]

db = SessionLocal()

print("=" * 100)
print("EXCLUDING SPECIFIC INVOICES BY AMOUNT")
print("=" * 100)

excluded_count = 0
not_found = []

for client_name, amount in INVOICES_TO_EXCLUDE:
    # Find client
    client = db.query(models.Client).filter_by(display_name=client_name).first()
    if not client:
        print(f"\n❌ Client not found: {client_name}")
        not_found.append((client_name, amount))
        continue

    # Find invoices for this client with matching balance_due
    target_amount = Decimal(str(amount))
    matching_invoices = db.query(models.Invoice).filter(
        models.Invoice.client_id == client.id,
        models.Invoice.balance_due == target_amount,
        models.Invoice.status.in_([
            models.InvoiceStatus.sent,
            models.InvoiceStatus.partially_paid
        ])
    ).all()

    if not matching_invoices:
        print(f"\n⚠️  No invoice found for {client_name} with balance ${amount:.2f}")
        not_found.append((client_name, amount))
        continue

    # Mark all matching invoices as excluded
    for inv in matching_invoices:
        inv.exclude_from_ar_aging = True
        print(f"\n✓ Excluded invoice #{inv.invoice_number} (ID: {inv.id})")
        print(f"  Client: {client_name}")
        print(f"  Amount: ${inv.balance_due:.2f}")
        excluded_count += 1

db.commit()

print("\n" + "=" * 100)
print(f"RESULTS: Excluded {excluded_count} invoices")
if not_found:
    print(f"Not found: {len(not_found)} invoices")
    for client_name, amount in not_found:
        print(f"  {client_name}: ${amount:.2f}")
print("=" * 100)

db.close()
