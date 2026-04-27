#!/usr/bin/env python3
"""
Generate curl commands to exclude discrepant invoices from AR aging.
Based on the comparison report, this helps you identify which invoices to exclude.
"""

import sys
sys.path.insert(0, '/Users/marksharkey/accounting/backend')

from database import SessionLocal
import models

# Clients with discrepancies that likely need exclusion
DISCREPANT_CLIENTS = [
    "Alan Hoffberg",
    "Atlantis Travel Agency",
    "Atlantis Travel Agency, Athens",
    "BJSA",
    "cyberabbi.com",
    "Digital Essentials (deleted)",
    "Don Adair",
    "echost.com",
    "edgepowersolutions.net",
    "ehappyhour.com, Inc.",
    "Enterprise Communications",
    "ERC",
    "erc programming",
    "Fish and Game",
    "Florida Corporate Training",
    "Frick, Mike",
    "Get Green Earth(2)",
    "Hawaii Health Guide",
    "hawthornepp",
    "icapture.com",
    "KATZ",
    "KAYA",
    "L F Rothchild",
    "Lombardcompany.com",
    "M&R & Sons",
    "Mahon Ranch",
    "Meryl Deutsch & Associates",
    "Net-Flow Corporation-",
    "Olivado USA",
    "onlearn",
    "Platinum Television Group",
    "Private Jet Trading",
    "Rescate de San Carlos A.C.",
    "Rus Berrett",
    "sancarlosproperty",
    "sancarlosproperty.com",
    "Singing Voice Lessons",
    "Sommer, Eric",
    "Spaeder",
    "SteamworksAZ",
    "Terriann Muller",
    "Whiteent",
    "zhost",
]

db = SessionLocal()

invoices_by_client = {}
for client_name in DISCREPANT_CLIENTS:
    client = db.query(models.Client).filter_by(display_name=client_name).first()
    if client:
        invs = db.query(models.Invoice).filter_by(client_id=client.id).all()
        if invs:
            invoices_by_client[client_name] = invs

print("=" * 100)
print("INVOICES TO EXCLUDE FROM AR AGING REPORT")
print("=" * 100)

total_invoices = 0
for client_name in sorted(invoices_by_client.keys(), key=str.lower):
    invs = invoices_by_client[client_name]
    print(f"\n{client_name} ({len(invs)} invoices):")
    for inv in invs:
        if inv.status in [models.InvoiceStatus.sent, models.InvoiceStatus.partially_paid]:
            print(f"  Invoice #{inv.invoice_number} (ID: {inv.id}): ${inv.balance_due:.2f} balance, Status: {inv.status.value}")
            total_invoices += 1

print(f"\n{'=' * 100}")
print(f"Total invoices from discrepant clients (with balance): {total_invoices}")
print(f"{'=' * 100}")

print("\nTo exclude these invoices from the AR Aging report, run:")
print("(Replace TOKEN with your actual auth token)")
print()

for client_name in sorted(invoices_by_client.keys(), key=str.lower):
    invs = invoices_by_client[client_name]
    for inv in invs:
        if inv.status in [models.InvoiceStatus.sent, models.InvoiceStatus.partially_paid]:
            print(f"curl -X POST -H \"Authorization: Bearer TOKEN\" \\")
            print(f"  http://localhost:8010/api/invoices/{inv.id}/exclude-from-ar-aging")

db.close()
