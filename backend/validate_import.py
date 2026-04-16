#!/usr/bin/env python3
"""
PrecisionPros Import Validation Script
Compares QBO source CSV files against the imported database to identify discrepancies.

Usage:
    python3 validate_import.py

Reports on:
- Customer count vs QBO export
- Invoice count vs QBO Sales Detail
- Line item integrity (unit_amount * qty = amount)
- Invoice subtotal integrity (subtotal = sum of line items)
- Open balance coverage (AR Aging invoices imported correctly)
"""

import sys
import os
import csv
from decimal import Decimal
from datetime import datetime
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
from models import Invoice, InvoiceLineItem, Client, ServiceCatalog, Expense, BillingSchedule

NAME_MAP = {
    "Sommer, Eric":                  "Arkadia Konsulting",
    "autobenefit":                   "Concierge Coaches",
    "sancarlosproperty":             "sancarlosproperty.com",
    "ehappyhour.com, Inc.":          "Timus, Inc.",
    "Atlantis Travel Agency":        "Atlantis Travel Agency, Athens",
    "Contractors Parts and Supply":  "Contractors Crance Co. Inc.",
    "ImageTag, Inc.":                "Paymerang, LLC",
    "Net-Flow Corporation-":         "Net-Flow Corporation",
    "Lombardcompany.com":            "Lombard Architectural Precast Products",
    "Actuarial Work Products, Inc.": "Castevens Technologies LLC",
    "Architectural Visual Inc.":     "Architectural Visual, Inc.",
    "B Factor Group":                "1SEO Digital Agency",
    "CVISION Technologies":          "Foxit Software",
    "CYoungConsulting.com":          "C Young Consulting LLC",
    "ChristopherAugustine.com":      "Christopher Augustine, LTD",
    "DesignGate Pte. Ltd.":          "DesignGate pte Ltd.",
    "Dr. Adams":                     "Dr. D.B. Adams",
    "Eternallygreen.com":            "Integrity Landscaping",
    "Fine Design Interiors":         "Fine Design Interiors, Inc.",
    "Hearnelake":                    "Hearne Lake Operations Ltd",
    "International Fishing Devices": "International Fishing Devices, Inc.",
    "L F Rothchild":                 "Shearson Financial",
    "Lambert, Bernadette":           "Bernadette/eyre",
    "MEDAxiom, LLC":                 "MEDAxiom, LLC.",
    "Ned Freeman":                   "calpreps.com",
    "Newmedia":                      "New Media Sales & Management Co. Ltd.",
    "Pacific Holidays, Inc.":        "JC Pacific Trading Co.",
    "Paul Brahaney":                 "Jog A Dog",
    "Peterson-mfg.com":              "Peterson Manufacturing Co.",
    "Preserve  Resort HOA?":         "Preserve Resort HOA?",
    "Rick Long":                     "Rick Long - RFS Corporation",
    "Robyn":                         "Robyn Glazner",
    "Sanson Financial Solutions, LLC": "Sanson Insurance & Financial Services, LL",
    "Serenity Canine Retreat":       "Serentiy Canine Retreat",
    "Sharkey, Keith":                "Key Real Estate Investments, LLC",
    "Sparle 'n Dazzle":              "Sparkle n Dazzle",
    "SteelRep":                      "Sun Belt Steel & Aluminum, Inc",
    "Svestka, Lura":                 "JTA, Inc.",
    "The Pension Studio":            "Darbster Foundation",
    "Tires to Go":                   "Tires2go Inc.",
    "Whatwatt.com/service lamp":     "Whatwatt LLC",
    "Whiteent":                      "White Enterprises",
    "Worldfamouscomics.com":         "WF Comics",
    "X-Tel Communications":          "James Rahfaldt",
    "Zhongwen":                      "Zhongwen.com",
    "aeroware":                      "Aero Wear",
    "agroresources.com":             "Agro Resources",
    "bingobuddies":                  "Soleau software",
    "druckers.com":                  "Druckers",
    "kimm.org":                      "David Kimm Fesler LTD",
    "peoplesourceonline":            "Peoplesource LLC",
    "platypuscreative":              "Platypus Creative",
    "psgraphics":                    "PS Graphics, Inc.",
    "zhost":                         "Ponder and Assoc",
}

