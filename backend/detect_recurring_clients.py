#!/usr/bin/env python3
"""
Detect recurring clients from invoice history and create billing schedules.

Analyzes invoice patterns to identify clients with regular billing cycles,
then creates billing schedules with line items from their most recent invoice.

Usage:
    python3 detect_recurring_clients.py --analyze    # Show candidates
    python3 detect_recurring_clients.py --create     # Create schedules
"""

import sys
import os
import argparse
from datetime import datetime, date, timedelta
from decimal import Decimal
from collections import defaultdict
from statistics import mean, stdev

parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--analyze", action="store_true", help="Analyze patterns and show candidates")
group.add_argument("--create", action="store_true", help="Create billing schedules for identified clients")
args = parser.parse_args()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
from models import Client, Invoice, BillingSchedule, BillingScheduleLineItem, ActivityLog
from sqlalchemy import func

db = SessionLocal()

def analyze_invoice_pattern(invoices):
    """
    Analyze invoice dates to detect recurring patterns.
    Returns: (cycle_days, confidence, regularity_score) or (None, 0, 0) if no pattern
    """
    if len(invoices) < 2:
        return None, 0, 0

    # Calculate days between consecutive invoices
    invoice_dates = sorted([inv.created_date for inv in invoices])
    intervals = []
    for i in range(1, len(invoice_dates)):
        delta = (invoice_dates[i] - invoice_dates[i-1]).days
        intervals.append(delta)

    if not intervals:
        return None, 0, 0

    avg_interval = mean(intervals)
    std_dev = stdev(intervals) if len(intervals) > 1 else 0

    # Categorize by typical billing cycles
    cycle_map = {
        30: ("monthly", 30),      # ±15 days tolerance
        90: ("quarterly", 45),    # ±22 days tolerance
        180: ("semi_annual", 90), # ±45 days tolerance
        365: ("annual", 90),      # ±90 days tolerance
    }

    best_cycle = None
    best_confidence = 0

    for target_days, (cycle_name, tolerance) in cycle_map.items():
        # Count intervals within tolerance
        matching = sum(1 for i in intervals if abs(i - target_days) <= tolerance)
        confidence = matching / len(intervals)

        if confidence > best_confidence:
            best_confidence = confidence
            best_cycle = cycle_name

    # Calculate regularity: 1.0 is perfectly regular, lower is more sporadic
    # (std_dev near 0 means very consistent)
    regularity = max(0, 1.0 - min(1.0, std_dev / 60))  # normalize to 0-1

    return best_cycle, best_confidence, regularity


def detect_recurring_clients():
    """Find all clients with recurring invoice patterns."""

    clients = db.query(Client).filter(Client.is_active == True).all()
    candidates = []

    print("\nAnalyzing invoice patterns...\n")

    for client in clients:
        invoices = db.query(Invoice).filter(
            Invoice.client_id == client.id
        ).order_by(Invoice.created_date).all()

        if len(invoices) < 3:  # Need at least 3 invoices to detect a pattern
            continue

        # Check if they already have a schedule
        existing_schedule = db.query(BillingSchedule).filter(
            BillingSchedule.client_id == client.id
        ).first()
        if existing_schedule:
            continue

        cycle, confidence, regularity = analyze_invoice_pattern(invoices)

        if cycle and confidence >= 0.6 and regularity >= 0.5:  # Threshold: 60% matching + 50% regularity
            # Get invoice amounts to check consistency
            amounts = [inv.subtotal for inv in invoices[-6:]]  # Last 6 invoices
            avg_amount = mean(amounts)
            amount_variance = (max(amounts) - min(amounts)) / avg_amount if avg_amount > 0 else 0

            # Most recent invoice for line items
            recent_invoice = invoices[-1]

            candidates.append({
                'client': client,
                'cycle': cycle,
                'confidence': confidence,
                'regularity': regularity,
                'invoices': len(invoices),
                'avg_amount': avg_amount,
                'amount_variance': amount_variance,
                'recent_invoice': recent_invoice,
                'intervals': [
                    (invoices[i].created_date - invoices[i-1].created_date).days
                    for i in range(1, len(invoices))
                ]
            })

    # Sort by confidence * regularity (best candidates first)
    candidates.sort(key=lambda c: c['confidence'] * c['regularity'], reverse=True)

    return candidates


