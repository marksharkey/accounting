# QBO Data Export Guide for PrecisionPros Re-Import

**Purpose:** Complete instructions for exporting all required data from QuickBooks Online (QBO) to perform a full re-import of PrecisionPros Billing.

**Required Time:** ~15-20 minutes to export all files  
**Date This Guide Was Created:** April 14, 2026

---

## Overview

A complete PrecisionPros re-import requires **5 CSV files** from QuickBooks Online. All files should be placed in `~/accounting/backend/` before running the import scripts.

| File | What It Contains | Where to Export |
|------|-----------------|-----------------|
| **Customers.csv** | All customers with contact info and open balances | Sales → Customers |
| **ProductServiceList__*.csv** | Service catalog (40 items) | Settings → Products & Services |
| **PrecisionPros_Network_Journal.csv** | All invoices with line items (4,000+ invoices) — **Use this instead of Sales Detail** | Reports → Journal |
| **PrecisionPros_Network_A_R_Aging_Detail_Report.csv** | Open invoice balances and payment status | Reports → A/R Aging Detail |
| **PrecisionPros_Network_Transaction_Detail_by_Account.csv** | All expenses and transactions (879+ items) | Reports → Transaction Detail by Account |

---

## Step-by-Step Export Instructions

### 1. Customer Export → `Customers.csv`

**Source:** Sales → Customers

1. In QBO, click **Sales**
2. Click **Customers**
3. Click the **Export** icon (top right, looks like a down arrow in a box)
4. Choose **Excel** (this gives you `.xls` format)
5. Save as `Customers.xls`

**Important:** QBO exports this as `.xls` (not `.xlsx`). Convert it to CSV before importing:

```bash
cd ~/accounting/backend
libreoffice --headless --convert-to csv Customers.xls --outdir .
# Result: Customers.csv
```

**Verify:** Open `Customers.csv` and check that:
- First row contains column headers: Name, Company name, Email, etc.
- 200+ rows of customer data
- Company name field is populated (this is what we import)

---

### 2. Product/Service Export → `ProductServiceList__*.csv`

**Source:** Settings → Products & Services

1. In QBO, click **Settings** (gear icon, top right)
2. Click **Products and Services**
3. Click **Export** (top right)
4. Choose **CSV** format
5. Save as `ProductServiceList__*.csv`

**Note:** QBO includes a timestamp in the filename automatically. The file will be named something like:
```
ProductServiceList__9341456449516862_04_13_2026.csv
```

**Verify:** Open the file and check:
- First row has headers: Name, Type, Income Account, etc.
- Contains ~40 active services
- Skip rows like "PmntDiscount_*" and internal placeholders (import script handles this)

---

### 3. Journal Report → `PrecisionPros_Network_Journal.csv`

**Source:** Reports → Journal

The Journal report contains ALL invoices with complete line item details. **This is now the primary source for invoice imports** (replaces Sales by Product/Service Detail).

1. In QBO, click **Reports** (left sidebar)
2. Search for **Journal** (or navigate through Accounting category)
3. Set date range: **From:** Jan 1, 2023 | **To:** Today (current date)
4. Click **Run report**
5. Click **Export** (top right)
6. Choose **CSV** format
7. Save as `PrecisionPros_Network_Journal.csv`

**Verify:** Open the file and check:
- Headers in rows 1-4
- Data starts at row 5 with blank first column for data rows
- Each invoice has: AR line (Accounts Receivable) + service line items
- Contains 4,000+ invoices with 4,000+ rows of line items
- Invoices from 2023 onwards
- Amount column has line item amounts

**Why Journal instead of Sales Detail?**
- Journal captures **all invoices** (Sales Detail was missing ~58 invoices)
- More reliable export from QBO
- Complete line item data included

---

### 4. A/R Aging Detail Report → `PrecisionPros_Network_A_R_Aging_Detail_Report.csv`

**Source:** Reports → A/R Aging Detail

This report tells us which invoices are paid vs open (used to set invoice status).

1. In QBO, click **Reports**
2. Search for **A/R Aging Detail** (or navigate through Sales category)
3. Set **As of date:** Today (current date)
4. Click **Run report**
5. Click **Export** (top right)
6. Choose **CSV** format
7. Save as `PrecisionPros_Network_A_R_Aging_Detail_Report.csv`

