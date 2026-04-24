# PrecisionPros UI Redesign — Claude Code Prompt

## Context

This is a React + Vite + Tailwind CSS accounting application for a small IT/web hosting business. 
The backend is FastAPI on port 8010, the frontend dev server runs on port 5173.

The UI was built with a consumer/marketing-website aesthetic — large fonts, heavy padding, and 
chunky card boxes. The goal is to redesign it to feel like professional accounting software 
(think QuickBooks Desktop, Xero, or FreshBooks): dense, data-forward, subdued headers, no 
unnecessary scrolling.

The **logic, routing, API calls, and component structure are all correct and should not change.** 
This is purely a visual/density redesign.

---

## The Problems (diagnosed from code review)

### 1. Base font is 18px — should be 13px
In `frontend/src/index.css`, the root font is set to `18px/145%`. For a data application 
displaying tables of 200 clients and 4,000 invoices, this is far too large. Target: **13px**.

### 2. Table rows are ~50px tall — should be ~28–30px
In `frontend/src/components/ui/Table.jsx`:
- `TableHead` has `h-12` (48px) — should be removed or replaced with `h-8`
- `TableCell` has `px-4 py-3` — should be `px-3 py-1`
- `TableHeader` background `bg-gray-50` is fine, keep it

### 3. Card padding is excessive
In `frontend/src/components/ui/Card.jsx`:
- `CardHeader` uses `p-6` — should be `px-4 py-3`
- `CardContent` uses `p-6 pt-0` — should be `px-4 pb-3 pt-0`
- `CardTitle` uses `text-2xl font-semibold` — should be `text-sm font-semibold uppercase tracking-wide text-gray-500`

### 4. Input height is too tall
In `frontend/src/components/ui/Input.jsx`:
- `h-10` (40px) — should be `h-7`
- `text-base` — should be `text-sm`
- `px-3 py-2` — should be `px-2 py-1`

### 5. Button sizes are too large
In `frontend/src/components/ui/Button.jsx`:
- `default` size: `px-4 py-2 text-sm` — should be `px-3 py-1 text-xs`
- `sm` size: `px-3 py-1 text-xs` — should be `px-2 py-0.5 text-xs`
- `lg` size: `px-6 py-3 text-base` — should be `px-4 py-1.5 text-sm`
- Remove `rounded-md`, use `rounded` (smaller radius looks more professional/compact)

### 6. Layout padding is excessive
In `frontend/src/components/Layout.jsx`:
- `px-4 py-6` on the inner div — should be `px-4 py-3`
- Page title `text-2xl font-bold` — should be `text-sm font-medium text-gray-500 uppercase tracking-wider`
- `mb-6` below title — should be `mb-3`

### 7. The `#root` constraint in index.css conflicts with sidebar layout
In `frontend/src/index.css`, the `#root` block has `width: 1126px`, `text-align: center`, 
and `border-inline`. These are leftover from the Vite starter template and break the full-width 
sidebar app layout. Remove all styles from the `#root` rule (keep it but make it empty, or just 
delete the rule). The app's own Layout component handles the full-screen layout correctly.

Also in `index.css`: remove the `h1` rule (56px font — not used in the app) and reduce `h2` to 
`font-size: 16px`. Remove the `font: 18px/145%` from `:root` and replace with `font-size: 13px; 
line-height: 1.4;`.

---

## Dashboard Redesign (most important page change)

The current dashboard (`frontend/src/pages/DashboardPage.jsx`) uses a "HorizontalScrollBar" 
pattern — five stacked cards, each with a summary on the left and horizontally-scrolling chips 
on the right. This is the biggest UX problem: it shows very little data and requires horizontal 
scrolling within each card.

**Replace the dashboard layout with this pattern:**

### Top row: KPI summary bar (single row, no cards)
A simple borderless row of 4–5 stat blocks, separated by vertical dividers. No card wrapper. Example layout:

```
MRR: $12,655   |   ARR: $151,866   |   Open Invoices: 12  ($4,200)   |   Past Due: 3  ($890)   |   Due for Billing: 7
```

Each stat is: a small gray label above, a larger dark number below. Clicking "Past Due" or 
"Open Invoices" navigates to `/invoices?status=overdue` etc.

