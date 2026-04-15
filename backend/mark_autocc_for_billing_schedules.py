#!/usr/bin/env python3
"""
Mark Clients with Billing Schedules as AutoCC Active
Sets autocc_recurring=True for all clients that have active billing schedules.
Also logs the activity changes.
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Client, BillingSchedule, ActivityLog
from sqlalchemy import func

db = SessionLocal()

try:
    print("\n" + "="*60)
    print("  Mark AutoCC Active for Billing Schedule Clients")
    print("="*60 + "\n")

    # Find all clients with active billing schedules
    clients_with_schedules = db.query(Client).join(
        BillingSchedule, Client.id == BillingSchedule.client_id
    ).filter(
        BillingSchedule.is_active == True
    ).distinct().all()

    print(f"Found {len(clients_with_schedules)} clients with active billing schedules\n")

    # Mark them as autocc active and log the change
    updated_count = 0
    for client in clients_with_schedules:
        # Only update if not already marked
        if not client.autocc_recurring:
            print(f"  • {client.company_name} (ID: {client.id})")

            # Update the client
            client.autocc_recurring = True

            # Log the activity
            log = ActivityLog(
                entity_type="client",
                entity_id=client.id,
                client_id=client.id,
                action="updated",
                performed_by_id=None,
                performed_by_name="Migration Script",
                timestamp=datetime.now(),
                notes="Marked as AutoCC Active (has billing schedule)",
                previous_value="false",
                new_value="true"
            )
            db.add(log)
            updated_count += 1

    db.commit()
    print(f"\n✓ Updated {updated_count} clients to autocc_recurring=True\n")

    # Summary
    print("="*60)
    print("  Migration Complete!")
    print("="*60)
    print(f"Clients with billing schedules: {len(clients_with_schedules)}")
    print(f"Clients updated to autocc active: {updated_count}\n")

except Exception as ex:
    db.rollback()
    print(f"\n❌ Migration FAILED — rolled back.")
    print(f"   Error: {ex}")
    import traceback
    traceback.print_exc()
    raise

finally:
    db.close()
