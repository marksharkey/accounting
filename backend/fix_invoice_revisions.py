#!/usr/bin/env python3
"""
Fix invoices where balance_due > total due to import script skipping revisions.

This happens when:
1. An invoice is revised in QBO (amount increased)
2. The import script skips the revised version (treating it as duplicate)
3. The invoice ends up with original total but AR aging balance_due (the revised amount)

This script detects and fixes these cases.

Usage:
    python3 fix_invoice_revisions.py --dry-run      # Show what would be fixed
    python3 fix_invoice_revisions.py --commit        # Apply fixes
"""

import sys
import os
import argparse
from decimal import Decimal
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
from models import Invoice, InvoiceLineItem, ActivityLog

parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--dry-run", action="store_true", help="Show what would be fixed")
group.add_argument("--commit", action="store_true", help="Apply fixes")
args = parser.parse_args()

DRY_RUN = args.dry_run

print(f"\n{'='*70}")
print(f"  Fix Invoice Revisions (balance_due > total)")
print(f"  {'DRY RUN (no changes)' if DRY_RUN else '*** LIVE COMMIT ***'}")
print(f"{'='*70}\n")

db = SessionLocal()

try:
    # Find all invoices where balance_due > total (data integrity issue)
    problem_invoices = db.query(Invoice).filter(
        Invoice.balance_due > Invoice.total
    ).all()

    if not problem_invoices:
        print("✓ No problem invoices found!")
        sys.exit(0)

    print(f"Found {len(problem_invoices)} invoice(s) with balance_due > total:\n")

    for inv in problem_invoices:
        difference = inv.balance_due - inv.total
        print(f"  Invoice #{inv.invoice_number} ({inv.client.display_name})")
        print(f"    Current total:      ${inv.total:.2f}")
        print(f"    Current balance:    ${inv.balance_due:.2f}")
        print(f"    Difference:         ${difference:.2f}")
        print(f"    Status:             {inv.status}")
        print()

        if not DRY_RUN:
            # Update invoice total to match balance_due (which is from AR aging)
            old_total = inv.total
            inv.subtotal = inv.balance_due
            inv.total = inv.balance_due

            # Add line item for the difference
            revision_item = InvoiceLineItem(
                invoice=inv,
                description=f"Invoice Revision - Additional Charges",
                quantity=Decimal("1"),
                unit_amount=difference,
                amount=difference,
            )
            inv.line_items.append(revision_item)

            # Create activity log
            log = ActivityLog(
                entity_type="invoice",
                entity_id=inv.id,
                client_id=inv.client_id,
                action="updated",
                performed_by_id=None,
                performed_by_name="Revision Fix Script",
                timestamp=datetime.now(),
                notes=f"Fixed invoice revision: total ${old_total:.2f} → ${inv.total:.2f}, added ${difference:.2f} adjustment line item"
            )
            db.add(log)

            db.commit()
            print(f"  ✓ Fixed: total updated to ${inv.total:.2f}")

    if DRY_RUN:
        print("\nNo changes made (dry run). Run with --commit to apply fixes.")
    else:
        print(f"\n✓ Fixed {len(problem_invoices)} invoice(s)")

    print(f"\n{'='*70}\n")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    db.rollback()
    sys.exit(1)

finally:
    db.close()
