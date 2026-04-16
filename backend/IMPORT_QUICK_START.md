# PrecisionPros Data Import Quick Start

**Goal:** Create a repeatable procedure for clearing and re-importing QBO data.

**Status:** Complete — ready for use

**Time Required:** 20 minutes (15 min export + 5 min import)

---

## The Process at a Glance

```
1. Export 5 CSV files from QBO (15 min) ← See QBO_EXPORT_GUIDE.md
   ↓
2. Place CSV files in ~/accounting/backend/
   ↓
3. Run the master import script (5-10 min) ← See below
   ↓
4. Validate results and review report
   ↓
5. Fix any issues identified in validation report
```

---

## Quick Start: Running the Import

### Prerequisites
- All 5 CSV files in `~/accounting/backend/` (see QBO_EXPORT_GUIDE.md)
- MySQL access (`mysql -u ppros -p` should work)
- Python 3 with dependencies installed

### Step 1: Preview (no changes)
```bash
cd ~/accounting/backend
python3 run_full_import.py --dry-run
```

This shows what will happen without making any database changes.

### Step 2: Execute (commits changes)
```bash
python3 run_full_import.py --commit
```

This will:
- Reset database (truncate all data tables)
- Import services, customers, invoices, expenses, billing schedules
- Run cleanup and manual fixes
- Validate results
- Generate a log file

### Step 3: Review Results
The script generates a log file with detailed output. Check:
- Number of records imported
- Any errors or warnings
- Post-import validation report

---

## What Gets Imported

| Category | Count | Source |
|----------|-------|--------|
| Services | ~40 | ProductServiceList CSV |
| Customers | ~200 | Customers CSV |
| Invoices | ~4,000 | Journal + A/R Aging CSVs |
| Line Items | ~10,500 | Journal CSV |
| Expenses | ~880 | Transaction Detail CSV |
| Billing Schedules | ~90 | Manually maintained in PrecisionPros |

---

## What Does NOT Get Imported

- Payment history (all invoices marked paid/open based on AR Aging)
- Credit memos (created manually as needed)
- Estimates (created manually as needed)
- Deleted customers' invoices (skipped automatically)
- Pre-2023 invoices (scope decision)
- AutoCC customer IDs (populate manually)

---

## Key Files

### Master Import Script
- **`run_full_import.py`** — Orchestrates the entire import procedure
  - Validates CSV files exist
  - Runs database reset
  - Executes all import scripts in sequence
  - Calls validation script
  - Generates comprehensive log

### Validation Script
- **`validate_import.py`** — Compares QBO source data to database
  - Reports missing invoices
  - Identifies date mismatches
  - Checks line item integrity
  - Validates subtotals
  - Generates repair recommendations

### Documentation
- **`QBO_EXPORT_GUIDE.md`** — Step-by-step export instructions
- **`IMPORT_PROCEDURES.md`** — Complete reference (from IMPORT_PROCEDURES.md)
- **`IMPORT_QUICK_START.md`** — This file

### Individual Import Scripts (called by master runner)
- `import_services.py` — Services
- `import_customers.py` — Customers
- `import_invoices_full.py` — Invoices + line items
- `import_expenses.py` — Expenses
- `import_billing_schedules_full.py` — Billing schedules
- `cleanup_data.py` — Fix unit prices and subtotals

---

## Troubleshooting

### Missing Invoices in Validation Report

Check the validation output for which invoices are missing. Common reasons:

1. **Deleted customers** — QBO exports invoices but imports skip them if customer doesn't exist
   - Solution: Add missing customers to `Customers.csv` export

2. **Date filtering** — Only 2023+ invoices are imported
   - Solution: Pre-2023 invoices are intentionally excluded

3. **CSV parsing issue** — Invoice # not recognized
   - Solution: Check that `import_invoices_full.py` is parsing the format correctly

### Wrong Invoice Dates

