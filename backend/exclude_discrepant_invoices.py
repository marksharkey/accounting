#!/usr/bin/env python3
"""
Exclude the 37 discrepant invoices from AR aging report.
"""

import sys
sys.path.insert(0, '/Users/marksharkey/accounting/backend')

from database import SessionLocal
import models

# Invoice IDs to exclude (from generate_exclusion_script.py output)
INVOICE_IDS = [
    4021, 3981, 4007, 264, 3928, 3922, 3924, 4001, 3926, 4011,
    2478, 2651, 3655, 3794, 3881, 3912, 4002, 4004, 208, 516,
    4020, 3960, 4022, 4015, 1117, 3835, 4018, 109, 422, 710,
    1016, 1352, 2238, 2570, 3642, 4019, 110
]

db = SessionLocal()

print("=" * 100)
print("EXCLUDING DISCREPANT INVOICES FROM AR AGING REPORT")
print("=" * 100)

# Update invoices
excluded_count = 0
not_found = []

for inv_id in INVOICE_IDS:
    invoice = db.query(models.Invoice).filter_by(id=inv_id).first()
    if invoice:
        invoice.exclude_from_ar_aging = True
        excluded_count += 1
        print(f"✓ Excluded invoice #{invoice.invoice_number} (ID: {inv_id}) - Client: {invoice.client.display_name}")
    else:
        not_found.append(inv_id)
        print(f"✗ Invoice not found: ID {inv_id}")

db.commit()

print("\n" + "=" * 100)
print(f"RESULTS: Excluded {excluded_count} invoices")
if not_found:
    print(f"Not found: {len(not_found)} invoices")
print("=" * 100)

db.close()
