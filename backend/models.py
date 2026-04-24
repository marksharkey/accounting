from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Date,
    Numeric, ForeignKey, Enum, SmallInteger
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────

class BillingCycle(str, enum.Enum):
    monthly = "monthly"
    quarterly = "quarterly"
    semi_annual = "semi_annual"
    annual = "annual"
    multi_year = "multi_year"


class AccountStatus(str, enum.Enum):
    active = "active"
    overdue = "overdue"
    suspended = "suspended"
    deleted = "deleted"


class InvoiceStatus(str, enum.Enum):
    draft = "draft"
    ready = "ready"
    sent = "sent"
    partially_paid = "partially_paid"
    paid = "paid"
    voided = "voided"


class CreditMemoStatus(str, enum.Enum):
    draft = "draft"
    sent = "sent"
    applied = "applied"
    voided = "voided"


class PaymentMethod(str, enum.Enum):
    autocc = "autocc"
    check = "check"
    credit_card = "credit_card"
    cash = "cash"


class AccountType(str, enum.Enum):
    income = "income"
    expense = "expense"
    asset = "asset"
    liability = "liability"


class CollectionsEventType(str, enum.Enum):
    invoice_sent = "invoice_sent"
    reminder_sent = "reminder_sent"
    late_fee_applied = "late_fee_applied"
    suspension_warning_sent = "suspension_warning_sent"
    suspended = "suspended"
    deletion_warning_sent = "deletion_warning_sent"
    deleted = "deleted"
    payment_received = "payment_received"
    collections_paused = "collections_paused"
    collections_resumed = "collections_resumed"


class LateFeeType(str, enum.Enum):
    flat = "flat"
    percentage = "percentage"
    none = "none"


class EstimateStatus(str, enum.Enum):
    draft = "draft"
    sent = "sent"
    accepted = "accepted"
    declined = "declined"
    expired = "expired"
    converted = "converted"


class EmailTemplateType(str, enum.Enum):
    new_invoice = "new_invoice"
    reminder_invoice = "reminder_invoice"
    invoice_past_due = "invoice_past_due"
    suspension_invoice = "suspension_invoice"
    cancellation_invoice = "cancellation_invoice"
    paid_invoice = "paid_invoice"
    credit_memo_issued = "credit_memo_issued"
    payment_failed = "payment_failed"
    default = "default"


class TransactionType(str, enum.Enum):
    check = "check"
    deposit = "deposit"
    transfer = "transfer"
    payment = "payment"
    fee = "fee"
    interest = "interest"
    other = "other"


# ─────────────────────────────────────────────
# Users
# ─────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


# ─────────────────────────────────────────────
# Chart of Accounts
# ─────────────────────────────────────────────