Check `validate_import.py` output for date mismatches. The import script uses:
- Invoice date from Sales Detail CSV
- Due date from A/R Aging CSV (or created_date + 12 days if not in AR Aging)

**Fix:** If dates are consistently wrong:
1. Review the import logic in `import_invoices_full.py`
2. Check QBO export format
3. Update parsing logic and re-run

### Line Item Amount Mismatches

The cleanup script fixes these automatically. If issues remain after cleanup:

```bash
python3 cleanup_data.py --commit
```

Then check the output for any unfixable issues (e.g., invoice #48958 manual fix).

### Database Errors

If the import fails with MySQL errors:

1. Check MySQL is running: `mysql -u ppros -p -e "SELECT 1;"`
2. Verify password is correct
3. Check that `precisionpros` database exists
4. Review error message in log file

---

## Validation Checklist

After importing, verify:

- [ ] Invoice count matches (within ~5%)
- [ ] No "Missing invoices" in validation report
- [ ] Line item count reasonable (typically 2-3 per invoice)
- [ ] No date mismatches, or mismatches are explainable
- [ ] Customer count matches
- [ ] Expense count reasonable
- [ ] Billing schedule imports correctly
- [ ] No duplicate records (import is idempotent for customers/services)

---

## Known Issues & Workarounds

### Invoice #48958
- QBO exported $1.00 instead of $25.00 for a line item
- **Fix applied automatically** by `run_full_import.py`
- Check: `SELECT * FROM invoices WHERE invoice_number = '48958';`

### 8 Customers Missing Email
- These customers import but have blank emails
- **Manually add emails after import:**
  - Dr. Adams
  - Enterprise Communications
  - ERC
  - Frick, Mike
  - mark sharkey
  - Sommer, Eric
  - Svestka, Lura (2 instances)

### 54 QBO Name Mismatches
- QBO invoices use "Name" field; customers exported use "Company name"
- **Already handled** by NAME_MAP in import scripts
- If new customers are added, add them to NAME_MAP in `import_invoices_full.py` and `import_billing_schedules_full.py`

---

## Running the Full Cycle

```bash
# 1. Export from QBO (15 min) — see QBO_EXPORT_GUIDE.md

# 2. Verify files are in place
ls -la ~/accounting/backend/*.csv

# 3. Preview import (no changes)
cd ~/accounting/backend
python3 run_full_import.py --dry-run

# 4. Execute import (commits changes)
python3 run_full_import.py --commit

# 5. Review validation report in the output

# 6. Fix any issues identified
# (Typically: add missing emails, check date mismatches)

# Done! Database is reset and fresh QBO data is imported.
```

---

## When to Use This Procedure

✅ **Use full re-import when:**
- Fixing data quality issues across many records
- Testing new import logic
- Creating a clean database state
- Quarterly backups/refresh
- Before major refactoring

❌ **Do NOT use full re-import when:**
- Adding a single customer or invoice (do it manually)
- Updating open balances (run incremental SQL update instead)
- Making small corrections (fix directly in database)

---

## Post-Import: Next Steps

After a successful import:

1. **Verify in UI** — Check that invoices, customers, expenses appear correctly
2. **Check billing schedules** — Review that recurring billing is set up
3. **Add AutoCC IDs** — Populate `autocc_customer_id` for collections
4. **Add missing emails** — 8 customers need manual email entry
5. **Test collections workflow** — Create a test invoice and verify automation

---

## Support & Issues

### File a bug or suggest improvement
If you find issues with the import procedure:
1. Note the exact problem (missing invoice, wrong date, etc.)
2. Note which step failed
3. Check validation report for details
4. Update the relevant import script

### Common References
- **IMPORT_PROCEDURES.md** — Complete reference with all decisions and mappings
- **QBO_EXPORT_GUIDE.md** — Detailed export instructions
- **validate_import.py** — Comparison tool and diagnostics

---

*Master import runner created: April 14, 2026*  
*For detailed reference, see IMPORT_PROCEDURES.md*