def resolve_name(name):
    name = name.replace("(deleted)", "").strip().rstrip(",").strip()
    return NAME_MAP.get(name, name)

def clean_decimal(val):
    if not val:
        return Decimal("0.00")
    try:
        return Decimal(str(val).replace(",", "").replace('"', "").strip() or "0")
    except:
        return Decimal("0.00")

def parse_date(val):
    if not val or not val.strip():
        return None
    try:
        return datetime.strptime(val.strip(), "%m/%d/%Y").date()
    except:
        return None

def parse_sales_detail_csv(csv_path):
    """
    Parse the Sales by Product/Service Detail CSV.
    This file is NOT a standard CSV — it's organized by product section.
    Format: blank first col = data row; non-blank first col = section header.
    Columns: _, date, txn_type, inv_num, customer, memo, qty, price, amount, balance
    """
    invoices = defaultdict(lambda: {"customer": "", "date": None, "line_count": 0, "total": Decimal("0")})
    current_product = None

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if not row:
                continue
            first = row[0].strip()

            # Section header rows (non-blank first col, not a total/meta row)
            if first and not any(first.startswith(x) for x in
                    ["Sales", "PrecisionPros", "January", "February", "March",
                     "April", "May", "June", "July", "August", "September",
                     "October", "November", "December", "Total", "Cash Basis", "TOTAL"]):
                current_product = first
                continue

            # Data rows have blank first column
            if first != "":
                continue
            if len(row) < 9:
                continue

            _, date_val, txn_type, inv_num, customer, memo, qty, price, amount, *_ = (row + [""] * 5)[:10]

            if txn_type.strip() != "Invoice":
                continue

            inv_num = inv_num.strip()
            if not inv_num:
                continue

            inv_date = parse_date(date_val)
            if invoices[inv_num]["date"] is None:
                invoices[inv_num]["customer"] = customer.strip()
                invoices[inv_num]["date"]     = inv_date

            invoices[inv_num]["line_count"] += 1
            invoices[inv_num]["total"] += clean_decimal(amount)

    return dict(invoices)

def parse_ar_aging_csv(csv_path):
    """
    Parse the A/R Aging Detail CSV to get open invoices.
    Returns dict of invoice_number -> open_balance for Invoice rows only.
    """
    open_invoices = {}
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if not row or len(row) < 8:
                continue
            blank, date_val, txn_type, num, customer, due_date, amount, open_bal = row[:8]
            if blank.strip() != "" or txn_type.strip() != "Invoice":
                continue
            num = num.strip()
            bal = clean_decimal(open_bal)
            if num and bal > 0:
                open_invoices[num] = bal
    return open_invoices

def parse_customers_csv(csv_path):
    """Parse Customers.csv — simple DictReader, headers on row 1."""
    customers = {}
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name    = (row.get("Name") or "").strip()
            company = (row.get("Company name") or "").strip()
            key     = company if company and company != name else name
            if key:
                customers[key] = row
    return customers


