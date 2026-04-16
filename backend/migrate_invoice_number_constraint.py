#!/usr/bin/env python3
"""
Migration: Allow duplicate invoice numbers for different customers

Change unique constraint on invoices.invoice_number from:
  UNIQUE (invoice_number)
to:
  UNIQUE (client_id, invoice_number)

This allows QB Desktop and QBO invoices with the same number but different customers.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from database import SessionLocal

print(f"\n{'='*70}")
print(f"  Migrating Invoice Unique Constraint")
print(f"  Current: UNIQUE (invoice_number)")
print(f"  New:     UNIQUE (client_id, invoice_number)")
print(f"{'='*70}\n")

try:
    db = SessionLocal()

    print("Step 1: Drop existing unique constraint on invoice_number...")
    try:
        db.execute(text("ALTER TABLE invoices DROP INDEX invoice_number"))
        db.commit()
        print("  ✓ Dropped\n")
    except Exception as e:
        if "check that column/key exists" in str(e):
            print("  ⚠ Index not found (already dropped?)\n")
        else:
            db.rollback()
            raise

    print("Step 2: Add new unique constraint (client_id, invoice_number)...")
    db.execute(text("""
        ALTER TABLE invoices
        ADD UNIQUE KEY uk_client_invoice_number (client_id, invoice_number)
    """))
    db.commit()
    print("  ✓ Added\n")

    print(f"{'='*70}")
    print(f"✅ Migration complete!")
    print(f"{'='*70}\n")

    db.close()

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
