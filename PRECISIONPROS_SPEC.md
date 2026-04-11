# PrecisionPros Billing System — Full Project Specification

## Business Context
- Sole proprietor web hosting / IT services business
- Two operators: Mark and Candace Sharkey
- ~200+ active clients
- Replacing QuickBooks Online
- No employees, no sales tax, no inventory

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11 / FastAPI |
| Database | MySQL 8+ (utf8mb4) |
| ORM | SQLAlchemy 2.0 + Alembic |
| Frontend | React + Vite |
| UI Components | Shadcn/ui + Tailwind CSS |
| API Client | Axios + TanStack Query |
| Routing | React Router v6 |
| PDF Generation | WeasyPrint |
| Email | aiosmtplib (SMTP) |
| Auth | JWT (python-jose + passlib) |

---

## Project Structure

```
~/accounting/
├── backend/
│   ├── main.py              # FastAPI app, CORS, auth routes, router registration
│   ├── config.py            # Pydantic settings from .env
│   ├── database.py          # SQLAlchemy engine + session + get_db
│   ├── models.py            # All SQLAlchemy models
│   ├── auth.py              # JWT create/verify, get_current_user dependency
│   ├── routers/
│   │   ├── clients.py       # Client CRUD, billing schedules, activity log
│   │   ├── invoices.py      # Invoice generation, prefill, A.net verify, void
│   │   ├── payments.py      # Payment recording, running balance update
│   │   ├── expenses.py      # Expense CRUD
│   │   ├── reports.py       # AR Aging, Revenue by Period, P&L, MRR/ARR
│   │   ├── collections.py   # Daily queue, late fees, account status
│   │   └── services.py      # Service catalog + chart of accounts CRUD
│   ├── services/
│   │   └── billing.py       # Prorate calc, invoice/memo/estimate numbering, cycle advance
│   ├── migrations/          # Alembic
│   ├── .env                 # Local config (not in git)
│   └── requirements.txt
│
└── frontend/                # React + Vite (Phase 1B — to be built)
```

---

## Database — 17 Tables

```
users                   — mark + candace, bcrypt passwords, JWT auth
chart_of_accounts       — income/expense categories (code, name, type)
service_catalog         — standard billable items with default amounts/cycles
clients                 — 200+ clients, billing type, collections settings, running balance
billing_schedules       — standing recurring charges per client (drives billing calendar)
invoices                — sequential PP-YYYY-NNNN numbering
invoice_line_items      — line items, supports prorated entries
estimates               — PP-EST-YYYY-NNNN, convertible to invoice
estimate_line_items
credit_memos            — PP-CM-YYYY-NNNN, negative invoices
credit_line_items
payments                — authnet/check/credit_card/cash, reconciled flag for Phase 2
expenses                — vendor expenses linked to chart of accounts
collections_events      — timeline of all collections actions per client/invoice
activity_log            — full audit trail across all entities
invoice_sequences       — gap-free sequential numbering per prefix per year
bank_transactions       — Phase 2 bank reconciliation (table exists, feature deferred)
```

---

## Key Business Rules

### Billing Types (per client)
- **authnet_recurring** — A.net charges automatically; operator verifies manually in A.net, marks verified in app, then sends paid-in-full invoice as receipt
- **fixed_recurring** — predictable charge, invoice sent on the 20th, due the 1st
- **mixed** — fixed charges + one-off items on same invoice
- **one_off** — ad hoc only

### Billing Cycles
monthly / quarterly / semi_annual / annual / multi_year

### Invoice Numbering
- Invoices: `PP-2026-0001`
- Credit Memos: `PP-CM-2026-0001`
- Estimates: `PP-EST-2026-0001`
- Sequential, never reused, resets each year

### Collections Timeline (non-A.net clients)
```
20th of month  → Invoice sent (due the 1st of next month)
10th           → Late fee applied + warning email sent
20th           → Suspension warning sent (operator suspends manually on web server)
Last day       → Deletion warning sent (operator deletes manually on web server)
```
- Account suspension/deletion are MANUAL — app just tracks status and sends emails
- Per-client late fee: flat dollar or percentage, grace days configurable
- Collections can be paused per client with a reason

### Payment Methods
authnet / check / credit_card / cash

### Running Account Balance
- Stored on `clients.account_balance`
- Decremented when payment recorded
- Negative = credit on account
- Invoice status calculated from payments: draft → sent → partially_paid → paid

### Prorating
```
prorated = (monthly_rate / days_in_month) × days_remaining
```
Generates a line item like: "Website Hosting — prorated 16 days (Apr 15–Apr 30) @ $25.00/mo — $13.33"

### Email Modes
- Auto-send: invoices go out immediately when status set to "ready"
- Batch approval: invoices queue up, operator reviews list and sends all at once
- Per-client preference stored as `auto_send_invoices` boolean

---

## API — All Endpoints (backend running on port 8010)

### Auth
```
POST /api/auth/token          — login, returns JWT (form data: username, password)
GET  /api/auth/me             — current user info
```
All other endpoints require: `Authorization: Bearer <token>`

