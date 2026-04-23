#!/usr/bin/env python3
"""
Import QBO Product/Service List and link services to income accounts
Maps QBO income account names to database chart_of_accounts codes
"""

import xlrd
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import models
from config import get_settings

settings = get_settings()

# Mapping from QBO Income Account name to database ChartOfAccount code
QBO_TO_DB_MAPPING = {
    'Web Hosting': '4100',
    'Email Hosting': '4100',
    'Domain Name Registrations': '4100',
    'Managed Servers': '4200',
    'Server Management Fees': '4200',
    'Web Programming': '4300',
    'Consulting Revenue': '4300',
    'Services': '4100',
    'Bad Debt': '4100',
    'Uncategorized Expenses': '4100',
    'Uncategorized Income {23}': '4100',
}

def import_qbo_services(excel_path):
    """Import services from QBO Excel file and link to income accounts"""

    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Read Excel file
        wb = xlrd.open_workbook(excel_path)
        ws = wb.sheet_by_index(0)

        print(f"Reading services from: {excel_path}")
        print(f"Sheet: {ws.name}, Rows: {ws.nrows}")

        updated = 0
        not_found = []

        # Skip header row
        for row_idx in range(1, ws.nrows):
            service_name = ws.cell_value(row_idx, 0)
            qbo_account = ws.cell_value(row_idx, 5)

            if not service_name or not qbo_account:
                continue

            # Find the database chart of account code
            db_code = QBO_TO_DB_MAPPING.get(qbo_account)
            if not db_code:
                print(f"⚠️  Unknown QBO account: {qbo_account}")
                db_code = '4100'  # Default to Web Hosting

            # Find the service in database
            service = session.query(models.ServiceCatalog).filter_by(name=service_name).first()

            if service:
                # Find the chart of account
                coa = session.query(models.ChartOfAccount).filter_by(code=db_code).first()
                if coa:
                    service.income_account_id = coa.id
                    updated += 1
                    print(f"✓ {service_name:40} → {coa.code} {coa.name}")
                else:
                    print(f"✗ Chart of account not found: {db_code}")
            else:
                not_found.append(service_name)

        session.commit()

        print(f"\n{'='*70}")
        print(f"Updated: {updated} services")
        if not_found:
            print(f"Not found in database: {len(not_found)}")
            for name in not_found[:5]:
                print(f"  - {name}")

    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    excel_path = "/Users/marksharkey/Downloads/ProductServiceList__9341456449516862_04_19_2026.xls"
    import_qbo_services(excel_path)
