#!/usr/bin/env python3
"""
Export data from local database to be imported on production server
"""
import json
import sys
from datetime import datetime, date
from decimal import Decimal
from database import SessionLocal
from models import Base

class DataEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def export_data():
    db = SessionLocal()
    export = {}

    total_records = 0

    # Export all tables in dependency order
    table_order = [
        'users',
        'company_info',
        'chart_of_accounts',
        'service_catalog',
        'clients',
        'billing_schedules',
        'billing_schedule_line_items',
        'invoices',
        'invoice_line_items',
        'estimates',
        'estimate_line_items',
        'credit_memos',
        'credit_line_items',
        'payments',
        'expenses',
        'bank_accounts',
        'bank_transactions',
        'bank_reconciliations',
        'journal_entries',
        'collections_events',
        'activity_log',
        'email_templates',
        'domains',
        'invoice_sequences',
    ]

    for mapper in Base.registry.mappers:
        model_class = mapper.class_
        table_name = model_class.__tablename__

        try:
            records = db.query(model_class).all()
            if records:
                # Convert to dicts with column names
                export[table_name] = []
                for record in records:
                    row = {}
                    for col in model_class.__table__.columns:
                        row[col.name] = getattr(record, col.name)
                    export[table_name].append(row)

                total_records += len(records)
                print(f"✓ {table_name}: {len(records)} records")
            else:
                print(f"  {table_name}: empty")
        except Exception as e:
            print(f"✗ {table_name}: {e}")

    db.close()

    print(f"\nTotal records exported: {total_records}")

    # Write to JSON file
    with open('/tmp/accounting_export.json', 'w') as f:
        json.dump(export, f, cls=DataEncoder, indent=2)

    print("✓ Exported to /tmp/accounting_export.json")
    return export

if __name__ == '__main__':
    export_data()
