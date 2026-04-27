#!/usr/bin/env python3
"""Show P&L category discrepancies in detail."""

import csv
from decimal import Decimal
from collections import defaultdict
from database import SessionLocal
import models

def clean_money(val):
    if not val or val.strip() == "":
        return Decimal("0.00")
    cleaned = val.strip().replace("$", "").replace(",", "").replace('"', '')
    try:
        return Decimal(cleaned)
    except:
        return Decimal("0.00")

# Parse QBO Journal
qbo_cats = defaultdict(lambda: {"debit": Decimal("0"), "credit": Decimal("0")})
with open('PrecisionPros_Network_Journal.csv', newline="", encoding="utf-8") as f:
    reader = csv.reader(f)
    for _ in range(4):
        next(reader, None)
    for raw_row in reader:
        if not raw_row or not any(raw_row) or (raw_row[0] and not raw_row[1]):
            continue
        if len(raw_row) < 9:
            continue
        gl_account = raw_row[6].strip() if len(raw_row) > 6 else ""
        debit_str = raw_row[7].strip() if len(raw_row) > 7 else ""
        credit_str = raw_row[8].strip() if len(raw_row) > 8 else ""
        if not gl_account or (not debit_str and not credit_str):
            continue
        qbo_cats[gl_account]["debit"] += clean_money(debit_str)
        qbo_cats[gl_account]["credit"] += clean_money(credit_str)

# Get DB categories
db = SessionLocal()
db_cats = defaultdict(lambda: {"debit": Decimal("0"), "credit": Decimal("0")})
for entry in db.query(models.JournalEntry).all():
    db_cats[entry.gl_account_name]["debit"] += entry.debit
    db_cats[entry.gl_account_name]["credit"] += entry.credit
db.close()

# Compare
print("\n" + "="*110)
print("P&L CATEGORY COMPARISON: QBO vs Database")
print("="*110 + "\n")

# Categories to compare
target_cats = []
for cat in sorted(qbo_cats.keys()):
    if any(kw.lower() in cat.lower() for kw in ["email", "cc fee", "dues", "marketing", "meals", "server", "tax"]):
        target_cats.append(cat)

for cat in target_cats:
    qbo_net = qbo_cats[cat]["credit"] - qbo_cats[cat]["debit"]
    db_net = db_cats[cat]["credit"] - db_cats[cat]["debit"] if cat in db_cats else Decimal("0")
    diff = db_net - qbo_net

    print(f"{cat}")
    print(f"  QBO:      ${qbo_net:>12,.2f}")
    print(f"  Database: ${db_net:>12,.2f}")
    print(f"  Diff:     ${diff:>12,.2f}  {'⚠️  SHORT' if diff > 0.01 else ('✓ OK' if abs(diff) < 0.01 else '⚠️  OVER')}")
    print()
