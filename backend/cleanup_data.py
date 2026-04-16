#!/usr/bin/env python3
"""
Data cleanup script — PrecisionPros Billing
Fixes imported invoice line items where amount != quantity * unit_amount.
Strategy: set unit_amount = amount / quantity (preserve what was actually charged).

Usage:
    python3 cleanup_data.py --dry-run
    python3 cleanup_data.py --commit
"""

import sys
import os
import argparse
from decimal import Decimal, ROUND_HALF_UP

parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--dry-run", action="store_true")
group.add_argument("--commit",  action="store_true")
args = parser.parse_args()

DRY_RUN = args.dry_run

print(f"\n{'='*60}")
print(f"  Data Cleanup — {'DRY RUN (no changes)' if DRY_RUN else '*** LIVE COMMIT ***'}")
print(f"{'='*60}\n")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
from models import InvoiceLineItem, Invoice, BillingScheduleLineItem, BillingSchedule

db = SessionLocal()

try:
    # ── Fix 1: Invoice line items — set unit_amount = amount / qty ────────────
    print("── Fix 1: Invoice line item unit prices ─────────────────")
    bad_lines = db.query(InvoiceLineItem).all()
    fix1_count = 0
    fix1_examples = []

    for li in bad_lines:
        qty      = Decimal(str(li.quantity))
        amount   = Decimal(str(li.amount)).quantize(Decimal("0.01"))
        expected_unit = (amount / qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if qty else Decimal("0.00")
        actual_unit  = Decimal(str(li.unit_amount)).quantize(Decimal("0.01"))

        if expected_unit != actual_unit:
            fix1_count += 1
            if len(fix1_examples) < 5:
                inv = db.query(Invoice).filter(Invoice.id == li.invoice_id).first()
                fix1_examples.append(
                    f"  #{inv.invoice_number if inv else li.invoice_id} — "
                    f"{li.description[:38]:<38} "
                    f"qty={qty} amt=${amount}  unit_price: ${actual_unit} → ${expected_unit}"
                )
            if not DRY_RUN:
                li.unit_amount = expected_unit

    print(f"  Line items to fix: {fix1_count}")
    for ex in fix1_examples:
        print(ex)
    if fix1_count > 5:
        print(f"  ... and {fix1_count - 5} more")
    print()

    # ── Fix 2: Invoice subtotals that don't match sum of line items ───────────
    print("── Fix 2: Invoice subtotals vs line item sums ───────────")
    invoices = db.query(Invoice).all()
    fix2_count = 0
    fix2_examples = []

    for inv in invoices:
        if not inv.line_items:
            continue
        line_sum    = sum(Decimal(str(li.amount)) for li in inv.line_items).quantize(Decimal("0.01"))
        inv_subtotal = Decimal(str(inv.subtotal)).quantize(Decimal("0.01"))

        if line_sum != inv_subtotal:
            fix2_count += 1
            if len(fix2_examples) < 5:
                fix2_examples.append(
                    f"  #{inv.invoice_number} subtotal={inv_subtotal} → {line_sum}"
                )
            if not DRY_RUN:
                late_fee = Decimal(str(inv.late_fee_amount or 0))
                inv.subtotal    = line_sum
                inv.total       = line_sum + late_fee
                inv.balance_due = inv.total - Decimal(str(inv.amount_paid or 0))

    print(f"  Invoices to fix: {fix2_count}")
    for ex in fix2_examples:
        print(ex)
    print()

    # ── Fix 3: Billing schedule line items ────────────────────────────────────
    print("── Fix 3: Billing schedule line item unit prices ────────")
    bs_lines  = db.query(BillingScheduleLineItem).all()
    fix3_count = 0

    for li in bs_lines:
        qty      = Decimal(str(li.quantity))
        amount   = Decimal(str(li.amount)).quantize(Decimal("0.01"))
        expected_unit = (amount / qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if qty else Decimal("0.00")
        actual_unit  = Decimal(str(li.unit_amount)).quantize(Decimal("0.01"))

        if expected_unit != actual_unit:
            fix3_count += 1
            if not DRY_RUN:
                li.unit_amount = expected_unit

    print(f"  Billing schedule line items to fix: {fix3_count}")
    print()

    # ── Fix 4: Billing schedule totals ───────────────────────────────────────
    print("── Fix 4: Billing schedule totals ───────────────────────")
    schedules  = db.query(BillingSchedule).all()
    fix4_count = 0

    for sched in schedules:
        if not sched.line_items:
            continue
        line_sum  = sum(Decimal(str(li.amount)) for li in sched.line_items).quantize(Decimal("0.01"))
        sched_amt = Decimal(str(sched.amount)).quantize(Decimal("0.01"))
        if line_sum != sched_amt:
            fix4_count += 1
            if not DRY_RUN:
                sched.amount = line_sum

    print(f"  Billing schedules to fix: {fix4_count}")
    print()

    # ── Summary ───────────────────────────────────────────────────────────────
    total = fix1_count + fix2_count + fix3_count + fix4_count
    print(f"{'─'*60}")
    print(f"  Total fixes: {total}")
    print()

    if DRY_RUN:
        print("✅ DRY RUN complete — no changes made.")
        print("   Run with --commit to apply fixes.\n")
    else:
        db.commit()
        print("✅ Cleanup complete — all fixes committed.\n")

except Exception as ex:
    db.rollback()
    print(f"\n❌ Cleanup FAILED — rolled back.")
    print(f"   Error: {ex}")
    import traceback; traceback.print_exc()
    raise

finally:
    db.close()
