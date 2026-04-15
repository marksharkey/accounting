# QBO → PrecisionPros Billing: Import Procedures & Lessons Learned

**Date:** April 14, 2026  
**Prepared by:** Claude (Anthropic)  
**Purpose:** Complete record of the QBO data migration — what was done, what problems were encountered, how they were resolved, and how to repeat or update the import cleanly.

---

## Table of Contents
1. [Overview](#overview)
2. [Source Files Required](#source-files-required)
3. [Pre-Import: Database Reset](#pre-import-database-reset)
4. [Step 1: Service Catalog](#step-1-service-catalog)
5. [Step 2: Customers / Clients](#step-2-customers--clients)
6. [Step 3: Invoices + Line Items](#step-3-invoices--line-items)
7. [Step 4: Expenses](#step-4-expenses)
8. [Step 5: Billing Schedules](#step-5-billing-schedules)
9. [Step 6: Post-Import Cleanup](#step-6-post-import-cleanup)
10. [Known Issues & Decisions](#known-issues--decisions)
11. [Name Mapping Reference](#name-mapping-reference)
12. [What Was NOT Imported](#what-was-not-imported)
13. [Re-Import Procedure](#re-import-procedure)
14. [Incremental Update Strategy](#incremental-update-strategy)

---

## Overview

PrecisionPros Billing was built to replace QuickBooks Online (QBO) for a sole-proprietor web hosting/IT services business. The migration imports:
- 202 clients
- 4,011 invoices with 10,576 line items (2023–2026)
- 879 expense transactions ($453,994 over 3 years)
- 40 service catalog items
- 92 billing schedules with full line item detail

**Collections cutoff date:** April 13, 2026. The backend collections router only triggers late fee / suspension / deletion logic for invoices created ON OR AFTER this date. All imported historical invoices are excluded from collections automation.

---

## Source Files Required

All files should be exported from QBO and placed in `~/accounting/backend/` before running import scripts.

| File | QBO Export Path | Script that uses it |
|------|----------------|-------------------|
| `Customers.csv` | Sales → Customers → Export (XLS, then convert to CSV via `libreoffice --headless --convert-to csv`) | `import_customers.py` |
| `ProductServiceList__*.csv` | Settings → Products & Services → Export | `import_services.py` |
| `PrecisionPros_Network_Sales_by_Product_Service_Detail.csv` | Reports → Sales by Product/Service Detail → Jan 1 2023 to Today → CSV | `import_invoices_full.py`, `import_billing_schedules_full.py` |
| `PrecisionPros_Network_A_R_Aging_Detail_Report.csv` | Reports → A/R Aging Detail → As of Today → CSV | `import_invoices_full.py` |
| `PrecisionPros_Network_Transaction_Detail_by_Account.csv` | Reports → Transaction Detail by Account → Jan 1 2023 to Today → Cash basis → CSV | `import_expenses.py` |

### Notes on QBO exports
- The **Customers export** comes as `.xls` (not `.xlsx`). Convert it first:
  ```bash
  libreoffice --headless --convert-to csv ~/Downloads/Customers.xls --outdir ~/accounting/backend/
  ```
- The **Products & Services export** has a `Table 1` row as the first line — the import script handles this automatically.
- The **Transaction Detail** report has NO filter for expense accounts — the script filters internally.
- QBO **does not export recurring transactions** with line item detail. Billing schedules must be reconstructed manually from invoice history (see Step 5).
- QBO **does not have a payment history export** that links payments to invoices reliably. Payment history import was skipped.

---

## Pre-Import: Database Reset

Before a full re-import, truncate all transaction data while preserving users, chart of accounts, and system settings.

```bash
mysql -u ppros -p precisionpros <<'EOF'
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
SET FOREIGN_KEY_CHECKS = 1;
EOF
```

**Preserved tables (do NOT truncate):**
- `users` — mark and candace login accounts
- `chart_of_accounts` — income/expense account structure
- `company_info` — PrecisionPros Network company details
- `invoice_sequences` — invoice numbering state

---

## Step 1: Service Catalog

**Script:** `import_services.py`  
**Source:** `ProductServiceList__*.csv`

```bash
python3 import_services.py --dry-run
python3 import_services.py --commit
```

**What it does:**
- Imports 40 active services (7 internal QBO placeholders are skipped)
- Maps QBO income accounts to PrecisionPros categories
- Sets `default_cycle = monthly` for all services (can be changed per-service after import)

**Skipped items:**
- `PmntDiscount_*` — internal QBO payment discount items
- `credit`, `migration`, `Services` — zero-value QBO placeholders

**Known issue:** The CSV filename contains a timestamp (`ProductServiceList__9341456449516862_04_13_2026.csv`). Update the `--csv` argument or rename the file if re-exporting on a different date.

---

## Step 2: Customers / Clients

**Script:** `import_customers.py`  
**Source:** `Customers.csv`

```bash
python3 import_customers.py --dry-run --csv Customers.csv
python3 import_customers.py --commit --csv Customers.csv
```

**What it does:**
- Imports 202 clients
- Uses `Company name` field when different from `Name` field (QBO has both)
- Splits comma-separated emails into `email` (primary) and `email_cc`
- Imports open balances as `account_balance`
- Strips embedded newlines from address fields
- Strips `.0` suffix from zip codes exported as floats

**Important behavior:** The script uses `Company name` over `Name` when they differ. This is the source of all the name mapping issues in later steps — QBO invoices reference the `Name` field, but we imported clients using `Company name`. The `NAME_MAP` in the invoice import script bridges this gap.

**Clients with no email (8 total):** These import with a blank email. Add emails manually after import:
- Dr. Adams:psychological
- Enterprise Communications:echost.com
- ERC:erc programming
- Frick, Mike:onlearn
- mark sharkey
- Sommer, Eric:icapture.com
- Svestka, Lura:jta
- Svestka, Lura:programming

**Default values set on all clients:**
- `authnet_recurring = false` (set to true for clients using Auth.net recurring billing)
- `account_status = active`
- `late_fee_type = none`
- `auto_send_invoices = False`
- `collections_paused = False`

---

## Step 3: Invoices + Line Items

**Script:** `import_invoices_full.py`  
**Sources:** `PrecisionPros_Network_Sales_by_Product_Service_Detail.csv` + `PrecisionPros_Network_A_R_Aging_Detail_Report.csv`

```bash
python3 import_invoices_full.py --dry-run
python3 import_invoices_full.py --commit
```

**What it does:**
- Parses 4,255 invoices from the Sales Detail report (organized by product/service)
- Cross-references A/R Aging Detail to identify open balances and set invoice status
- Skips invoices for deleted clients
- Sets invoice status: `paid` (no open balance), `sent` (fully unpaid), `partially_paid` (some paid)
- Imports in batches of 200 with intermediate commits
- Updates `client.account_balance` for invoices with open balances

**Invoice status logic:**
- If invoice number appears in AR Aging Detail with open_balance > 0 → `sent` or `partially_paid`
- If not in AR Aging → `paid` (assumed fully collected)
- `amount_paid = subtotal - open_balance`
- `due_date` from AR Aging if available, otherwise `created_date + 12 days`

**NAME_MAP — critical:** QBO invoice customer names often differ from the company_name we imported. The script has a complete mapping of 54 QBO names → PrecisionPros company names. If new clients are added to QBO and re-imported, check for new mismatches in the "Clients not matched" output and add them to NAME_MAP.

**Known issue — prorated line items:** QBO exports the `amount` field as the prorated amount actually charged, not `qty × unit_price`. After import, `cleanup_data.py` corrects unit_amount to match (unit_amount = amount ÷ qty). This preserves exact historical billing amounts.

**Known issue — invoice #48958:** This invoice shows $1.00 instead of $25.00 because QBO exported the payment amount instead of the invoice amount for this line item. After import, fix manually:
```sql
UPDATE invoice_line_items li
JOIN invoices i ON i.id = li.invoice_id
SET li.unit_amount = 25.00, li.amount = 25.00
WHERE i.invoice_number = '48958';

UPDATE invoices
SET subtotal = 25.00, total = 25.00, amount_paid = 1.00, balance_due = 24.00
WHERE invoice_number = '48958';
```

---

## Step 4: Expenses

**Script:** `import_expenses.py`  
**Source:** `PrecisionPros_Network_Transaction_Detail_by_Account.csv`

```bash
cp ~/Downloads/PrecisionPros\ Network_Transaction\ Detail\ by\ Account.csv \
   ~/accounting/backend/PrecisionPros_Network_Transaction_Detail_by_Account.csv

python3 import_expenses.py --dry-run
python3 import_expenses.py --commit
```

**What it does:**
- Imports 879 expense transactions ($453,994 over Jan 2023 – Apr 2026)
- Filters to expense-only accounts (skips income, asset, liability accounts)
- Only imports transaction types: Expense, Check, Bill, Bill Payment, Journal Entry, Credit Card Credit
- Amounts stored as absolute values (positive), negated from QBO's negative format
- Links to chart_of_accounts by category name match

**Expense accounts imported:**
Marketing, Meals, Purchased Services, Supplies, TA (Travel & Auto), Taxes (2022/2023/2024/2025), Web Hosting Expenses, A&G, Bank Fees, Credit Card Fees, Dial Up, Dues & Subscriptions, Postage, Telephone, Server Management Fees, Domain Registrations, Email Hosting, Servers, Bad Debt, Reconciliation Discrepancies

**Accounts skipped (income/asset/liability):**
Chase Checking, Checking-wcws, Amex Savings, Accounts Receivable, A/R - simply hosting, Loan From Sharkey's, Owner's Draw, Uncategorized Income, Domain Name Registrations (income), Email Hosting (income), Managed Servers, Services, Web Hosting, Web Programming

**Note:** The `--dry-run` output includes a `By account` summary with transaction counts and totals — review this before committing to verify the numbers look reasonable.

---

## Step 5: Billing Schedules

**Script:** `import_billing_schedules_full.py`  
**Source:** `PrecisionPros_Network_Sales_by_Product_Service_Detail.csv` (reused from Step 3)  
**Also requires:** Recurring transactions list pasted manually from QBO UI

```bash
python3 import_billing_schedules_full.py --dry-run
python3 import_billing_schedules_full.py --commit
```

**Background:** QBO does not export recurring transactions with line item detail, and has no CSV export for the recurring transactions list at all. The procedure was:

1. In QBO, go to Settings → Recurring Transactions
2. Select all text on the page and paste into chat with Claude
3. Claude parsed 95 recurring schedules (customer, interval, next date, amount)
4. For each client, the script finds the most recent invoice whose total matches the expected recurring amount
5. Line items are taken from that source invoice and used as the billing schedule line items

**Interval mapping:**
- Every Month → `monthly`
- Every 3 Months → `quarterly`
- Every Year / Every 12 Months → `annual`

**Special cases handled:**

| Client | Issue | Resolution |
|--------|-------|-----------|
| Emerge Inc. | Custom negotiated server pricing ($185 + $758.99) | Hardcoded original amounts, not catalog prices |
| Mike Lorts | Had 13x Domain Registration on monthly schedule | Removed — domain registrations are annual, not monthly |
| Atlantis Travel Agency | Most recent invoice ($138) didn't match QBO amount ($178) | Manual override with correct line items |
| Hawaii Health Guide | Recent invoices included late fees | Manual override without late fee |
| Louisiana, LLC | Most recent invoice had one-time domain renewal | Used earlier clean invoice (#49212) |
| Timus, Inc. | Recent invoices included late fees | Manual override without late fee |
| edgepowersolutions.net | Annual billing, no matching monthly invoice | Manual: 12x Business Email @ $15 = $180 |
| sancarlosproperty.com | Most recent invoice had domain renewal | Manual override without domain |

**Prorated line items:** Many source invoices had split/prorated lines (one service appearing as 2 lines that sum to the full amount). These were consolidated in `CLEAN_LINES` within the script. Custom/negotiated pricing was preserved from the original invoices — catalog prices were NOT applied to clients with negotiated rates.

**Result:** 92 billing schedules — 78 monthly, 9 quarterly, 5 annual. MRR: $12,655.57/month.

---

## Step 6: Post-Import Cleanup

**Script:** `cleanup_data.py`

```bash
python3 cleanup_data.py --dry-run
python3 cleanup_data.py --commit
```

**What it fixes:**
1. Invoice line items where `unit_amount ≠ amount ÷ quantity` — sets `unit_amount = amount ÷ qty` to preserve actual billed amounts
2. Invoice subtotals that don't match sum of line items (recalculates subtotal, total, balance_due)
3. Billing schedule line items with same mismatch
4. Billing schedule totals that don't match their line item sums

**After cleanup, apply the invoice #48958 fix manually (see Step 3).**

**Then run the collections cutoff fix** — the backend already has `COLLECTIONS_CUTOFF_DATE = date(2026, 4, 13)` in `routers/collections.py`. This prevents historical imported invoices from triggering suspension/deletion alerts.

---

## Known Issues & Decisions

| Issue | Decision |
|-------|----------|
| QBO exports `amount` as prorated value, not `qty × unit_price` | Set `unit_amount = amount ÷ qty` to preserve exact billed amounts |
| Invoice #48958 has $1.00 line item (should be $25.00) | Manual SQL fix after import |
| 8 clients have no email address | Import with blank email, fix manually |
| Historical invoices trigger false suspension alerts | Collections cutoff date filters them out |
| Payment history not imported | Skipped — all imported invoices either show as `paid` or `sent/partially_paid` based on AR Aging |
| Pre-2023 invoices not imported | Decision: only 2023+ invoices imported; older history excluded |
| QBO recurring transactions have no CSV export | Paste from QBO UI, parse manually |
| QBO `Name` ≠ `Company name` for 54 clients | Full NAME_MAP maintained in `import_invoices_full.py` and `import_billing_schedules_full.py` |
| Billing schedule line items have custom pricing | Preserved from source invoices — catalog prices not applied |

---

## Name Mapping Reference

These are clients where QBO's invoice `Name` field differs from the `Company name` used in PrecisionPros. Both scripts (`import_invoices_full.py` and `import_billing_schedules_full.py`) contain this full mapping.

| QBO Invoice Name | PrecisionPros Company Name |
|-----------------|---------------------------|
| Sommer, Eric | Arkadia Konsulting |
| autobenefit | Concierge Coaches |
| sancarlosproperty | sancarlosproperty.com |
| ehappyhour.com, Inc. | Timus, Inc. |
| Atlantis Travel Agency | Atlantis Travel Agency, Athens |
| Contractors Parts and Supply | Contractors Crance Co. Inc. |
| ImageTag, Inc. | Paymerang, LLC |
| Net-Flow Corporation- | Net-Flow Corporation |
| Lombardcompany.com | Lombard Architectural Precast Products |
| Actuarial Work Products, Inc. | Castevens Technologies LLC |
| Architectural Visual Inc. | Architectural Visual, Inc. |
| B Factor Group | 1SEO Digital Agency |
| CVISION Technologies | Foxit Software |
| CYoungConsulting.com | C Young Consulting LLC |
| ChristopherAugustine.com | Christopher Augustine, LTD |
| DesignGate Pte. Ltd. | DesignGate pte Ltd. |
| Dr. Adams | Dr. D.B. Adams |
| Eternallygreen.com | Integrity Landscaping |
| Fine Design Interiors | Fine Design Interiors, Inc. |
| Hearnelake | Hearne Lake Operations Ltd |
| International Fishing Devices | International Fishing Devices, Inc. |
| L F Rothchild | Shearson Financial |
| Lambert, Bernadette | Bernadette/eyre |
| MEDAxiom, LLC | MEDAxiom, LLC. |
| Ned Freeman | calpreps.com |
| Newmedia | New Media Sales & Management Co. Ltd. |
| Pacific Holidays, Inc. | JC Pacific Trading Co. |
| Paul Brahaney | Jog A Dog |
| Peterson-mfg.com | Peterson Manufacturing Co. |
| Preserve  Resort HOA? | Preserve Resort HOA? |
| Rick Long | Rick Long - RFS Corporation |
| Robyn | Robyn Glazner |
| Sanson Financial Solutions, LLC | Sanson Insurance & Financial Services, LL |
| Serenity Canine Retreat | Serentiy Canine Retreat |
| Sharkey, Keith | Key Real Estate Investments, LLC |
| Sparle 'n Dazzle | Sparkle n Dazzle |
| SteelRep | Sun Belt Steel & Aluminum, Inc |
| Svestka, Lura | JTA, Inc. |
| The Pension Studio | Darbster Foundation |
| Tires to Go | Tires2go Inc. |
| Whatwatt.com/service lamp | Whatwatt LLC |
| Whiteent | White Enterprises |
| Worldfamouscomics.com | WF Comics |
| X-Tel Communications | James Rahfaldt |
| Zhongwen | Zhongwen.com |
| aeroware | Aero Wear |
| agroresources.com | Agro Resources |
| bingobuddies | Soleau software |
| druckers.com | Druckers |
| kimm.org | David Kimm Fesler LTD |
| peoplesourceonline | Peoplesource LLC |
| platypuscreative | Platypus Creative |
| psgraphics | PS Graphics, Inc. |
| zhost | Ponder and Assoc |

---

## What Was NOT Imported

| Data | Reason |
|------|--------|
| Payment history | QBO payment export doesn't reliably link payments to invoices. All imported invoices show correct paid/unpaid status from AR Aging. |
| Invoices before 2023 | Decision: pre-2023 history excluded to keep data manageable. 22 pre-2023 invoices with open balances were also excluded. |
| Billing schedule line items from QBO | QBO doesn't export these. Reconstructed from most recent matching invoice. |
| Credit memos | Not exported or imported. Create manually as needed. |
| Estimates | Not exported or imported. |
| Deleted clients' invoices | 244 invoices for deleted QBO clients were skipped during import. |
| authnet_customer_id | QBO doesn't store Authorize.net customer IDs. Must be populated manually per client. |

---

## Re-Import Procedure

To completely wipe and re-import all data from fresh QBO exports:

```bash
cd ~/accounting/backend

# Step 0: Export fresh files from QBO (see Source Files section)
# Place all CSV files in ~/accounting/backend/

# Step 1: Reset database
mysql -u ppros -p precisionpros <<'EOF'
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
SET FOREIGN_KEY_CHECKS = 1;
EOF

# Step 2: Service catalog
python3 import_services.py --dry-run
python3 import_services.py --commit

# Step 3: Clients
python3 import_customers.py --dry-run --csv Customers.csv
python3 import_customers.py --commit --csv Customers.csv

# Step 4: Invoices + line items
python3 import_invoices_full.py --dry-run
python3 import_invoices_full.py --commit

# Step 5: Expenses
python3 import_expenses.py --dry-run
python3 import_expenses.py --commit

# Step 6: Billing schedules
python3 import_billing_schedules_full.py --dry-run
python3 import_billing_schedules_full.py --commit

# Step 7: Cleanup
python3 cleanup_data.py --dry-run
python3 cleanup_data.py --commit

# Step 8: Manual fix for invoice #48958
mysql -u ppros -p precisionpros <<'EOF'
UPDATE invoice_line_items li
JOIN invoices i ON i.id = li.invoice_id
SET li.unit_amount = 25.00, li.amount = 25.00
WHERE i.invoice_number = '48958';
UPDATE invoices
SET subtotal = 25.00, total = 25.00, amount_paid = 1.00, balance_due = 24.00
WHERE invoice_number = '48958';
EOF
```

**Total time:** approximately 5–10 minutes for all steps.

---

## Incremental Update Strategy

Rather than a full re-import, consider these targeted updates as your QBO data changes:

### New clients added in QBO
Re-run `import_customers.py` — it skips existing clients by `company_name` match, only inserting new ones.

### New invoices (ongoing)
Once you start creating invoices natively in PrecisionPros, stop importing invoices from QBO. The transition date is April 13, 2026.

### Updated open balances (payments received in QBO before cutover)
Run a targeted SQL update using a fresh AR Aging Detail export rather than re-importing all invoices.

### Expenses
Re-run `import_expenses.py` with a narrower date range. The script doesn't check for duplicates by date/vendor/amount — add a `--since` date argument to Claude Code to avoid double-importing.

### Billing schedule changes
The billing schedules are now native to PrecisionPros — edit them directly in the UI. Do not re-run `import_billing_schedules_full.py` unless doing a full reset, as it will skip clients that already have a schedule.

### When to do a full re-import
Only if there are significant data quality issues discovered across many clients. The scripts are idempotent for clients and services (skip duplicates), but invoices and expenses do not deduplicate — a full reset + re-import is the safest approach if needed.

---

*End of import procedures document.*
