#!/usr/bin/env python3
"""
Import data exported from local database to production server
"""
import json
import sys
from datetime import datetime
from database import SessionLocal, engine
from models import Base
from sqlalchemy import inspect, MetaData, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def import_data(json_file):
    # First, recreate schema
    logger.info("Recreating database schema...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    logger.info("✓ Schema created")

    # Load JSON data
    logger.info(f"Loading data from {json_file}...")
    with open(json_file, 'r') as f:
        data = json.load(f)

    db = SessionLocal()
    total_imported = 0

    try:
        # Disable foreign key checks during import
        db.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        logger.info("Disabled foreign key checks")

        # Truncate all tables
        logger.info("Truncating existing tables...")
        for mapper in Base.registry.mappers:
            table_name = mapper.class_.__tablename__
            db.execute(text(f"TRUNCATE TABLE `{table_name}`"))
        db.commit()
        logger.info("✓ Tables truncated")
        # Get all model classes indexed by table name
        models_by_table = {}
        for mapper in Base.registry.mappers:
            models_by_table[mapper.class_.__tablename__] = mapper.class_

        # Import tables in dependency order
        table_order = [
            'users',
            'company_info',
            'chart_of_accounts',
            'service_catalog',
            'clients',
            'email_templates',
            'domains',
            'invoice_sequences',
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
        ]

        for table_name in table_order:
            if table_name not in data or not data[table_name]:
                continue

            model_class = models_by_table.get(table_name)
            if not model_class:
                logger.warning(f"✗ {table_name}: model not found")
                continue

            records = data[table_name]
            imported_count = 0
            skipped_count = 0

            # Handle duplicates for invoices (by invoice_number)
            if table_name == 'invoices':
                seen_numbers = set()
                filtered_records = []
                for row in records:
                    inv_num = row.get('invoice_number')
                    if inv_num in seen_numbers:
                        logger.warning(f"  Skipping duplicate invoice_number: {inv_num}")
                        skipped_count += 1
                    else:
                        seen_numbers.add(inv_num)
                        filtered_records.append(row)
                records = filtered_records

            for row in records:
                try:
                    # Create instance from row data
                    obj = model_class(**row)
                    db.add(obj)
                    imported_count += 1
                except Exception as e:
                    logger.error(f"  {table_name}: {e} - row: {row}")
                    db.rollback()
                    raise

            db.commit()
            total_imported += imported_count
            if skipped_count > 0:
                logger.info(f"✓ {table_name}: {imported_count} imported, {skipped_count} skipped")
            else:
                logger.info(f"✓ {table_name}: {imported_count} records")

        logger.info(f"\n✓ Total imported: {total_imported} records")

        # Re-enable foreign key checks
        db.execute(text("SET FOREIGN_KEY_CHECKS=1"))
        db.commit()
        logger.info("✓ Re-enabled foreign key checks")

    except Exception as e:
        logger.error(f"Import failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == '__main__':
    json_file = sys.argv[1] if len(sys.argv) > 1 else '/tmp/accounting_export.json'
    import_data(json_file)
