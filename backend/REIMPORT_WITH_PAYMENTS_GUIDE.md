# Full Re-Import Guide with Payments & Journal Entries

**Last Updated:** April 26, 2026

---

## Overview

This guide covers a complete database re-import with:
- Invoice and line item data (from QBO Journal)
- Expense transactions
- Billing schedules
- **NEW: GL journal entries** for accrual-basis P&L reporting
- **NEW: Payment records** to track invoice payment history
- Payment reconciliation to update invoice balances
- Data cleanup and manual fixes
- Known data quality adjustments

**Total Time:** ~30 minutes (15 min export + 15 min import)

---

## Step 1: Export Required Reports from QBO

You'll need these 6 CSV files. Export from QBO with date range **Jan 1, 2023 to Today**:

### 1. **Customers.csv**
- Location: Sales → Customers (Export)
- Format: Excel (.xls), will convert to CSV
- Content: All 200+ customer records with emails, addresses

### 2. **ProductServiceList__*.csv**
- Location: Settings → Products & Services (Export)
- Format: CSV
- Content: ~40 services in catalog

### 3. **PrecisionPros_Network_Journal.csv** ⭐ **KEY REPORT**
- Location: Reports → Journal
- Filters: Date range Jan 1, 2023 to Today
- Content: Complete GL journal with all invoices + line items + expenses
- **Why this:** Captures ALL 4,260 invoices (Sales Detail report was missing 58)

### 4. **PrecisionPros_Network_A_R_Aging_Detail_Report.csv**
- Location: Reports → A/R Aging Detail
- **Date Setting:** Set "As of" to **Today** (no date range — this is a snapshot report)
- Content: Invoice aging data as of today (used for open balance + due date)

### 5. **PrecisionPros_Network_Transaction_Detail_by_Account.csv**
- Location: Reports → Transaction Detail by Account
- Filters: Date range Jan 1, 2023 to Today, Cash basis
- Content: ~880 expense transactions

### 6. **PrecisionPros_Network_Invoices_and_Received_Payments.csv** ⭐ **NEW**
- Location: Reports → Invoices and Received Payments
- Filters: Date range Jan 1, 2023 to Today
- Content: Invoice list with payment transactions
- **Why this:** Imports payment records to match QBO payment history

---

## Step 2: Place CSV Files in Backend Directory

```bash
# Copy all exports to the backend directory
cp ~/Downloads/*.csv ~/accounting/backend/

# Convert Customers.xls to CSV if needed
cd ~/accounting/backend
libreoffice --headless --convert-to csv Customers.xls --outdir .
```

Verify files are in place:
```bash
ls -la ~/accounting/backend/*.csv | grep -E "Customers|ProductServiceList|Journal|Aging|Transaction|Invoices_and_Received"
```

---

## Step 3: Preview the Import (No Changes)

```bash
cd ~/accounting/backend
python3 run_full_import.py --dry-run
```

This will:
- ✓ Verify all CSV files exist
- ✓ Show what WILL be imported (customers, invoices, expenses, billing schedules, journal entries, payments)
- ✓ Calculate estimated record counts
- ✓ Generate log file
- ✓ **Make NO database changes**

Review the output carefully. Look for:
- File count matches expected (Customers, ProductServiceList, Journal, AR Aging, Transactions, Invoices & Payments)
- No errors in pre-import checks
- Estimated record counts seem reasonable

---

## Step 4: Execute the Full Import

```bash
python3 run_full_import.py --commit
```

**What happens (in order):**

