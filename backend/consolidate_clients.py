#!/usr/bin/env python3
"""
Consolidate duplicate clients to match QBO structure.
This reassigns invoices from secondary clients to primary clients.
"""

import sys
sys.path.insert(0, '/Users/marksharkey/accounting/backend')

from database import SessionLocal
import models

# Client consolidations: (primary_id, secondary_id)
# Using IDs from database for accuracy
CONSOLIDATIONS = [
    (64, 65),  # Enterprise Communications <- Enterprise Communications:echost.com
    (76, 77),  # Frick, Mike <- Frick, Mike:onlearn
    (66, 67),  # ERC <- ERC:erc programming
    (169, 170),  # Sommer, Eric <- Sommer, Eric:icapture.com
    # Note: Atlantis Travel Agency, Athens (21) and sancarlosproperty.com (159) only have one entry each
]

db = SessionLocal()

print("=" * 100)
print("CLIENT CONSOLIDATION PLAN")
print("=" * 100)

for primary_id, secondary_id in CONSOLIDATIONS:
    primary = db.query(models.Client).filter_by(id=primary_id).first()
    secondary = db.query(models.Client).filter_by(id=secondary_id).first()

    if not primary:
        print(f"\n❌ PRIMARY CLIENT NOT FOUND: {primary_id}")
        continue
    if not secondary:
        print(f"\n⚠️  SECONDARY CLIENT NOT FOUND: {secondary_id}")
        continue

    # Count invoices for each
    primary_invs = db.query(models.Invoice).filter_by(client_id=primary.id).count()
    secondary_invs = db.query(models.Invoice).filter_by(client_id=secondary.id).count()

    # Get totals
    primary_total = db.query(models.Invoice).filter_by(client_id=primary.id).all()
    primary_balance = sum(float(inv.balance_due) for inv in primary_total)

    secondary_total = db.query(models.Invoice).filter_by(client_id=secondary.id).all()
    secondary_balance = sum(float(inv.balance_due) for inv in secondary_total)

    print(f"\n✓ {primary.display_name}")
    print(f"  Primary (ID: {primary.id}): {primary_invs} invoices, Balance: ${primary_balance:.2f}")
    print(f"  ← {secondary.display_name} (ID: {secondary.id}): {secondary_invs} invoices, Balance: ${secondary_balance:.2f}")
    print(f"  Combined balance after merge: ${primary_balance + secondary_balance:.2f}")

print("\n" + "=" * 100)
print("To execute the consolidation, run:")
print("python3 consolidate_clients.py --execute")
print("=" * 100)

# Execute consolidation if --execute flag is present
if len(sys.argv) > 1 and sys.argv[1] == "--execute":
    print("\nExecuting consolidation...")

    for primary_id, secondary_id in CONSOLIDATIONS:
        primary = db.query(models.Client).filter_by(id=primary_id).first()
        secondary = db.query(models.Client).filter_by(id=secondary_id).first()

        if not primary or not secondary:
            continue

        # Move all invoices from secondary to primary
        invoices = db.query(models.Invoice).filter_by(client_id=secondary.id).all()
        count = len(invoices)

        for inv in invoices:
            inv.client_id = primary.id

        # Deactivate secondary client
        secondary.account_status = models.AccountStatus.deleted

        db.commit()
        print(f"✓ Moved {count} invoices from {secondary.display_name} to {primary.display_name}")

    print("\n✓ Consolidation complete!")
    print("The secondary clients have been marked as deleted.")

db.close()
