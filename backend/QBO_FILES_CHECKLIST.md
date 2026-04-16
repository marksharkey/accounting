# QBO Files Needed for Re-Import

**Checklist for exporting the 5 required CSV files from QuickBooks Online**

Export these files and place them in: `~/accounting/backend/`

---

## 📋 Export Checklist

- [ ] **Customers.csv** *(converted from .xls)*
- [ ] **ProductServiceList__*.csv** *(includes timestamp)*
- [ ] **PrecisionPros_Network_Sales_by_Product_Service_Detail.csv**
- [ ] **PrecisionPros_Network_A_R_Aging_Detail_Report.csv**
- [ ] **PrecisionPros_Network_Transaction_Detail_by_Account.csv**

---

## 📥 Quick Export Reference

### 1️⃣ Customers
```
QBO Path:     Sales → Customers → Export
Format:       Excel (.xls)
Convert to:   CSV using: libreoffice --headless --convert-to csv Customers.xls
Save as:      Customers.csv
Expected:     ~200 rows (customers)
```

### 2️⃣ Products & Services
```
QBO Path:     Settings → Products & Services → Export
Format:       CSV
Save as:      ProductServiceList__*.csv
Expected:     ~40 rows (services)
Note:         Filename auto-includes timestamp from QBO
```

### 3️⃣ Sales by Product/Service Detail
```
QBO Path:     Reports → Sales by Product/Service Detail
Date Range:   From Jan 1, 2023 To Today
Format:       CSV
Save as:      PrecisionPros_Network_Sales_by_Product_Service_Detail.csv
Expected:     ~10,500 rows (line items from 4,000+ invoices)
```

### 4️⃣ A/R Aging Detail
```
QBO Path:     Reports → A/R Aging Detail
As Of Date:   Today (current date)
Format:       CSV
Save as:      PrecisionPros_Network_A_R_Aging_Detail_Report.csv
Expected:     ~200-300 rows (open invoices)
```

### 5️⃣ Transaction Detail by Account
```
QBO Path:     Reports → Transaction Detail by Account
Date Range:   From Jan 1, 2023 To Today
Basis:        ⚠️ MUST be Cash basis (not Accrual)
Format:       CSV
Save as:      PrecisionPros_Network_Transaction_Detail_by_Account.csv
Expected:     ~880 rows (expense transactions)
```

---

## ✅ After Exporting

Place all files in:
```bash
~/accounting/backend/
```

Verify all files are present:
```bash
cd ~/accounting/backend
ls -la *.csv | grep -E "(Customers|ProductService|Sales_by_Product|A_R_Aging|Transaction_Detail)"
```

You should see 5 files. If any are missing, go back to QBO and re-export.

---

## 🚀 Then Run Import

```bash
cd ~/accounting/backend

# Preview (no changes)
python3 run_full_import.py --dry-run

# Execute
python3 run_full_import.py --commit
```

---

## 📖 For Detailed Instructions

See: `QBO_EXPORT_GUIDE.md`

---

*Export checklist created April 14, 2026*
