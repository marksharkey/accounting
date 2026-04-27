#!/usr/bin/env python3
"""
Create CreditMemo records for client overpayments from QB Desktop migration.
These represent credits from clients that paid more than their invoices.

Usage:
    python3 create_overpayment_credits.py --dry-run
    python3 create_overpayment_credits.py --commit
"""

import sys
import argparse
sys.path.insert(0, '.')
from database import SessionLocal
import models
from datetime import date

# Parse arguments
parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--dry-run", action="store_true")
group.add_argument("--commit", action="store_true")
args = parser.parse_args()

DRY_RUN = args.dry_run

# Overpayments to create: (client_name, amount)
OVERPAYMENTS = [
    ("zhost", 45.20),
    ("Whiteent", 25.00),
    ("L F Rothchild", 50.00),
    ("SteamworksAZ", 59.80),
    ("Hawaii Health Guide", 1.00),
    ("Sommer, Eric", 4.00),
]

db = SessionLocal()

print("=" * 100)
print("CREATING CREDIT MEMO RECORDS FOR OVERPAYMENTS")
print("=" * 100)

created_count = 0

for client_name, amount in OVERPAYMENTS:
    # Find or create client
    client = db.query(models.Client).filter_by(display_name=client_name).first()

    if not client:
        print(f"\n⚠️  Client not found: {client_name}")
        print("   Creating client record...")

        # Create client with minimal info
        client = models.Client(
            company_name=client_name,
            display_name=client_name,
            email="unknown@example.com",  # Required field
            account_status=models.AccountStatus.active
        )
        db.add(client)
        db.commit()
        print(f"   ✓ Created client: {client_name}")

    # Generate memo number
    existing_count = db.query(models.CreditMemo).filter_by(client_id=client.id).count()
    memo_number = f"CM-{client.id:03d}-{existing_count + 1:03d}"

    # Create CreditMemo record
    credit_memo = models.CreditMemo(
        memo_number=memo_number,
        client_id=client.id,
        total=amount,
        reason="Overpayment from QB Desktop migration",
        status=models.CreditMemoStatus.applied,  # Already applied as overpayment
        created_date=date.today(),
        applied_to_invoice_id=None,  # Not applied to specific invoice
    )

    db.add(credit_memo)
    db.commit()

    # Create line item for the credit
    line_item = models.CreditLineItem(
        credit_memo_id=credit_memo.id,
        description="Overpayment credit",
        quantity=1,
        unit_amount=amount,
        amount=amount,
        sort_order=0
    )
    db.add(line_item)
    if not DRY_RUN:
        db.commit()

    print(f"\n✓ Created CreditMemo for {client.display_name}")
    print(f"  Memo #: {memo_number}")
    print(f"  Amount: ${amount:.2f}")
    print(f"  Status: applied")
    created_count += 1

if DRY_RUN:
    db.rollback()
    print("\n" + "=" * 100)
    print("📋 DRY RUN (no changes committed)")
else:
    print("\n" + "=" * 100)
    print("✅ Credit memos created")

print(f"RESULTS: Created {created_count} CreditMemo records")
print("=" * 100)

db.close()
