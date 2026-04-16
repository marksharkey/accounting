# Import Infrastructure Setup Complete

**Date Created:** April 14, 2026  
**Status:** ✅ Ready to use

---

## What's Been Created

I've built a complete, repeatable import infrastructure for PrecisionPros. You now have:

### 1. **Master Import Runner** (`run_full_import.py`)
A single command orchestrates the entire re-import process end-to-end:

```bash
python3 run_full_import.py --dry-run    # Preview
python3 run_full_import.py --commit     # Execute
```

**What it does:**
- ✓ Validates all required CSV files exist
- ✓ Resets the database (truncates data, preserves schema)
- ✓ Runs all 6 import scripts in sequence (services → customers → invoices → expenses → billing schedules → cleanup)
- ✓ Applies manual fixes (e.g., invoice #48958)
- ✓ Calls validation script to compare QBO source to database
- ✓ Generates comprehensive log file with timestamps
- ✓ Provides clear success/failure reporting

**Key feature:** Error handling stops the process on required step failures so you don't get partial imports.

---

### 2. **Validation Script** (`validate_import.py`)
Automatically compares QBO source data to the imported database:

```bash
python3 validate_import.py
```

**What it checks:**
- Customer counts (QBO vs DB)
- Invoice counts (QBO vs DB) 
- Missing invoices (in QBO but not imported)
- Invoice date mismatches
- Line item integrity (qty × unit_price = amount)
- Invoice subtotals vs sum of line items
- Line item count validation

**Output:** Issues categorized as ERROR or WARNING with actionable recommendations.

---

### 3. **Export Guide** (`QBO_EXPORT_GUIDE.md`)
Complete step-by-step instructions for exporting all data from QBO.

---

### 4. **Quick Start Guide** (`IMPORT_QUICK_START.md`)
Overview of the entire process with:
- Process diagram
- Running the import
- Troubleshooting common issues
- Validation checklist
- Known issues & workarounds

---

## Exact QBO Files Needed for Re-Import

Place these 5 files in `~/accounting/backend/` before running `run_full_import.py`:

| Filename | QBO Location | What It Contains |
|----------|--------------|-----------------|
| **Customers.csv** | Sales → Customers (Export) | 200+ customers with addresses, emails, open balances |
| **ProductServiceList__*.csv** | Settings → Products & Services (Export) | ~40 services in catalog |
| **PrecisionPros_Network_Sales_by_Product_Service_Detail.csv** | Reports → Sales by Product/Service Detail (Jan 1 2023 - Today) | 4,000+ invoices with 10,500+ line items |
| **PrecisionPros_Network_A_R_Aging_Detail_Report.csv** | Reports → A/R Aging Detail (As of Today) | Invoice aging data (used to set paid/open status) |
| **PrecisionPros_Network_Transaction_Detail_by_Account.csv** | Reports → Transaction Detail by Account (Jan 1 2023 - Today, Cash basis) | ~880 expense transactions |

**File conversion note:** The Customers export from QBO comes as `.xls`. Convert it to CSV:
```bash
libreoffice --headless --convert-to csv Customers.xls --outdir ~/accounting/backend/
```

See `QBO_EXPORT_GUIDE.md` for detailed step-by-step export instructions.

---

## How to Use This System

### For a Full Re-Import (Start Fresh)

```bash
# Step 1: Export data from QBO (15 min)
# See QBO_EXPORT_GUIDE.md for detailed instructions
# Files go in: ~/accounting/backend/

# Step 2: Preview the import (no changes)
cd ~/accounting/backend
python3 run_full_import.py --dry-run

# Step 3: Execute (commits to database)
python3 run_full_import.py --commit
```

**Total time:** ~20 minutes (15 export + 5 import)

### To Identify Issues

```bash
# Run validation against current database
cd ~/accounting/backend
python3 validate_import.py
```

This generates a detailed report of:
- Missing invoices
- Date mismatches
- Line item problems
- Amount discrepancies

---

## The Process

```
START
  │
  ├─ Check CSV files exist
  │   └─ If missing: Stop with clear error message
  │
  ├─ Database Reset
  │   └─ Truncate: clients, invoices, line_items, expenses, billing_schedules, etc.
  │   └─ Preserve: users, chart_of_accounts, company_info, invoice_sequences
  │
  ├─ Import Services (~40 items)
  ├─ Import Customers (~200 items)
  ├─ Import Invoices (~4,000 with ~10,500 line items)
  ├─ Import Expenses (~880 transactions)
  ├─ Import Billing Schedules (~90 schedules)
  │
  ├─ Data Cleanup
  │   └─ Fix unit prices: unit_amount = amount ÷ qty
  │   └─ Fix subtotals: subtotal = sum of line items
  │
  ├─ Apply Manual Fixes
  │   └─ Invoice #48958 (known QBO export error)
  │
  ├─ Validation Report
  │   └─ Compare QBO source to imported DB
  │   └─ Report discrepancies and recommendations
  │
  └─ END
```

---

## Key Design Decisions

### Why This Approach?

1. **Repeatable:** Same script, same process every time
2. **Safe:** `--dry-run` mode lets you preview before committing
3. **Transparent:** Comprehensive logging shows exactly what happened
4. **Validating:** Automatic comparison catches import issues
5. **Documented:** Multiple guides for different audiences

### Idempotency

- **Customers & Services:** Skipped if already exist (name match)
- **Invoices & Expenses:** No deduplication — full reset recommended
- **Billing Schedules:** Skipped if client already has one

**Note:** For incremental updates (new customers, new invoices), use targeted SQL updates or run individual scripts.

---

## Handling Known Issues

### Missing Invoices

The validation script will report which invoices exist in QBO but not in the database. Common reasons:

1. **Deleted customers** — QBO exports invoices but import skips them if customer was deleted
   - **Fix:** Ensure all customers in QBO are exported to CSV

2. **Date filtering** — Only invoices from 2023 onwards are imported
   - **Note:** This is intentional (pre-2023 history excluded per original decisions)

3. **Name mapping** — Some QBO customer names don't match exported company names
   - **Fix:** Update `NAME_MAP` in `import_invoices_full.py` and `import_billing_schedules_full.py`

### Wrong Invoice Dates

If validation reports date mismatches:
1. Check QBO export format (Sales Detail vs AR Aging report)
2. Review date parsing logic in `import_invoices_full.py`
3. Update if needed and re-run import

### Line Item Issues

If validation reports line item problems:
```bash
python3 cleanup_data.py --commit
```

This script automatically fixes:
- Unit prices (sets unit_amount = amount ÷ qty)
- Subtotals (recalculates from line items)
- Balance due (subtotal - amount_paid)

---

## Testing the System

### Test Run (Recommended First Step)

```bash
# Preview without making changes
cd ~/accounting/backend
python3 run_full_import.py --dry-run

# Review the output to see:
# - "All required CSV files found" ✓
# - Each step preview
# - Estimated record counts
# - Log file location
```

### Live Run

```bash
python3 run_full_import.py --commit

# Takes 5-10 minutes
# Generates detailed log file
# Runs validation automatically
```

### Validation Check

```bash
python3 validate_import.py

# Compares QBO source to database
# Reports any discrepancies
# Provides recommendations for fixes
```

---

## Files Modified / Created

**Created (New):**
- `run_full_import.py` — Master import orchestrator
- `validate_import.py` — Validation/comparison script
- `QBO_EXPORT_GUIDE.md` — Export instructions
- `IMPORT_QUICK_START.md` — Quick reference guide
- `IMPORT_SETUP_SUMMARY.md` — This file

**Existing (Unchanged):**
- `import_services.py`
- `import_customers.py`
- `import_invoices_full.py`
- `import_expenses.py`
- `import_billing_schedules_full.py`
- `cleanup_data.py`

---

## Next Steps

1. **Review** the new documentation:
   - Start with `IMPORT_QUICK_START.md` for overview
   - See `QBO_EXPORT_GUIDE.md` for export instructions
   - Refer to `IMPORT_PROCEDURES.md` for detailed reference

2. **Export data from QBO** (15 min):
   - Follow the 5-step process in `QBO_EXPORT_GUIDE.md`
   - Place CSV files in `~/accounting/backend/`

3. **Run a test import** (5 min):
   ```bash
   python3 run_full_import.py --dry-run
   ```

4. **Execute full import** (5 min):
   ```bash
   python3 run_full_import.py --commit
   ```

5. **Review validation report** and fix any issues

6. **Add missing data** (if needed):
   - 8 customers need email addresses added manually
   - AutoCC customer IDs (for collections)

---

## Maintenance

The system is self-contained and maintainable:

- **To fix import bugs:** Update the individual import script, then re-run master runner
- **To add new mapping:** Update `NAME_MAP` in invoice/billing schedule scripts
- **To change what gets imported:** Edit import script logic and re-run
- **To validate changes:** Run validation script automatically (or separately)

---

## Questions?

Refer to:
- `IMPORT_PROCEDURES.md` — Complete reference with all decisions documented
- `QBO_EXPORT_GUIDE.md` — Detailed export instructions
- `IMPORT_QUICK_START.md` — Troubleshooting guide
- `validate_import.py --help` or review script comments

---

**Status:** ✅ Infrastructure ready for use  
**Date:** April 14, 2026

The system is designed to handle the complete data import lifecycle with safety, transparency, and validation. You now have a repeatable procedure that can be run whenever you need a fresh import of QBO data.
