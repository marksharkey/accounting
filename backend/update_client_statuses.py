#!/usr/bin/env python3
"""
Update Client Account Statuses Based on Invoice Status
Updates client status to 'overdue' if they have unpaid invoices past due,
otherwise sets to 'active' (unless they are suspended or deleted).
"""

import sys
import os
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Client, Invoice, AccountStatus, ActivityLog

db = SessionLocal()

try:
    print("\n" + "="*60)
    print("  Update Client Account Statuses")
    print("="*60 + "\n")

    all_clients = db.query(Client).all()
    print(f"Processing {len(all_clients)} clients...\n")

    updated_count = 0
    overdue_count = 0
    active_count = 0
    suspended_count = 0
    deleted_count = 0

    for client in all_clients:
        old_status = client.account_status
        today = date.today()

        # Check if client has any past due unpaid invoices
        past_due_invoices = db.query(Invoice).filter(
            Invoice.client_id == client.id,
            Invoice.due_date < today,
            Invoice.status != 'paid',
            Invoice.status != 'voided'
        ).all()

        # Determine new status
        if len(past_due_invoices) > 0:
            new_status = AccountStatus.overdue
        elif client.account_status == 'suspended':
            # Keep suspended status if explicitly set
            new_status = AccountStatus.suspended
        elif client.account_status == 'deleted':
            # Keep deleted status if explicitly set
            new_status = AccountStatus.deleted
        else:
            # Default to active
            new_status = AccountStatus.active

        # Update if status changed
        if old_status != new_status:
            client.account_status = new_status

            # Create activity log
            log = ActivityLog(
                entity_type="client",
                entity_id=client.id,
                client_id=client.id,
                action="status_changed",
                performed_by_id=None,
                performed_by_name="Status Update Script",
                timestamp=datetime.now(),
                notes=f"Status updated based on invoice status: {len(past_due_invoices)} past due unpaid invoice(s)",
                previous_value=str(old_status.value),
                new_value=str(new_status.value)
            )
            db.add(log)
            updated_count += 1

            print(f"  • {client.company_name} (ID: {client.id}): {old_status.value} → {new_status.value}")
            if len(past_due_invoices) > 0:
                print(f"    └─ {len(past_due_invoices)} past due unpaid invoice(s)")

        # Count final statuses
        if new_status == AccountStatus.overdue:
            overdue_count += 1
        elif new_status == AccountStatus.active:
            active_count += 1
        elif new_status == AccountStatus.suspended:
            suspended_count += 1
        elif new_status == AccountStatus.deleted:
            deleted_count += 1

    db.commit()
    print(f"\n✓ Updated {updated_count} client statuses\n")

    # Summary
    print("="*60)
    print("  Status Summary")
    print("="*60)
    print(f"Active:     {active_count} clients")
    print(f"Overdue:    {overdue_count} clients")
    print(f"Suspended:  {suspended_count} clients")
    print(f"Deleted:    {deleted_count} clients")
    print(f"Total:      {len(all_clients)} clients\n")

except Exception as ex:
    db.rollback()
    print(f"\n❌ Update FAILED — rolled back.")
    print(f"   Error: {ex}")
    import traceback
    traceback.print_exc()
    raise

finally:
    db.close()
