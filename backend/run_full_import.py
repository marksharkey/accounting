#!/usr/bin/env python3
"""
PrecisionPros Master Import Runner
Automates the complete re-import procedure: database reset, all import scripts, cleanup, and validation.

Usage:
    python3 run_full_import.py --dry-run        # Preview all steps, no database changes
    python3 run_full_import.py --commit         # Execute full re-import
    python3 run_full_import.py --commit --skip-validation  # Skip post-import validation

Prerequisites:
    - All required QBO CSV files in ~/accounting/backend/:
      * Customers.csv
      * ProductServiceList__*.csv
      * PrecisionPros_Network_Journal.csv (invoices + line items)
      * PrecisionPros_Network_A_R_Aging_Detail_Report.csv
      * PrecisionPros_Network_Transaction_Detail_by_Account.csv
    - .env file with DB credentials (copy .env.example and update)
      Required vars: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
    - MySQL access (mysql CLI tool installed)

This script ensures a repeatable, safe import process with comprehensive logging and error handling.
"""

import sys
import os
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

# ── Load .env credentials ──────────────────────────────────────────────────────
def load_env(backend_dir):
    """Read DB credentials from .env file."""
    env = {}
    env_path = Path(backend_dir) / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    env[key.strip()] = val.strip()
    return env

# ── Configuration ──────────────────────────────────────────────────────────────

REQUIRED_CSV_FILES = {
    "Customers.csv": "Customer list export from QBO",
    "ProductServiceList__*.csv": "Product & Service list (filename has timestamp)",
    "PrecisionPros_Network_Journal.csv": "Journal report (2023+)",
    "PrecisionPros_Network_A_R_Aging_Detail_Report.csv": "A/R Aging detail report",
    "PrecisionPros_Network_Transaction_Detail_by_Account.csv": "Transaction detail report",
    "PrecisionPros_Network_Invoices_and_Received_Payments.csv": "Invoices and Received Payments report (for payment import)",
}

IMPORT_STEPS = [
    {
        "name": "Database Reset",
        "type": "sql",
        "required": True,
        "description": "Truncate all data tables (preserves users, COA, company_info)",
    },
    {
        "name": "Service Catalog Import",
        "type": "script",
        "script": "import_services.py",
        "required": True,
        "description": "Import 40 services from ProductServiceList CSV",
    },
    {
        "name": "Customer/Client Import",
        "type": "script",
        "script": "import_customers.py",
        "args": "--csv Customers.csv",
        "required": True,
        "description": "Import 202 clients",
    },
    {
        "name": "Invoice + Line Items Import",
        "type": "script",
        "script": "import_invoices_from_journal.py",
        "required": True,
        "description": "Import 4,260+ invoices from Journal CSV",
    },
    {
        "name": "Expense Import",
        "type": "script",
        "script": "import_expenses.py",
        "required": True,
        "description": "Import 879 expense transactions",
    },
    {
        "name": "Billing Schedules Import",
        "type": "script",
        "script": "import_billing_schedules_full.py",
        "required": True,
        "description": "Import 92 billing schedules from invoice history",
    },
    {
        "name": "Journal Entries Import",
        "type": "script",
        "script": "import_qbo_journal_to_db.py",
        "args": "PrecisionPros_Network_Journal.csv",
        "required": False,
        "description": "Import GL journal entries for accrual-basis P&L reporting",
    },
    {
        "name": "Payment Import",
        "type": "script",
        "script": "import_payments_from_report.py",
        "args": "PrecisionPros_Network_Invoices_and_Received_Payments.csv",
        "required": False,
        "description": "Import payment records from Invoices and Received Payments report",
    },
    {
        "name": "Payment Reconciliation",
        "type": "script",
        "script": "reconcile_invoices_with_payments.py",
        "required": False,
        "description": "Reconcile invoice amounts and status based on payments",
    },
    {
        "name": "Data Cleanup",
        "type": "script",
        "script": "cleanup_data.py",
        "required": True,
        "description": "Fix unit prices, subtotals, and balance issues",
    },
    {
        "name": "Manual Fixes",
        "type": "sql",
        "required": True,
        "description": "Apply known fixes (e.g., invoice #48958)",
    },
    {
        "name": "Create Overpayment Credits",
        "type": "script",
        "script": "create_overpayment_credits.py",
        "required": False,
        "description": "Create credit memos for client overpayments from QB migration (zhost, Whiteent, L F Rothchild, SteamworksAZ)",
    },
    {
        "name": "Exclude Discrepant Invoices",
        "type": "script",
        "script": "exclude_specific_invoices.py",
        "required": False,
        "description": "Mark specific invoices as excluded from AR aging (data quality fixes)",
    },
]

