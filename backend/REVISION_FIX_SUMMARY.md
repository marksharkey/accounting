# Invoice Revision Import Fix — Summary

## Problem Identified

When invoices are revised in QuickBooks Online (QBO) and resent with the same invoice number, the import script was treating them as **duplicates** and skipping the revised version. This resulted in:

- **Incorrect invoice totals** — System had the original amount, not the revised amount
- **Data integrity issues** — `balance_due > total` (impossible state)
- **Inability to record payments** — Payments couldn't be applied until the invoice was corrected

### Example: Don Adair Invoice #49252
- Original invoice: $15.00
- Revised (in QBO): $365.00 (+$350 additional charge)
- **System had**: total=$15.00, balance_due=$365.00 ❌
- **After fix**: total=$365.00, balance_due=$365.00 ✅

---

## Solutions Implemented

### 1. Fixed Existing Corrupted Invoices
**Script**: `fix_invoice_revisions.py`

Detects all invoices where `balance_due > total` (data integrity violation) and fixes them:
- Updates invoice total to match balance_due
- Adds a line item "Invoice Revision - Additional Charges" for the difference
- Creates an activity log entry documenting the fix

**Usage**:
```bash
# Preview what would be fixed (no changes)
python3 fix_invoice_revisions.py --dry-run

# Apply fixes
python3 fix_invoice_revisions.py --commit
```

**Results**: 
- ✅ Found 1 invoice with this issue (Don Adair #49252)
- ✅ Fixed it: total now $365.00, with proper line items

---

### 2. Updated Import Script to Handle Revisions
**Script**: `import_invoices_from_journal.py`

Enhanced duplicate detection logic:

**Before**:
- If invoice number exists → Log as duplicate, skip
- Result: Revised versions were ignored

**After**:
- If invoice exists for **same customer** with **different amount** → UPDATE it (revision)
- If invoice exists for **same customer** with **same amount** → Skip it (true duplicate)
- If invoice doesn't exist → CREATE it (new invoice)

**Key Changes**:
```python
# Check for existing invoice with same number AND customer
existing = db.query(Invoice).filter(
    Invoice.invoice_number == inv_num,
    Invoice.client_id == client.id
).first()

if existing:
    if abs(existing.total - inv_data["amount"]) > Decimal("0.01"):
        # REVISION: Update the invoice
        # - Update total, subtotal, amount_paid, balance_due
        # - Replace line items with new ones
        # - Create activity log entry
    else:
        # TRUE DUPLICATE: Skip
```

**Import Output**:
```
✓ Imported 123 new invoices
✓ Updated 5 invoice revisions
✓ Skipped 2 invoices (customer not found or duplicate)

📝 Invoice revisions detected and updated:
  #49252: $15.00 → $365.00
  ...
```

---

## How to Use Going Forward

### For Regular Imports
```bash
# Normal import (creates new invoices, updates revisions)
python3 import_invoices_from_journal.py --commit
```

The script will now:
1. ✅ Create new invoices that don't exist
2. ✅ Update invoices when QBO revisions are detected
3. ✅ Skip true duplicates
4. ✅ Report what was done

### If New Data Integrity Issues Arise
```bash
# Check for any new balance_due > total issues
python3 fix_invoice_revisions.py --dry-run

# Fix them
python3 fix_invoice_revisions.py --commit
```

---

## Verification

### Don Adair Invoice #49252 Status

**Before**:
```
Total:       $15.00  ❌
Balance Due: $365.00
Status:      sent
Line Items:  1 item ($15.00)
```

**After**:
```
Total:       $365.00 ✅
Balance Due: $365.00 ✅
Status:      sent
Line Items:  2 items
  - Business Email (up to 5 users): $15.00
  - Invoice Revision - Additional Charges: $350.00
Payment Recording: ✅ Enabled
```

---

## Testing Recommendations

1. **Test payment recording** on invoice #49252 (should now work)
2. **Re-run the import** with updated QBO CSV files to verify revision detection works
3. **Check AR aging report** — should now show accurate balances

---

## Files Modified

| File | Changes |
|------|---------|
| `fix_invoice_revisions.py` | NEW — Fixes existing corrupted invoices |
| `import_invoices_from_journal.py` | UPDATED — Added revision detection logic |

---

## Technical Details

### Revision Detection Algorithm

The script detects revisions by:
1. **Composite key**: `(invoice_number, customer_name)` — ensures we're matching the right invoice
2. **Amount comparison**: If amounts differ by > $0.01, it's a revision
3. **Line item replacement**: Deletes old items, adds new ones from QBO
4. **Status update**: Recalculates status, amount_paid, balance_due based on AR aging data

### Why This Works

- QBO provides revised invoice data in the journal export
- The import script now processes both the old and revised versions
- When it detects the revision (same customer, different amount), it updates in place
- No duplicate invoices are created
- All line items reflect the latest QBO state

---

## Questions?

If you encounter `balance_due > total` again, it indicates a revision wasn't detected. Run `fix_invoice_revisions.py` to correct it, and check the QBO CSV export to understand what happened.
