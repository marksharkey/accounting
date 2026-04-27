#!/usr/bin/env python3
"""
Reconcile invoices with their payments - update invoice amounts and status

Usage:
    python3 reconcile_invoices_with_payments.py --dry-run
    python3 reconcile_invoices_with_payments.py --commit
"""

import argparse
import sys
from database import SessionLocal
from models import Invoice, Payment
from decimal import Decimal

# Parse arguments
parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--dry-run", action="store_true")
group.add_argument("--commit", action="store_true")
args = parser.parse_args()

DRY_RUN = args.dry_run

db = SessionLocal()

try:
    invoices = db.query(Invoice).all()
    updated = 0

    for inv in invoices:
        # Get all payments for this invoice
        payments = db.query(Payment).filter(Payment.invoice_id == inv.id).all()

        if not payments:
            continue

        # Calculate total paid
        total_paid = sum(p.amount for p in payments)

        # Update if different
        if inv.amount_paid != total_paid:
            old_paid = inv.amount_paid
            inv.amount_paid = total_paid
            inv.balance_due = max(Decimal("0.00"), inv.subtotal - total_paid)

            # Update status
            if inv.balance_due <= 0:
                inv.status = "paid"
            elif total_paid > 0:
                inv.status = "partially_paid"

            updated += 1
            print(f"Updated {inv.invoice_number}: ${old_paid} → ${total_paid} ({inv.status})")

    if DRY_RUN:
        db.rollback()
        print(f"\n📋 DRY RUN (no changes committed)")
    else:
        db.commit()
        print(f"\n✅ Reconciled {updated} invoices")

except Exception as e:
    db.rollback()
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