# ── Database reset SQL ─────────────────────────────────────────────────────────
DB_RESET_SQL = """
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE activity_log;
TRUNCATE TABLE collections_events;
TRUNCATE TABLE bank_transactions;
TRUNCATE TABLE credit_line_items;
TRUNCATE TABLE credit_memos;
TRUNCATE TABLE estimate_line_items;
TRUNCATE TABLE estimates;
TRUNCATE TABLE invoice_line_items;
TRUNCATE TABLE payments;
TRUNCATE TABLE invoices;
TRUNCATE TABLE billing_schedule_line_items;
TRUNCATE TABLE billing_schedules;
TRUNCATE TABLE clients;
TRUNCATE TABLE expenses;
TRUNCATE TABLE service_catalog;
TRUNCATE TABLE journal_entries;
SET FOREIGN_KEY_CHECKS = 1;
"""

# ── Manual fixes SQL ───────────────────────────────────────────────────────────
MANUAL_FIXES_SQL = """
UPDATE invoice_line_items li
JOIN invoices i ON i.id = li.invoice_id
SET li.unit_amount = 25.00, li.amount = 25.00
WHERE i.invoice_number = '48958';

UPDATE invoices
SET subtotal = 25.00, total = 25.00, amount_paid = 1.00, balance_due = 24.00
WHERE invoice_number = '48958';
"""

# ── Import runner ──────────────────────────────────────────────────────────────