class ChartOfAccount(Base):
    __tablename__ = "chart_of_accounts"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    account_type = Column(Enum(AccountType), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    service_catalog = relationship("ServiceCatalog", back_populates="income_account")
    expenses = relationship("Expense", back_populates="category")


# ─────────────────────────────────────────────
# Service Catalog
# ─────────────────────────────────────────────

class ServiceCatalog(Base):
    __tablename__ = "service_catalog"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    default_amount = Column(Numeric(10, 2), nullable=False)
    default_cycle = Column(Enum(BillingCycle), nullable=False, default=BillingCycle.monthly)
    category = Column(String(50), nullable=True)
    income_account_id = Column(Integer, ForeignKey("chart_of_accounts.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    income_account = relationship("ChartOfAccount", back_populates="service_catalog")


# ─────────────────────────────────────────────
# Clients
# ─────────────────────────────────────────────

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(150), nullable=False)
    display_name = Column(String(150), nullable=True)
    full_name = Column(String(150), nullable=True)
    email = Column(String(150), nullable=False)
    email_cc = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    address_line1 = Column(String(150), nullable=True)
    address_line2 = Column(String(150), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    zip_code = Column(String(20), nullable=True)

    autocc_recurring = Column(Boolean, nullable=False, default=False)
    autocc_customer_id = Column(String(50), nullable=True)
    account_status = Column(Enum(AccountStatus), nullable=False, default=AccountStatus.active)
    account_balance = Column(Numeric(10, 2), default=0.00)

    late_fee_type = Column(Enum(LateFeeType), default=LateFeeType.none)
    late_fee_amount = Column(Numeric(10, 2), default=0.00)
    late_fee_grace_days = Column(SmallInteger, default=0)
    collections_exempt = Column(Boolean, default=False)
    collections_paused = Column(Boolean, default=False)
    collections_pause_reason = Column(Text, nullable=True)

    auto_send_invoices = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    billing_schedules = relationship("BillingSchedule", back_populates="client", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="client")
    credit_memos = relationship("CreditMemo", back_populates="client")
    payments = relationship("Payment", back_populates="client")
    collections_events = relationship("CollectionsEvent", back_populates="client")
    activity_logs = relationship("ActivityLog", back_populates="client")
    domains = relationship("Domain", back_populates="client")


# ─────────────────────────────────────────────
# Billing Schedules
# ─────────────────────────────────────────────

class BillingSchedule(Base):
    __tablename__ = "billing_schedules"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)

    amount = Column(Numeric(10, 2), nullable=False, default=0.00)
    cycle = Column(Enum(BillingCycle), nullable=False)
    next_bill_date = Column(Date, nullable=False)
    autocc_recurring = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    client = relationship("Client", back_populates="billing_schedules")
    line_items = relationship("BillingScheduleLineItem", back_populates="billing_schedule", cascade="all, delete-orphan", order_by="BillingScheduleLineItem.sort_order")


class BillingScheduleLineItem(Base):
    __tablename__ = "billing_schedule_line_items"

    id = Column(Integer, primary_key=True, index=True)
    billing_schedule_id = Column(Integer, ForeignKey("billing_schedules.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("service_catalog.id"), nullable=True)
    domain_id = Column(Integer, ForeignKey("domains.id"), nullable=True)

    description = Column(String(255), nullable=False)
    quantity = Column(Numeric(10, 4), default=1.0000)
    unit_amount = Column(Numeric(10, 2), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    sort_order = Column(SmallInteger, default=0)

    billing_schedule = relationship("BillingSchedule", back_populates="line_items")
    service = relationship("ServiceCatalog")
    domain = relationship("Domain")


# ─────────────────────────────────────────────
# Invoices
# ─────────────────────────────────────────────

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(20), unique=True, nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)

    created_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    sent_date = Column(DateTime, nullable=True)

    status = Column(Enum(InvoiceStatus), nullable=False, default=InvoiceStatus.draft)
    autocc_verified = Column(Boolean, default=False)
    autocc_transaction_id = Column(String(50), nullable=True)

    subtotal = Column(Numeric(10, 2), nullable=False, default=0.00)
    late_fee_amount = Column(Numeric(10, 2), default=0.00)
    total = Column(Numeric(10, 2), nullable=False, default=0.00)
    amount_paid = Column(Numeric(10, 2), default=0.00)
    balance_due = Column(Numeric(10, 2), default=0.00)
    previous_balance = Column(Numeric(10, 2), default=0.00, nullable=False)

    notes = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)
    voided_reason = Column(Text, nullable=True)

    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    client = relationship("Client", back_populates="invoices")
    line_items = relationship("InvoiceLineItem", back_populates="invoice", cascade="all, delete-orphan", order_by="InvoiceLineItem.sort_order")
    payments = relationship("Payment", back_populates="invoice")
    credit_memos = relationship("CreditMemo", back_populates="applied_invoice")
    collections_events = relationship("CollectionsEvent", back_populates="invoice")
    created_by = relationship("User")


class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("service_catalog.id"), nullable=True)

    description = Column(String(255), nullable=False)
    quantity = Column(Numeric(10, 4), default=1.0000)
    unit_amount = Column(Numeric(10, 2), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    is_prorated = Column(Boolean, default=False)
    prorate_note = Column(String(255), nullable=True)
    sort_order = Column(SmallInteger, default=0)

    invoice = relationship("Invoice", back_populates="line_items")
    service = relationship("ServiceCatalog")


# ─────────────────────────────────────────────
# Estimates
# ─────────────────────────────────────────────

class Estimate(Base):
    __tablename__ = "estimates"

    id = Column(Integer, primary_key=True, index=True)
    estimate_number = Column(String(20), unique=True, nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)

    created_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=True)
    sent_date = Column(DateTime, nullable=True)

    status = Column(Enum(EstimateStatus), nullable=False, default=EstimateStatus.draft)
    converted_to_invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)

    total = Column(Numeric(10, 2), nullable=False, default=0.00)
    notes = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)

    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    client = relationship("Client")
    line_items = relationship("EstimateLineItem", back_populates="estimate", cascade="all, delete-orphan", order_by="EstimateLineItem.sort_order")
    converted_invoice = relationship("Invoice")
    created_by = relationship("User")