class ImportValidator:
    def __init__(self):
        self.db     = SessionLocal()
        self.issues = []
        self.stats  = {}

    def log(self, msg):
        print(msg)

    def issue(self, severity, message):
        self.issues.append({"severity": severity, "message": message})
        marker = "❌" if severity == "ERROR" else "⚠"
        self.log(f"  {marker} [{severity}] {message}")

    # ── Validation checks ────────────────────────────────────────────────────

    def validate_customers(self):
        self.log("\n── Customer Validation ──────────────────────────────────")

        csv_path = Path(".") / "Customers.csv"
        if not csv_path.exists():
            self.issue("WARNING", "Customers.csv not found — skipping customer validation")
            return

        qbo = parse_customers_csv(csv_path)
        db  = {c.company_name: c for c in self.db.query(Client).all()}

        self.stats["qbo_customers"] = len(qbo)
        self.stats["db_customers"]  = len(db)
        self.log(f"  QBO: {len(qbo)} customers   DB: {len(db)} clients")

        missing = set(qbo.keys()) - set(db.keys())
        if missing:
            self.issue("ERROR", f"{len(missing)} QBO customers not in DB")
            for name in sorted(missing)[:5]:
                self.log(f"    - {name}")
            if len(missing) > 5:
                self.log(f"    ... and {len(missing) - 5} more")
        else:
            self.log("  ✓ All QBO customers are in the database")

    def validate_invoices(self):
        self.log("\n── Invoice Validation ───────────────────────────────────")

        sales_csv = Path(".") / "PrecisionPros_Network_Sales_by_Product_Service_Detail.csv"
        if not sales_csv.exists():
            self.issue("WARNING", "Sales Detail CSV not found — skipping invoice validation")
            return

        qbo_invoices = parse_sales_detail_csv(sales_csv)
        db_invoices  = {i.invoice_number: i for i in self.db.query(Invoice).all()}

        self.stats["qbo_invoices"] = len(qbo_invoices)
        self.stats["db_invoices"]  = len(db_invoices)
        self.log(f"  QBO: {len(qbo_invoices)} invoices   DB: {len(db_invoices)} invoices")

        # Invoices in QBO not in DB (excluding deleted clients — expected)
        missing = set(qbo_invoices.keys()) - set(db_invoices.keys())
        if missing:
            # Separate deleted-client invoices (expected) from genuine misses
            deleted = [n for n, inv in qbo_invoices.items()
                       if n in missing and "(deleted)" in inv.get("customer", "")]
            genuine_missing = missing - set(deleted)

            if deleted:
                self.log(f"  ✓ {len(deleted)} invoices skipped (deleted clients — expected)")
            if genuine_missing:
                self.issue("ERROR", f"{len(genuine_missing)} non-deleted invoices missing from DB")
                for num in sorted(genuine_missing)[:10]:
                    inv = qbo_invoices[num]
                    self.log(f"    #{num}: {inv['customer']} ({inv['date']})")
                if len(genuine_missing) > 10:
                    self.log(f"    ... and {len(genuine_missing) - 10} more")
            else:
                self.log("  ✓ All non-deleted invoices are in the database")
        else:
            self.log("  ✓ All QBO invoices are in the database")

        # Line item counts
        db_li_count = self.db.query(InvoiceLineItem).count()
        self.stats["db_line_items"] = db_li_count
        self.log(f"  DB line items: {db_li_count:,}")

    def validate_open_balances(self):
        self.log("\n── Open Balance Validation ──────────────────────────────")

        ar_csv = Path(".") / "PrecisionPros_Network_A_R_Aging_Detail_Report.csv"
        if not ar_csv.exists():
            self.issue("WARNING", "AR Aging CSV not found — skipping open balance validation")
            return

        qbo_open = parse_ar_aging_csv(ar_csv)
        db_invoices = {i.invoice_number: i for i in self.db.query(Invoice).all()}

        mismatches = []
        missing_open = []

        for inv_num, qbo_balance in qbo_open.items():
            db_inv = db_invoices.get(inv_num)
            if not db_inv:
                missing_open.append(inv_num)
                continue
            db_balance = Decimal(str(db_inv.balance_due)).quantize(Decimal("0.01"))
            qbo_balance = qbo_balance.quantize(Decimal("0.01"))
            if db_balance != qbo_balance:
                mismatches.append({
                    "invoice": inv_num,
                    "qbo": qbo_balance,
                    "db":  db_balance,
                })

        self.log(f"  QBO open invoices: {len(qbo_open)}   Mismatches: {len(mismatches)}")

        if missing_open:
            self.issue("ERROR", f"{len(missing_open)} open invoices from AR Aging not in DB")
            for num in missing_open[:5]:
                self.log(f"    #{num}")

        if mismatches:
            self.issue("ERROR", f"{len(mismatches)} invoices have wrong balance_due")
            for m in mismatches[:5]:
                self.log(f"    #{m['invoice']}: QBO=${m['qbo']}  DB=${m['db']}")
        else:
            self.log("  ✓ All open balances match QBO")

    def validate_line_item_math(self):
        self.log("\n── Line Item Math Validation ────────────────────────────")

        issues = 0
        examples = []

        for li in self.db.query(InvoiceLineItem).all():
            qty      = Decimal(str(li.quantity))
            unit     = Decimal(str(li.unit_amount))
            amount   = Decimal(str(li.amount)).quantize(Decimal("0.01"))
            expected = (qty * unit).quantize(Decimal("0.01"))
            if expected != amount:
                issues += 1
                if len(examples) < 5:
                    inv = self.db.query(Invoice).filter(Invoice.id == li.invoice_id).first()
                    examples.append(f"    #{inv.invoice_number if inv else '?'}: "
                                    f"{li.description[:35]} — {qty}×${unit}=${expected} (stored ${amount})")

        if issues:
            self.issue("ERROR", f"{issues} line items where qty×unit_price ≠ amount")
            for ex in examples:
                self.log(ex)
            self.log("  → Run: python3 cleanup_data.py --commit")
        else:
            self.log(f"  ✓ All line item amounts are consistent")

    def validate_invoice_subtotals(self):
        self.log("\n── Invoice Subtotal Validation ──────────────────────────")

        issues = 0
        examples = []

        for inv in self.db.query(Invoice).all():
            if not inv.line_items:
                continue
            line_sum = sum(Decimal(str(li.amount)) for li in inv.line_items).quantize(Decimal("0.01"))
            subtotal = Decimal(str(inv.subtotal)).quantize(Decimal("0.01"))
            if line_sum != subtotal:
                issues += 1
                if len(examples) < 5:
                    examples.append(f"    #{inv.invoice_number}: subtotal=${subtotal} line_sum=${line_sum}")

        if issues:
            self.issue("ERROR", f"{issues} invoices where subtotal ≠ sum of line items")
            for ex in examples:
                self.log(ex)
            self.log("  → Run: python3 cleanup_data.py --commit")
        else:
            self.log(f"  ✓ All invoice subtotals are consistent")

    def validate_billing_schedules(self):
        self.log("\n── Billing Schedule Validation ──────────────────────────")

        schedules = self.db.query(BillingSchedule).filter_by(is_active=True).all()
        self.stats["billing_schedules"] = len(schedules)

        no_lines = [s for s in schedules if not s.line_items]
        self.log(f"  Active schedules: {len(schedules)}")

        if no_lines:
            self.issue("WARNING", f"{len(no_lines)} billing schedules have no line items")
            for s in no_lines[:5]:
                client = self.db.query(Client).filter(Client.id == s.client_id).first()
                self.log(f"    {client.company_name if client else s.client_id}")
        else:
            self.log("  ✓ All billing schedules have line items")

    def print_summary(self):
        error_count   = sum(1 for i in self.issues if i["severity"] == "ERROR")
        warning_count = sum(1 for i in self.issues if i["severity"] == "WARNING")

        self.log(f"""
{'='*70}
VALIDATION SUMMARY
{'='*70}
  Customers:         {self.stats.get('qbo_customers','?')} in QBO  →  {self.stats.get('db_customers','?')} in DB
  Invoices:          {self.stats.get('qbo_invoices','?')} in QBO  →  {self.stats.get('db_invoices','?')} in DB
  Line Items:        {self.stats.get('db_line_items','?')} in DB
  Billing Schedules: {self.stats.get('billing_schedules','?')} active

  Errors:   {error_count}
  Warnings: {warning_count}

  {'✅ All checks passed' if error_count == 0 else '❌ Issues found — see above'}
{'='*70}
""")
        return error_count == 0

    def run(self):
        print(f"\n{'='*70}")
        print("  PrecisionPros Import Validator")
        print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}")

        try:
            self.validate_customers()
            self.validate_invoices()
            self.validate_open_balances()
            self.validate_line_item_math()
            self.validate_invoice_subtotals()
            self.validate_billing_schedules()
            success = self.print_summary()
            return 0 if success else 1
        except Exception as e:
            self.log(f"\n❌ Validation error: {e}")
            import traceback
            self.log(traceback.format_exc())
            return 1
        finally:
            self.db.close()


if __name__ == "__main__":
    validator = ImportValidator()
    sys.exit(validator.run())