1. **Database Reset** — Truncate all data tables (preserve users, COA, company info)
2. **Services Import** — ~40 services
3. **Customers Import** — ~200 clients
4. **Invoice Import** — ~4,260 invoices with line items (from Journal)
5. **Expense Import** — ~880 transactions
6. **Billing Schedules Import** — ~92 schedules
7. **Journal Entries Import** — GL entries for P&L reporting
8. **Payment Import** — Payment records from QBO
9. **Payment Reconciliation** — Update invoice amounts_paid and balance_due
10. **Data Cleanup** — Fix unit prices and subtotals
11. **Manual Fixes** — Apply known fixes (e.g., invoice #48958: $1 → $25)
12. **Overpayment Credits** — Create credit memos for 4 clients (zhost, Whiteent, L F Rothchild, SteamworksAZ)
13. **Invoice Exclusions** — Mark 7 invoices as excluded from AR aging (data quality fixes)

---

## Step 5: Verify Import Success

Check the import log (auto-generated):
```bash
tail -f ~/accounting/backend/import_log_*.txt
```

Look for:
- ✓ "All required CSV files found"
- ✓ Each import step completed successfully
- ✓ Record counts seem reasonable
- ✓ No FATAL errors

---

## Step 6: Verify in the UI

### Start the dev servers (if not already running)

**Terminal 1 — Backend:**
```bash
cd ~/accounting/backend
source venv/bin/activate
uvicorn main:app --port 8010 --reload
```

**Terminal 2 — Frontend:**
```bash
cd ~/accounting/frontend
npm run dev
```

Navigate to http://localhost:5173 and check:

### Dashboard
- [ ] Invoice count displayed
- [ ] Recent invoices show up
- [ ] Client count is correct (~200)
- [ ] No error messages

### Invoices Page
- [ ] Can view invoice list
- [ ] Line items display correctly
- [ ] Amounts match expectations
- [ ] Payment amounts show correctly (NEW)
- [ ] Invoice status reflects payment status (draft/sent/paid/partially_paid)

### Clients Page
- [ ] Client list shows ~200 clients
- [ ] Client details display correctly
- [ ] Account balances show

### Reports → A/R Aging
- [ ] Invoice count and totals reasonable
- [ ] No major discrepancies vs QBO
- [ ] Excludes the 7 known discrepant invoices
- [ ] Overpayment credits display correctly for 4 clients

---

## Known Data Quality Issues (Already Fixed)

These invoices are known to be discrepant with QBO and are excluded from AR aging:

| Client | Amount(s) | Issue |
|--------|-----------|-------|
| cyberabbi.com | $50.61 | QBO export issue |
| Get Green Earth(2) | $50 + $200 | Duplicate/duplicate |
| KATZ | $0.40 | Rounding error |
| Rescate de San Carlos | $9.27 | Pre-migration data |
| Sommer, Eric | $664.05 | Already has valid $90 invoice |
| Terriann Muller | $135.00 | QBO cleanup |

**Action:** These are automatically excluded during import via `exclude_specific_invoices.py`

---

## Known Overpayments (Already Fixed)

These 4 clients have overpayment credits from QB Desktop migration:

| Client | Amount | Status |
|--------|--------|--------|
| zhost | $45.20 | Credit memo created |
| Whiteent | $25.00 | Credit memo created |
| L F Rothchild | $50.00 | Credit memo created |
| SteamworksAZ | $59.80 | Credit memo created |

**Action:** Credit memos are created automatically via `create_overpayment_credits.py`

---

## Troubleshooting

### Missing CSV Files
**Error:** "❌ MISSING CSV FILES"

**Fix:** 
- Verify all 6 exports are in `~/accounting/backend/`
- Check file names match exactly (except ProductServiceList which has a timestamp)
- Re-export from QBO if files are incomplete

### Database Connection Error
**Error:** "❌ SQL Error: Access denied"

**Fix:**
- Ensure MySQL is running: `mysql -u ppros -p -e "SELECT 1;"`
- Verify .env credentials: `cat ~/accounting/backend/.env`
- Check password in .env is correct

### Payment Import Fails
**Error:** "❌ Script failed: import_payments_from_report.py"

**Fix:**
- Verify `PrecisionPros_Network_Invoices_and_Received_Payments.csv` exists
- Check it was exported with correct date range (Jan 1, 2023 to Today)
- Try --dry-run first to see what's failing

### Validation Report Shows Missing Invoices
**Error:** Validation reports invoices in QBO but not in database

**Common causes:**
- Customers not exported (deleted customers in QBO)
- Name mapping issue (customer name doesn't match)
- Date filtering (pre-2023 invoices excluded by design)

**Fix:**
- Update NAME_MAP in import scripts if customers were added
- Re-export Customers CSV with all customers (including deleted)

---

## Post-Import Next Steps

1. **Check payments are recorded:**
   ```bash
   # In MySQL
   SELECT COUNT(*) FROM payments;
   SELECT COUNT(DISTINCT invoice_id) FROM payments;
   ```

2. **Verify journal entries imported:**
   ```bash
   SELECT COUNT(*) FROM journal_entries;
   SELECT COUNT(DISTINCT gl_account_code) FROM journal_entries;
   ```

3. **Add missing customer data:**
   - 8 customers still need email addresses (see IMPORT_QUICK_START.md)
   - AutoCC customer IDs (if using automated collections)

4. **Test key workflows:**
   - Create a new invoice → verify it shows up
   - Record a payment → verify balance updates
   - Create a credit memo → verify AR aging reflects it

---

## Rolling Back if Needed

If something goes wrong, you can restore from backup:

```bash
# Check recent backups
ls -lh ~/.backups/precisionpros_*.sql | tail -5

# Restore (DANGEROUS — only if import failed)
mysql -u ppros -p precisionpros < ~/.backups/precisionpros_LATEST.sql
```

---

## Questions?

Refer to:
- `IMPORT_QUICK_START.md` — Quick overview of import process
- `QBO_EXPORT_GUIDE.md` — Detailed export instructions
- `IMPORT_PROCEDURES.md` — Complete reference with all decisions
- `IMPORT_INFRASTRUCTURE.md` — Technical architecture

---

**Remember:** Always do a `--dry-run` first before committing!