class EstimateLineItem(Base):
    __tablename__ = "estimate_line_items"

    id = Column(Integer, primary_key=True, index=True)
    estimate_id = Column(Integer, ForeignKey("estimates.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("service_catalog.id"), nullable=True)

    description = Column(String(255), nullable=False)
    quantity = Column(Numeric(10, 4), default=1.0000)
    unit_amount = Column(Numeric(10, 2), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    sort_order = Column(SmallInteger, default=0)

    estimate = relationship("Estimate", back_populates="line_items")
    service = relationship("ServiceCatalog")


# ─────────────────────────────────────────────
# Credit Memos
# ─────────────────────────────────────────────

class CreditMemo(Base):
    __tablename__ = "credit_memos"

    id = Column(Integer, primary_key=True, index=True)
    memo_number = Column(String(20), unique=True, nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    applied_to_invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)

    created_date = Column(Date, nullable=False)
    sent_date = Column(DateTime, nullable=True)
    status = Column(Enum(CreditMemoStatus), nullable=False, default=CreditMemoStatus.draft)

    total = Column(Numeric(10, 2), nullable=False)
    reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    client = relationship("Client", back_populates="credit_memos")
    applied_invoice = relationship("Invoice", back_populates="credit_memos")
    line_items = relationship("CreditLineItem", back_populates="credit_memo", cascade="all, delete-orphan", order_by="CreditLineItem.sort_order")
    created_by = relationship("User")


class CreditLineItem(Base):
    __tablename__ = "credit_line_items"

    id = Column(Integer, primary_key=True, index=True)
    credit_memo_id = Column(Integer, ForeignKey("credit_memos.id"), nullable=False)

    description = Column(String(255), nullable=False)
    quantity = Column(Numeric(10, 4), default=1.0000)
    unit_amount = Column(Numeric(10, 2), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    sort_order = Column(SmallInteger, default=0)

    credit_memo = relationship("CreditMemo", back_populates="line_items")


# ─────────────────────────────────────────────
# Payments
# ─────────────────────────────────────────────

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)

    payment_date = Column(Date, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    method = Column(Enum(PaymentMethod), nullable=False)
    reference_number = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    recorded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reconciled = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    invoice = relationship("Invoice", back_populates="payments")
    client = relationship("Client", back_populates="payments")
    recorded_by = relationship("User")


# ─────────────────────────────────────────────
# Expenses
# ─────────────────────────────────────────────

class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    expense_date = Column(Date, nullable=False)
    vendor = Column(String(150), nullable=False)
    description = Column(String(255), nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    category_id = Column(Integer, ForeignKey("chart_of_accounts.id"), nullable=True)
    reference_number = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    receipt_filename = Column(String(255), nullable=True)

    recorded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reconciled = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    category = relationship("ChartOfAccount", back_populates="expenses")
    recorded_by = relationship("User")


# ─────────────────────────────────────────────
# Collections Events
# ─────────────────────────────────────────────

class Registrar(str, enum.Enum):
    cloudflare = "cloudflare"
    godaddy = "godaddy"
    hosting_com = "hosting_com"
    other = "other"


# ─────────────────────────────────────────────
# Domains
# ─────────────────────────────────────────────

class Domain(Base):
    __tablename__ = "domains"

    id = Column(Integer, primary_key=True, index=True)
    domain_name = Column(String(255), nullable=False, unique=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    registrar = Column(Enum(Registrar), nullable=False, default=Registrar.cloudflare)
    expiration_date = Column(Date, nullable=False)
    renewal_cost = Column(Numeric(10, 2), nullable=False, default=25.00)
    auto_renew = Column(Boolean, default=False)
    cloudflare_id = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    client = relationship("Client", back_populates="domains")


class CollectionsEvent(Base):
    __tablename__ = "collections_events"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)

    event_type = Column(Enum(CollectionsEventType), nullable=False)
    event_date = Column(DateTime, server_default=func.now())
    performed_by = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    overridden = Column(Boolean, default=False)
    override_reason = Column(Text, nullable=True)

    client = relationship("Client", back_populates="collections_events")
    invoice = relationship("Invoice", back_populates="collections_events")


# ─────────────────────────────────────────────
# Activity Log
# ─────────────────────────────────────────────

class ActivityLog(Base):
    __tablename__ = "activity_log"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)

    action = Column(String(100), nullable=False)
    performed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    performed_by_name = Column(String(100), nullable=True)
    timestamp = Column(DateTime, server_default=func.now())
    notes = Column(Text, nullable=True)
    previous_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)

    client = relationship("Client", back_populates="activity_logs")
    performed_by = relationship("User")


# ─────────────────────────────────────────────
# Invoice Sequences
# ─────────────────────────────────────────────

class InvoiceSequence(Base):
    __tablename__ = "invoice_sequences"

    id = Column(Integer, primary_key=True)
    prefix = Column(String(20), unique=True, nullable=False)
    last_number = Column(Integer, nullable=False, default=0)
    year = Column(SmallInteger, nullable=False)


# ─────────────────────────────────────────────
# Company Info (Settings)
# ─────────────────────────────────────────────

class CompanyInfo(Base):
    __tablename__ = "company_info"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(150), nullable=False)
    address_line1 = Column(String(150), nullable=True)
    address_line2 = Column(String(150), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    zip_code = Column(String(20), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(150), nullable=True)
    website_url = Column(String(255), nullable=True)
    logo_filename = Column(String(255), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ─────────────────────────────────────────────
# Email Templates
# ─────────────────────────────────────────────

class EmailTemplate(Base):
    __tablename__ = "email_templates"

    id = Column(Integer, primary_key=True, index=True)
    template_type = Column(Enum(EmailTemplateType), nullable=False, unique=True)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ─────────────────────────────────────────────
# Phase 2 — Bank Reconciliation
# ─────────────────────────────────────────────

class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id = Column(Integer, primary_key=True, index=True)
    account_name = Column(String(100), nullable=False)
    account_number = Column(String(20), nullable=True)
    account_type = Column(String(50), nullable=False)
    opening_balance = Column(Numeric(12, 2), default=0, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    transactions = relationship("BankTransaction", back_populates="bank_account")
    reconciliations = relationship("BankReconciliation", back_populates="bank_account")


class BankTransaction(Base):
    __tablename__ = "bank_transactions"

    id = Column(Integer, primary_key=True, index=True)
    bank_account_id = Column(Integer, ForeignKey("bank_accounts.id"), nullable=False)
    transaction_date = Column(Date, nullable=False)
    transaction_type = Column(Enum(TransactionType), default=TransactionType.other, nullable=False)
    transaction_number = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    gl_account = Column(String(100), nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    balance = Column(Numeric(12, 2), nullable=True)
    matched_payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    reconciled = Column(Boolean, default=False)
    imported_date = Column(DateTime, server_default=func.now())
    import_batch = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    bank_account = relationship("BankAccount", back_populates="transactions")
    matched_payment = relationship("Payment")


class BankReconciliation(Base):
    __tablename__ = "bank_reconciliations"

    id = Column(Integer, primary_key=True, index=True)
    bank_account_id = Column(Integer, ForeignKey("bank_accounts.id"), nullable=False)
    reconciliation_date = Column(Date, nullable=False)
    statement_balance = Column(Numeric(12, 2), nullable=False)
    cleared_amount = Column(Numeric(12, 2), default=0, nullable=False)
    difference = Column(Numeric(12, 2), default=0, nullable=False)
    is_complete = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    bank_account = relationship("BankAccount", back_populates="reconciliations")


class JournalEntry(Base):
    """GL journal entry for accrual-basis P&L reporting"""
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    transaction_date = Column(Date, nullable=False, index=True)
    gl_account_code = Column(String(10), nullable=False, index=True)
    gl_account_name = Column(String(255), nullable=False)
    debit = Column(Numeric(12, 2), default=0, nullable=False)
    credit = Column(Numeric(12, 2), default=0, nullable=False)
    description = Column(Text, nullable=True)
    reference_number = Column(String(50), nullable=True)
    source = Column(String(50), default="qbo_journal", nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