# ── ANALYZE MODE ──────────────────────────────────────────────────────────────
if args.analyze:
    candidates = detect_recurring_clients()

    print(f"{'='*100}")
    print(f"  RECURRING CLIENT DETECTION — {len(candidates)} candidates found")
    print(f"{'='*100}\n")

    if not candidates:
        print("No candidates found.")
        sys.exit(0)

    print(f"{'Client':<40} {'Cycle':<12} {'Conf':<6} {'Reg':<6} {'Amt Var':<8} {'Recent':<10}")
    print(f"{'-'*100}")

    for c in candidates:
        client_name = c['client'].company_name[:39]
        recent_date = c['recent_invoice'].created_date
        print(f"{client_name:<40} {c['cycle']:<12} {c['confidence']:.1%}  {c['regularity']:.1%}  {c['amount_variance']:.1%}    {recent_date}")

    print(f"\n{'-'*100}")
    print(f"Confidence: How many intervals match the expected cycle")
    print(f"Regularity: How consistent the intervals are (1.0 = perfectly regular)")
    print(f"Amt Var:    Variance in invoice amounts (lower is more consistent)")
    print()
    print(f"Run with --create to generate billing schedules for these {len(candidates)} clients.\n")


# ── CREATE MODE ───────────────────────────────────────────────────────────────
elif args.create:
    candidates = detect_recurring_clients()

    print(f"\n{'='*100}")
    print(f"  CREATING BILLING SCHEDULES — {len(candidates)} clients")
    print(f"{'='*100}\n")

    if not candidates:
        print("No candidates found.")
        sys.exit(0)

    created = 0
    skipped = 0

    for candidate in candidates:
        client = candidate['client']
        recent_inv = candidate['recent_invoice']

        print(f"→ {client.company_name:<40}", end=" ")

        try:
            # Determine next bill date based on cycle
            today = date.today()
            cycle = candidate['cycle']

            if cycle == 'monthly':
                # Next month, same day
                if today.month == 12:
                    next_date = today.replace(year=today.year + 1, month=1, day=1)
                else:
                    next_date = today.replace(month=today.month + 1, day=1)
            elif cycle == 'quarterly':
                # 3 months out
                month = today.month + 3
                year = today.year
                while month > 12:
                    month -= 12
                    year += 1
                next_date = today.replace(year=year, month=month, day=1)
            elif cycle == 'semi_annual':
                # 6 months out
                month = today.month + 6
                year = today.year
                while month > 12:
                    month -= 12
                    year += 1
                next_date = today.replace(year=year, month=month, day=1)
            elif cycle == 'annual':
                # 1 year out
                next_date = today.replace(year=today.year + 1, month=1, day=1)

            # Create billing schedule
            total_amount = Decimal("0.00")
            line_items_data = []

            for li in recent_inv.line_items:
                total_amount += Decimal(str(li.amount))
                line_items_data.append({
                    'description': li.description,
                    'quantity': li.quantity,
                    'unit_amount': li.unit_amount,
                    'service_id': li.service_id,
                })

            schedule = BillingSchedule(
                client_id=client.id,
                amount=total_amount,
                cycle=cycle,
                next_bill_date=next_date,
                autocc_recurring=False,
                is_active=True,
                notes=f"Auto-generated from invoice history (source: #{recent_inv.invoice_number})"
            )
            db.add(schedule)
            db.flush()

            # Add line items
            for i, li_data in enumerate(line_items_data):
                qty = Decimal(str(li_data['quantity']))
                unit_amt = Decimal(str(li_data['unit_amount']))
                line_item = BillingScheduleLineItem(
                    billing_schedule_id=schedule.id,
                    description=li_data['description'],
                    quantity=qty,
                    unit_amount=unit_amt,
                    amount=qty * unit_amt,
                    service_id=li_data['service_id'],
                    sort_order=i
                )
                db.add(line_item)

            # Log the action
            log = ActivityLog(
                entity_type="billing_schedule",
                entity_id=schedule.id,
                client_id=client.id,
                action="created",
                performed_by_id=None,
                performed_by_name="Auto-detect Script",
                notes=f"Auto-generated from {len(recent_inv.line_items)} line items in invoice #{recent_inv.invoice_number}"
            )
            db.add(log)

            print(f"✓ {candidate['cycle']:<12} ${total_amount:>8.2f}  ({len(line_items_data)} items)")
            created += 1

        except Exception as e:
            print(f"✗ Error: {e}")
            skipped += 1

    db.commit()
    db.close()

    print(f"\n{'='*100}")
    print(f"✅ Created {created} billing schedules")
    if skipped:
        print(f"⚠️  Skipped {skipped} due to errors")
    print(f"{'='*100}\n")
