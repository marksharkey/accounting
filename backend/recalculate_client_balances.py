#!/usr/bin/env python3
"""
Recalculate Client Account Balances Based on Invoice Balance Due
Updates client.account_balance to equal the sum of all unpaid invoice balances.
"""

import sys
import os
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Client, Invoice, ActivityLog

db = SessionLocal()

try:
    print("\n" + "="*60)
    print("  Recalculate Client Account Balances")
    print("="*60 + "\n")

    all_clients = db.query(Client).all()
    print(f"Processing {len(all_clients)} clients...\n")

    updated_count = 0
    total_corrected = Decimal('0.00')

    for client in all_clients:
        old_balance = client.account_balance

        # Calculate sum of all unpaid invoice balances
        unpaid_invoices = db.query(Invoice).filter(
            Invoice.client_id == client.id,
            Invoice.status != 'paid',
            Invoice.status != 'voided'
        ).all()

        new_balance = sum(Decimal(str(inv.balance_due)) for inv in unpaid_invoices)

        # Update if balance changed
        if old_balance != new_balance:
            client.account_balance = new_balance

            # Only log significant changes (more than a penny)
            if abs(old_balance - new_balance) > Decimal('0.01'):
                # Create activity log
                log = ActivityLog(
                    entity_type="client",
                    entity_id=client.id,
                    client_id=client.id,
                    action="updated",
                    performed_by_id=None,
                    performed_by_name="Balance Recalculation Script",
                    timestamp=datetime.now(),
                    notes=f"Account balance recalculated from {len(unpaid_invoices)} unpaid invoice(s)",
                    previous_value=f"${float(old_balance):.2f}",
                    new_value=f"${float(new_balance):.2f}"
                )
                db.add(log)

            updated_count += 1
            difference = new_balance - old_balance
            total_corrected += difference

            print(f"  • {client.company_name} (ID: {client.id})")
            print(f"    ${float(old_balance):.2f} → ${float(new_balance):.2f} (Δ ${float(difference):+.2f}) [{len(unpaid_invoices)} unpaid invoices]")

    db.commit()
    print(f"\n✓ Updated {updated_count} client balances")
    print(f"✓ Total amount corrected: ${float(total_corrected):+.2f}\n")

    # Verification
    print("="*60)
    print("  Verification")
    print("="*60)

    clients_with_zero_balance_but_unpaid = 0
    total_unpaid = Decimal('0.00')

    for client in all_clients:
        unpaid = db.query(Invoice).filter(
            Invoice.client_id == client.id,
            Invoice.status != 'paid',
            Invoice.status != 'voided'
        ).all()

        unpaid_sum = sum(Decimal(str(inv.balance_due)) for inv in unpaid)
        total_unpaid += unpaid_sum

        if unpaid_sum > 0 and client.account_balance == 0:
            clients_with_zero_balance_but_unpaid += 1

    print(f"Clients with $0.00 balance but unpaid invoices: {clients_with_zero_balance_but_unpaid}")
    print(f"Total outstanding across all clients: ${float(total_unpaid):.2f}\n")

except Exception as ex:
    db.rollback()
    print(f"\n❌ Recalculation FAILED — rolled back.")
    print(f"   Error: {ex}")
    import traceback
    traceback.print_exc()
    raise

finally:
    db.close()