class ImportRunner:
    def __init__(self, dry_run=False, skip_validation=False, backend_dir="."):
        self.dry_run = dry_run
        self.skip_validation = skip_validation
        self.backend_dir = Path(backend_dir)
        self.log_file = self.backend_dir / f"import_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": dry_run,
            "steps": [],
            "passed": 0,
            "failed": 0,
            "errors": [],
        }

        # Load DB credentials from .env
        env = load_env(backend_dir)
        self.db_host     = env.get("DB_HOST", "localhost")
        self.db_port     = env.get("DB_PORT", "3306")
        self.db_name     = env.get("DB_NAME", "precisionpros")
        self.db_user     = env.get("DB_USER", "ppros")
        self.db_password = env.get("DB_PASSWORD", "")

        self._log_header()

    def _log_header(self):
        header = f"""
{'='*70}
  PrecisionPros Master Import Runner
{'='*70}
  Start Time:  {datetime.now().isoformat()}
  Mode:        {'DRY RUN (no changes)' if self.dry_run else '*** LIVE COMMIT ***'}
  Backend Dir: {self.backend_dir}
  DB:          {self.db_user}@{self.db_host}:{self.db_port}/{self.db_name}
  Log File:    {self.log_file}
{'='*70}
"""
        print(header)
        with open(self.log_file, "w") as f:
            f.write(header)

    def log(self, msg):
        print(msg)
        with open(self.log_file, "a") as f:
            f.write(msg + "\n")

    def check_csv_files(self):
        """Verify all required CSV files exist."""
        self.log("\n[STEP 0] Checking for required CSV files...")
        missing = []
        for pattern, description in REQUIRED_CSV_FILES.items():
            if "*" in pattern:
                files = list(self.backend_dir.glob(pattern))
                if not files:
                    missing.append(f"{pattern} — {description}")
            else:
                if not (self.backend_dir / pattern).exists():
                    missing.append(f"{pattern} — {description}")

        if missing:
            self.log("\n❌ MISSING CSV FILES:")
            for m in missing:
                self.log(f"   • {m}")
            self.log("\nPlease export these files from QBO before running import.")
            self.log("See QBO_EXPORT_GUIDE.md for instructions.")
            return False

        self.log("✓ All required CSV files found")
        return True

    def find_product_service_csv(self):
        """Find the ProductServiceList CSV (has timestamp in filename)."""
        files = list(self.backend_dir.glob("ProductServiceList__*"))
        return files[0].name if files else None

    def run_sql(self, sql, description):
        """Execute SQL non-interactively using credentials from .env."""
        if self.dry_run:
            self.log(f"\n[DRY RUN] Would execute SQL: {description}")
            return True

        try:
            cmd = [
                "mysql",
                f"-u{self.db_user}",
                f"-h{self.db_host}",
                f"-P{self.db_port}",
                self.db_name,
            ]
            # Only add password if provided (avoid "-p" alone which prompts)
            if self.db_password:
                cmd.insert(2, f"-p{self.db_password}")
            result = subprocess.run(
                cmd,
                input=sql,
                text=True,
                capture_output=True,
                timeout=60,
            )
            if result.returncode != 0:
                self.log(f"❌ SQL Error: {result.stderr}")
                return False
            self.log(f"✓ {description}")
            return True
        except Exception as e:
            self.log(f"❌ Error executing SQL: {e}")
            return False

    def run_script(self, script_name, args=""):
        """Run one import script with --dry-run or --commit."""
        mode_arg = "--dry-run" if self.dry_run else "--commit"
        cmd = ["python3", str(self.backend_dir / script_name), mode_arg]
        if args:
            cmd.extend(args.split())

        try:
            result = subprocess.run(
                cmd,
                cwd=self.backend_dir,
                capture_output=True,
                text=True,
                timeout=300,
            )
            output = result.stdout + result.stderr
            self.log(output)

            if result.returncode != 0:
                self.log(f"❌ Script failed with return code {result.returncode}")
                return False
            return True

        except subprocess.TimeoutExpired:
            self.log("❌ Script timed out after 5 minutes")
            return False
        except Exception as e:
            self.log(f"❌ Error running script: {e}")
            return False

    def run_imports(self):
        """Execute all import steps in order."""
        self.log("\n" + "="*70)
        self.log("IMPORT PROCEDURE")
        self.log("="*70)

        for i, step in enumerate(IMPORT_STEPS, 1):
            self.log(f"\n[STEP {i}] {step['name']}")
            self.log(f"  {step['description']}")

            step_type = step.get("type", "script")
            success = False

            if step_type == "sql" and step["name"] == "Database Reset":
                success = self.run_sql(DB_RESET_SQL, "Database reset")
            elif step_type == "sql" and step["name"] == "Manual Fixes":
                success = self.run_sql(MANUAL_FIXES_SQL, "Manual fixes (invoice #48958)")
            elif step_type == "script":
                script = step.get("script")
                args = step.get("args", "")

                # ProductServiceList has a timestamp in the filename — find it dynamically
                if script == "import_services.py":
                    csv_file = self.find_product_service_csv()
                    if csv_file:
                        args = f"--csv {csv_file}"
                    else:
                        self.log("❌ ProductServiceList CSV not found")
                        success = False

                if script:
                    success = self.run_script(script, args)
            else:
                self.log(f"  ⚠ Unknown step type: {step_type}")
                success = False

            self.results["steps"].append({
                "name": step["name"],
                "success": success,
                "required": step["required"],
            })

            if success:
                self.results["passed"] += 1
            else:
                self.results["failed"] += 1
                if step["required"]:
                    self.results["errors"].append(
                        f"Required step '{step['name']}' failed — stopping import"
                    )
                    self.log("\n❌ IMPORT STOPPED: Required step failed")
                    return False

        return True

    def run_validation(self):
        """Run post-import validation."""
        if self.skip_validation or self.dry_run:
            self.log("\n(Validation skipped)")
            return True

        self.log("\n" + "="*70)
        self.log("POST-IMPORT VALIDATION")
        self.log("="*70)

        try:
            result = subprocess.run(
                ["python3", str(self.backend_dir / "validate_import.py")],
                cwd=self.backend_dir,
                capture_output=True,
                text=True,
                timeout=120,
            )
            self.log(result.stdout)
            if result.stderr:
                self.log(result.stderr)
            return result.returncode == 0
        except Exception as e:
            self.log(f"⚠ Validation script error: {e}")
            return False

    def print_summary(self):
        summary = f"""
{'='*70}
IMPORT SUMMARY
{'='*70}
Timestamp: {self.results['timestamp']}
Mode:      {'DRY RUN' if self.dry_run else 'LIVE COMMIT'}
Passed:    {self.results['passed']} / {len(IMPORT_STEPS)}
Failed:    {self.results['failed']} / {len(IMPORT_STEPS)}

Steps:
"""
        for step in self.results["steps"]:
            status   = "✓" if step["success"] else "❌"
            required = " [REQUIRED]" if step["required"] else ""
            summary += f"  {status} {step['name']}{required}\n"

        if self.results["errors"]:
            summary += "\nErrors:\n"
            for err in self.results["errors"]:
                summary += f"  • {err}\n"

        summary += f"\nLog file: {self.log_file}\n"
        summary += "="*70 + "\n"
        self.log(summary)

    def run(self):
        try:
            if not self.check_csv_files():
                self.results["failed"] = 1
                self.results["errors"].append("Missing CSV files")
                self.print_summary()
                return False

            if not self.run_imports():
                self.print_summary()
                return False

            if not self.run_validation():
                self.log("\n⚠ Validation found issues — see report above")

            self.print_summary()
            return self.results["failed"] == 0

        except KeyboardInterrupt:
            self.log("\n\n❌ Import interrupted by user")
            self.print_summary()
            return False
        except Exception as e:
            self.log(f"\n\n❌ Unexpected error: {e}")
            import traceback
            self.log(traceback.format_exc())
            self.print_summary()
            return False


def main():
    parser = argparse.ArgumentParser(description="PrecisionPros Master Import Runner")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true",
                       help="Preview all steps without making changes")
    group.add_argument("--commit", action="store_true",
                       help="Execute the full import (changes database)")
    parser.add_argument("--skip-validation", action="store_true",
                        help="Skip post-import validation")

    args = parser.parse_args()

    runner = ImportRunner(
        dry_run=args.dry_run,
        skip_validation=args.skip_validation,
        backend_dir=os.path.dirname(os.path.abspath(__file__)),
    )

    success = runner.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