### Clients
```
GET    /api/clients/                        — list, supports search/filter/pagination
POST   /api/clients/                        — create
GET    /api/clients/{id}                    — get one
PUT    /api/clients/{id}                    — update
DELETE /api/clients/{id}                    — soft delete (sets is_active=False)
GET    /api/clients/{id}/billing-schedules  — list active schedules
POST   /api/clients/{id}/billing-schedules  — add schedule
GET    /api/clients/{id}/invoices           — invoice history
GET    /api/clients/{id}/activity           — audit log
```

### Service Catalog
```
GET  /api/services/           — list services
POST /api/services/           — create service
PUT  /api/services/{id}       — update service
GET  /api/services/categories — distinct categories
GET  /api/services/accounts   — chart of accounts
POST /api/services/accounts   — create account
PUT  /api/services/accounts/{id} — update account
```

### Invoices
```
GET  /api/invoices/                     — list, filter by client/status/date
GET  /api/invoices/due-for-billing      — clients with schedules due (days_ahead param)
POST /api/invoices/prefill/{client_id}  — pre-populate from billing schedules
POST /api/invoices/                     — create invoice with line items
GET  /api/invoices/{id}                 — get one
PUT  /api/invoices/{id}/status          — update status
POST /api/invoices/{id}/verify-authnet  — mark A.net charge verified
POST /api/invoices/{id}/void            — void (requires reason)
```

### Payments
```
GET  /api/payments/   — list payments
POST /api/payments/   — record payment (updates invoice status + client balance)
```

### Expenses
```
GET    /api/expenses/     — list expenses
POST   /api/expenses/     — create
PUT    /api/expenses/{id} — update
DELETE /api/expenses/{id} — delete
```

### Reports
```
GET /api/reports/ar-aging               — AR aging buckets (current/1-30/31-60/61-90/90+)
GET /api/reports/revenue-by-period      — monthly totals for a year
GET /api/reports/client-revenue-summary — annual billing per client
GET /api/reports/profit-loss            — income vs expenses by category
GET /api/reports/recurring-revenue      — MRR/ARR from active billing schedules
```

### Collections
```
GET  /api/collections/daily-queue                    — today's action items
POST /api/collections/apply-late-fee/{invoice_id}    — apply late fee
POST /api/collections/update-account-status/{client_id} — update client status
```

---

## Phase Build Order

### Phase 1A ✅ COMPLETE
- Backend foundation, all models, all routers, JWT auth
- MySQL database with all 17 tables created
- Users: mark / candace (dev passwords = usernames)
- Git repo initialized at ~/accounting/

### Phase 1B — React Frontend (NEXT)
Pages to build:
1. **Login** — JWT auth, store token, redirect to dashboard
2. **Dashboard** — daily action queue, overdue count, MRR/ARR snapshot, due-for-billing list
3. **Clients** — searchable list, status badges, account balance column
4. **Client Detail** — profile, billing schedules, invoice history, account balance, activity log
5. **Invoice Builder** — prefill from schedules, add one-off items from service catalog, A.net verify checkbox, save draft / mark ready
6. **Invoice List** — filterable by status/client/date, bulk send queue
7. **Service Catalog** — manage standard items and chart of accounts
8. **Expenses** — simple log
9. **Reports** — AR Aging, Revenue, P&L, MRR

### Phase 1C — Communications
- Email templates (invoice, receipt, reminder, late fee, suspension warning, deletion warning)
- SMTP sending via aiosmtplib
- Batch email approval queue

### Phase 1D — PDF + Reporting UI
- WeasyPrint invoice/credit memo PDF generation
- Downloadable reports

### Phase 2 — Bank Reconciliation
- CSV bank statement import
- Auto-match deposits to payments
- Reconciliation workflow

---

## Frontend Notes for Claude Code

- Vite dev server runs on port 5173
- All API calls go to `http://localhost:8010`
- JWT token stored in localStorage as `pp_token`
- Auth header: `Authorization: Bearer <token>`
- Login uses `application/x-www-form-urlencoded` (OAuth2 form), not JSON
- React Query for all server state
- React Router v6 for navigation
- Shadcn/ui + Tailwind for UI
- No client-facing portal — this is an internal tool only
- Two users only — no role-based permissions needed

---

## Git Commits Done
- `066201d` — Initial commit — add .gitignore
- `a97a9b7` — Phase 1A: Add backend foundation — config, database, auth, requirements
- `f482bf7` — Phase 1A: Add models (full schema) and billing service
- (pending) — Phase 1A: Complete — all routers, main.py, pin bcrypt==4.0.1

Phase 1A ✅ COMPLETE - Backend, all 17 tables, JWT auth
Phase 1B ✅ COMPLETE - Full React frontend, all pages working
Phase 1C ✅ COMPLETE - Email templates, SMTP via Gmail, all triggers working
Phase 1D - NEXT - PDF generation (WeasyPrint), downloadable invoices
Phase 2  - Bank reconciliation
