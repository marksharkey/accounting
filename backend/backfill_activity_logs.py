#!/usr/bin/env python3
"""
Backfill Activity Logs for Existing Records
Adds "created" activity logs for clients, invoices, billing schedules, and payments
that were imported but don't have activity log entries yet.
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Client, Invoice, BillingSchedule, Payment, ActivityLog

db = SessionLocal()

try:
    print("\n" + "="*60)
    print("  Activity Log Backfill Script")
    print("="*60 + "\n")

    # ── Backfill Clients ──────────────────────────────────────────────────────
    print("Backfilling client activity logs...")
    clients_without_logs = []
    for client in db.query(Client).all():
        # Check if client has any activity logs
        has_log = db.query(ActivityLog).filter(
            ActivityLog.entity_type == "client",
            ActivityLog.entity_id == client.id
        ).first()
        if not has_log:
            clients_without_logs.append(client)

    for client in clients_without_logs:
        log = ActivityLog(
            entity_type="client",
            entity_id=client.id,
            client_id=client.id,
            action="created",
            performed_by_id=None,
            performed_by_name="QBO Import",
            timestamp=client.created_at if client.created_at else datetime.now(),
            notes="Imported from QuickBooks Online (backfilled)"
        )
        db.add(log)

    db.commit()
    print(f"  ✓ Added {len(clients_without_logs)} client activity logs\n")

    # ── Backfill Invoices ─────────────────────────────────────────────────────
    print("Backfilling invoice activity logs...")
    invoices_without_logs = []
    for invoice in db.query(Invoice).all():
        # Check if invoice has any activity logs
        has_log = db.query(ActivityLog).filter(
            ActivityLog.entity_type == "invoice",
            ActivityLog.entity_id == invoice.id
        ).first()
        if not has_log:
            invoices_without_logs.append(invoice)

    for invoice in invoices_without_logs:
        notes = f"Invoice #{invoice.invoice_number} for ${invoice.total:.2f} (due {invoice.due_date}). Imported from QuickBooks Online"
        log = ActivityLog(
            entity_type="invoice",
            entity_id=invoice.id,
            client_id=invoice.client_id,
            action="created",
            performed_by_id=None,
            performed_by_name="QBO Import",
            timestamp=datetime.combine(invoice.created_date, datetime.min.time()),
            notes=notes
        )
        db.add(log)

    db.commit()
    print(f"  ✓ Added {len(invoices_without_logs)} invoice activity logs\n")

    # ── Backfill Billing Schedules ────────────────────────────────────────────
    print("Backfilling billing schedule activity logs...")
    schedules_without_logs = []
    for schedule in db.query(BillingSchedule).all():
        # Check if schedule has any activity logs
        has_log = db.query(ActivityLog).filter(
            ActivityLog.entity_type == "billing_schedule",
            ActivityLog.entity_id == schedule.id
        ).first()
        if not has_log:
            schedules_without_logs.append(schedule)

    for schedule in schedules_without_logs:
        cycle_display = schedule.cycle.replace('_', ' ').title() if schedule.cycle else 'Unknown'
        notes = f"{cycle_display} billing schedule for ${schedule.amount:.2f} (next bill: {schedule.next_bill_date}). Imported from QuickBooks Online"
        log = ActivityLog(
            entity_type="billing_schedule",
            entity_id=schedule.id,
            client_id=schedule.client_id,
            action="created",
            performed_by_id=None,
            performed_by_name="QBO Import",
            timestamp=schedule.created_at if schedule.created_at else datetime.now(),
            notes=notes
        )
        db.add(log)

    db.commit()
    print(f"  ✓ Added {len(schedules_without_logs)} billing schedule activity logs\n")

    # ── Backfill Payments ─────────────────────────────────────────────────────
    print("Backfilling payment activity logs...")
    payments_without_logs = []
    for payment in db.query(Payment).all():
        # Check if payment has any activity logs
        has_log = db.query(ActivityLog).filter(
            ActivityLog.entity_type == "payment",
            ActivityLog.entity_id == payment.id
        ).first()
        if not has_log:
            payments_without_logs.append(payment)

    for payment in payments_without_logs:
        invoice_ref = f"Invoice #{payment.invoice.invoice_number}" if payment.invoice else "Unknown invoice"
        method_display = payment.method.replace('_', ' ').title() if payment.method else 'Unknown method'
        ref_str = f" ({payment.reference_number})" if payment.reference_number else ""
        notes = f"Payment of ${payment.amount:.2f} for {invoice_ref} via {method_display}{ref_str}. Imported from QuickBooks Online"
        log = ActivityLog(
            entity_type="payment",
            entity_id=payment.id,
            client_id=payment.client_id,
            action="created",
            performed_by_id=None,
            performed_by_name="QBO Import",
            timestamp=datetime.combine(payment.payment_date, datetime.min.time()),
            notes=notes
        )
        db.add(log)

    db.commit()
    print(f"  ✓ Added {len(payments_without_logs)} payment activity logs\n")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("="*60)
    print("  Backfill Complete!")
    print("="*60)
    print(f"Total activity logs created: {len(clients_without_logs) + len(invoices_without_logs) + len(schedules_without_logs) + len(payments_without_logs)}\n")

except Exception as ex:
    db.rollback()
    print(f"\n❌ Backfill FAILED — rolled back.")
    print(f"   Error: {ex}")
    import traceback
    traceback.print_exc()
    raise

finally:
    db.close()