### Below that: a proper action table
Replace the chip-scroll rows with a single flat table titled "Action Items" that lists all 
invoices from all queue buckets (invoiced_and_due, past_due, suspension_candidates, 
termination_candidates) in one place. Columns:

| Client | Invoice # | Amount | Days Overdue | Category | Action |
|--------|-----------|--------|-------------|----------|--------|

- "Category" column shows a small color-coded badge: Due Today / Past Due / Suspension / Termination
- "Action" column: a small "View" link navigating to the invoice
- Sort by days_overdue descending by default
- Empty state: a single centered line "No action items today"

### Below that: "Due for Billing" section
A simple table (not chips) listing clients due for billing in the next 7 days. Columns:

| Client | Billing Type | Amount | Next Bill Date | Action |
|--------|-------------|--------|----------------|--------|

Keep the existing API calls — just change how the data is rendered. The data shape from the 
API stays the same.

---

## Clients List Page

`frontend/src/pages/ClientsListPage.jsx` — the table currently only shows 5 columns. 
The API returns more useful data. Add these columns to the table:

**New columns:** Email, City, Billing Type  
**Keep:** Name (linked), Balance, Status  
**Remove:** The redundant "Actions" / "View" button column — the name link is sufficient

Also: move the filter controls to a single compact row (search input + status dropdown + 
"Add Client" button all on one line, no stacked rows).

---

## Invoice List Page

`frontend/src/pages/InvoiceListPage.jsx` — the filter area is two rows tall and takes 
significant vertical space. Compress filters to a single row:

`[Invoice #] [Status ▾] [Client ▾] [From] [To] [Reset] [+ New Invoice]`

All on one line. Labels can be removed — placeholders inside the inputs are enough.

The table itself is good — just let the density improvements from the shared components 
do the work.

---

## Global Color & Style Direction

- Background: keep `#f9fafb` (gray-50) for the app shell, white for table/card surfaces
- Text: primary data in `#111827` (gray-900), secondary/labels in `#6b7280` (gray-500)
- Accent/links: keep blue (`#2563eb`) but use it sparingly — only for clickable values
- Borders: `#e5e7eb` (gray-200), subtle — not heavy
- Status badges: keep the color coding (green=paid, red=overdue, yellow=partial, blue=sent, gray=draft) but make them smaller — `text-xs px-1.5 py-0.5 rounded` instead of the current larger rounded-full style
- No shadows on tables — flat borders only
- Sidebar: no changes needed

---

## Execution Order

Work in this order so each step builds on the last and you can verify density improvements 
progressively:

1. `frontend/src/index.css` — fix root font, remove `#root` constraints, clean up h1/h2
2. `frontend/src/components/ui/Table.jsx` — reduce row height and padding
3. `frontend/src/components/ui/Card.jsx` — reduce card padding and title size
4. `frontend/src/components/ui/Input.jsx` — reduce input height
5. `frontend/src/components/ui/Button.jsx` — reduce button padding and radius
6. `frontend/src/components/Layout.jsx` — reduce outer padding, subdue page titles
7. `frontend/src/pages/DashboardPage.jsx` — full redesign (KPI bar + action table)
8. `frontend/src/pages/ClientsListPage.jsx` — add columns, compress filters
9. `frontend/src/pages/InvoiceListPage.jsx` — compress filters to one row

After each file, run the dev server and visually verify the change before moving to the next.

---

## What NOT to Change

- All API calls, query keys, data fetching logic — leave untouched
- React Router routes and navigation — leave untouched  
- Auth/JWT logic — leave untouched
- Sidebar structure and navigation items — leave untouched
- Modal components (AddClientModal, RecordPaymentModal, SendInvoiceModal, etc.) — 
  apply the density improvements from shared components, but don't restructure them
- Backend — do not touch anything in `backend/`
- All other pages (InvoiceDetailPage, ClientDetailPage, ExpensesPage, ReportsPage, etc.) 
  will benefit automatically from the shared component changes; only touch them if 
  something looks obviously broken after the shared component updates

---

## Success Criteria

When done, the app should:
- Show at least 20 client rows without scrolling on a standard 1080p monitor
- Have no horizontal scrolling on the main list pages at 1280px viewport width
- Dashboard should show all action items at a glance without any horizontal scroll
- Page headers should be visually quiet — they label the page, they don't dominate it
- All interactive elements (buttons, inputs, dropdowns) should feel compact but still 
  comfortably clickable
