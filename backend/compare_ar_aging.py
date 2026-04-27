#!/usr/bin/env python3
"""
Compare AR Aging data between QBO export and current database.
Shows discrepancies that need to be excluded from reports.
"""

import csv
from datetime import date
from decimal import Decimal
import sys
sys.path.insert(0, '/Users/marksharkey/accounting/backend')

from database import SessionLocal
import models

def parse_qbo_csv(csv_path):
    """Parse QBO AR Aging export. Returns {client_name: {aging_bucket: amount}}"""
    qbo_data = {}

    with open(csv_path) as f:
        reader = csv.DictReader(f, fieldnames=['Client', 'Current', '1-30', '31-60', '61-90', '91+', 'Total'])
        for i, row in enumerate(reader):
            if i < 5 or not row['Client'] or row['Client'].startswith('TOTAL') or 'Total for' in row['Client']:
                continue

            client_name = row['Client'].strip()
            if not client_name:
                continue

            # Skip subtotal rows
            if f"Total for" in client_name:
                continue

            try:
                current = float(row['Current'].replace(',', '') or 0)
                aged_1_30 = float(row['1-30'].replace(',', '') or 0)
                aged_31_60 = float(row['31-60'].replace(',', '') or 0)
                aged_61_90 = float(row['61-90'].replace(',', '') or 0)
                aged_91_plus = float(row['91+'].replace(',', '') or 0)
                total = float(row['Total'].replace(',', '') or 0)

                qbo_data[client_name] = {
                    'current': current,
                    '1_30': aged_1_30,
                    '31_60': aged_31_60,
                    '61_90': aged_61_90,
                    'over_90': aged_91_plus,
                    'total': total,
                }
            except (ValueError, TypeError):
                pass

    return qbo_data

def get_app_ar_aging(as_of=None, exclude_excluded=True):
    """Get AR Aging from app database. Returns {client_name: {aging_bucket: amount}}"""
    as_of = as_of or date.today()
    db = SessionLocal()

    query = db.query(models.Invoice).filter(
        models.Invoice.status.in_([
            models.InvoiceStatus.sent,
            models.InvoiceStatus.partially_paid
        ])
    )

    if exclude_excluded:
        query = query.filter(~models.Invoice.exclude_from_ar_aging)

    invoices = query.all()

    client_data = {}
    for inv in invoices:
        days_overdue = (as_of - inv.due_date).days
        client_name = inv.client.display_name

        if client_name not in client_data:
            client_data[client_name] = {
                'current': 0,
                '1_30': 0,
                '31_60': 0,
                '61_90': 0,
                'over_90': 0,
            }

        balance = float(inv.balance_due)

        if days_overdue <= 0:
            client_data[client_name]['current'] += balance
        elif days_overdue <= 30:
            client_data[client_name]['1_30'] += balance
        elif days_overdue <= 60:
            client_data[client_name]['31_60'] += balance
        elif days_overdue <= 90:
            client_data[client_name]['61_90'] += balance
        else:
            client_data[client_name]['over_90'] += balance

    # Add credits from applied credit memos
    applied_credits = db.query(models.CreditMemo).filter(
        models.CreditMemo.status == models.CreditMemoStatus.applied
    ).all()

    for cm in applied_credits:
        client_name = cm.client.display_name
        if client_name not in client_data:
            client_data[client_name] = {
                'current': 0,
                '1_30': 0,
                '31_60': 0,
                '61_90': 0,
                'over_90': 0,
            }
        # Show credits as negative in over_90 bucket
        client_data[client_name]['over_90'] -= float(cm.total)

    db.close()
    return client_data

def compare_ar_aging(qbo_csv_path):
    """Compare QBO and app AR aging data, show discrepancies."""

    print("=" * 100)
    print("AR AGING DISCREPANCY REPORT")
    print("=" * 100)

    qbo_data = parse_qbo_csv(qbo_csv_path)
    app_data = get_app_ar_aging()

    all_clients = set(qbo_data.keys()) | set(app_data.keys())

    discrepancies = []

    print("\nCOMPARISON BY CLIENT:")
    print("-" * 100)

    for client in sorted(all_clients, key=str.lower):
        qbo = qbo_data.get(client, {'current': 0, '1_30': 0, '31_60': 0, '61_90': 0, 'over_90': 0, 'total': 0})
        app = app_data.get(client, {'current': 0, '1_30': 0, '31_60': 0, '61_90': 0, 'over_90': 0})

        qbo_total = qbo.get('total', sum([qbo.get(k, 0) for k in ['current', '1_30', '31_60', '61_90', 'over_90']]))
        app_total = sum([app.get(k, 0) for k in ['current', '1_30', '31_60', '61_90', 'over_90']])

        # Check if there's a discrepancy
        is_different = False
        for key in ['current', '1_30', '31_60', '61_90', 'over_90']:
            if abs(qbo.get(key, 0) - app.get(key, 0)) > 0.01:
                is_different = True
                break

        if is_different or abs(qbo_total - app_total) > 0.01:
            discrepancies.append(client)
            print(f"\n❌ {client}")
            print(f"   {'Aging Bucket':<15} {'QBO':<15} {'App':<15} {'Difference':<15}")
            print(f"   {'-'*60}")

            for bucket in ['current', '1_30', '31_60', '61_90', 'over_90']:
                qbo_val = qbo.get(bucket, 0)
                app_val = app.get(bucket, 0)
                diff = qbo_val - app_val

                status = "✓" if abs(diff) < 0.01 else "✗"
                print(f"   {bucket:<15} ${qbo_val:>13.2f} ${app_val:>13.2f} ${diff:>13.2f} {status}")

            print(f"   {'TOTAL':<15} ${qbo_total:>13.2f} ${app_total:>13.2f} ${qbo_total - app_total:>13.2f}")
        else:
            print(f"✓ {client:<30} QBO: ${qbo_total:>10.2f}  App: ${app_total:>10.2f}")

    print("\n" + "=" * 100)
    print(f"SUMMARY: Found {len(discrepancies)} client(s) with discrepancies")
    print("=" * 100)

    if discrepancies:
        print("\nClients with discrepancies:")
        for client in sorted(discrepancies, key=str.lower):
            print(f"  - {client}")

if __name__ == '__main__':
    csv_path = '/Users/marksharkey/Downloads/PrecisionPros Network_A_R Aging Summary Report (1).csv'
    compare_ar_aging(csv_path)