**Verify:** Open the file and check:
- First row has headers: Name, Invoice #, Date, Due Date, Open Balance, etc.
- Contains invoice aging data
- Open Balance column shows amounts still owed (0 = paid)

---

### 5. Transaction Detail by Account Report → `PrecisionPros_Network_Transaction_Detail_by_Account.csv`

**Source:** Reports → Transaction Detail by Account

This report contains all expenses (used by expense import).

1. In QBO, click **Reports**
2. Search for **Transaction Detail by Account** (or navigate through Accounting category)
3. Set date range: **From:** Jan 1, 2023 | **To:** Today
4. **Important:** Set to **Cash basis** (not Accrual)
5. Click **Run report**
6. Click **Export** (top right)
7. Choose **CSV** format
8. Save as `PrecisionPros_Network_Transaction_Detail_by_Account.csv`

**Verify:** Open the file and check:
- First row has headers: Account, Type, Date, Name, Amount, etc.
- Contains 800+ transaction rows
- Amount column shows debits/credits (negatives for expenses)

---

## File Placement

After exporting, all CSV files should be in:
```
~/accounting/backend/
```

**Quick check:**
```bash
ls -la ~/accounting/backend/*.csv
```

You should see:
- `Customers.csv`
- `ProductServiceList__*.csv` (with timestamp)
- `PrecisionPros_Network_Sales_by_Product_Service_Detail.csv`
- `PrecisionPros_Network_A_R_Aging_Detail_Report.csv`
- `PrecisionPros_Network_Transaction_Detail_by_Account.csv`

---

## Import Procedure

Once all files are in place, run the master import script:

```bash
cd ~/accounting/backend

# Preview (no changes)
python3 run_full_import.py --dry-run

# Execute (commits changes to database)
python3 run_full_import.py --commit
```

The script will:
1. ✓ Verify all CSV files exist
2. ✓ Reset the database
3. ✓ Import services, customers, invoices, expenses, billing schedules
4. ✓ Run cleanup and manual fixes
5. ✓ Validate the results
6. ✓ Generate a report

**Total time:** 5-10 minutes

---

## Troubleshooting

### "Customers.xls conversion failed"
Make sure LibreOffice is installed:
```bash
brew install libreoffice
```

### "ProductServiceList CSV not found"
QBO adds a timestamp to the filename. Check:
```bash
ls -la ~/accounting/backend/ProductServiceList__*
```

The import script will detect it automatically.

### "Report not found in QBO"
QBO's reports interface varies slightly. Use the search box at the top of Reports to find the report by name.

### "Date range issues"
Always use these date ranges:
- **Sales by Product/Service:** Jan 1, 2023 to Today
- **A/R Aging:** As of Today
- **Transaction Detail:** Jan 1, 2023 to Today

This ensures consistency across imported data (2023+ invoices, all open balances, all expenses since 2023).

---

## When to Re-Export

Export fresh files **whenever you need a clean re-import** to fix data quality issues. Common scenarios:

- **After fixing bugs** in import scripts — export fresh to apply the fixes
- **Quarterly backups** — export to create a backup/snapshot
- **Before major refactoring** — export to ensure a clean state to work from
- **After significant QBO changes** — if you added/deleted many customers or services

**Do NOT re-export for incremental updates** — once PrecisionPros is live, maintain invoices natively and only re-import when necessary.

---

## Export Notes from IMPORT_PROCEDURES.md

### Customers Export
- Uses `Company name` field (different from `Name` field for some customers)
- 8 customers have no email — add manually after import
- Import skips deleted customers automatically

### Sales Detail Report
- Contains line item details (qty, unit price, amount)
- QBO exports `amount` as the prorated amount actually charged (not qty × unit_price)
- Cleanup script fixes this: `unit_amount = amount ÷ qty`

### A/R Aging Report
- Essential for determining invoice status (paid vs open)
- Open Balance > 0 = invoice is unpaid
- Used to calculate `amount_paid` and `balance_due`

### Transaction Detail Report
- No filter for expense accounts in the export
- Import script filters internally (skips income/asset/liability accounts)
- 879 expense transactions imported ($453,994 total)

### Product/Service Export
- Contains ~40 active services
- Import script skips 7 internal QBO placeholders automatically
- Income accounts are mapped to PrecisionPros categories

---

*Last Updated: April 14, 2026*
