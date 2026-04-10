from sqlalchemy.orm import Session
from datetime import date
import models
from config import get_settings

settings = get_settings()


def next_invoice_number(db: Session) -> str:
    year = date.today().year
    prefix = settings.invoice_prefix
    seq = db.query(models.InvoiceSequence).filter_by(prefix=prefix).with_for_update().first()
    if not seq or seq.year != year:
        if seq:
            seq.year = year
            seq.last_number = 1
        else:
            seq = models.InvoiceSequence(prefix=prefix, year=year, last_number=1)
            db.add(seq)
    else:
        seq.last_number += 1
    db.flush()
    return f"{prefix}-{year}-{seq.last_number:04d}"


def next_credit_memo_number(db: Session) -> str:
    year = date.today().year
    prefix = settings.credit_memo_prefix
    seq = db.query(models.InvoiceSequence).filter_by(prefix=prefix).with_for_update().first()
    if not seq or seq.year != year:
        if seq:
            seq.year = year
            seq.last_number = 1
        else:
            seq = models.InvoiceSequence(prefix=prefix, year=year, last_number=1)
            db.add(seq)
    else:
        seq.last_number += 1
    db.flush()
    return f"{prefix}-{year}-{seq.last_number:04d}"


def next_estimate_number(db: Session) -> str:
    year = date.today().year
    prefix = f"{settings.invoice_prefix}-EST"
    seq = db.query(models.InvoiceSequence).filter_by(prefix=prefix).with_for_update().first()
    if not seq or seq.year != year:
        if seq:
            seq.year = year
            seq.last_number = 1
        else:
            seq = models.InvoiceSequence(prefix=prefix, year=year, last_number=1)
            db.add(seq)
    else:
        seq.last_number += 1
    db.flush()
    return f"{prefix}-{year}-{seq.last_number:04d}"


def calculate_prorate(
    monthly_amount: float,
    start_date: date,
    cycle_end_date: date
) -> tuple[float, str]:
    from calendar import monthrange
    days_in_month = monthrange(start_date.year, start_date.month)[1]
    days_remaining = (cycle_end_date - start_date).days + 1
    daily_rate = float(monthly_amount) / days_in_month
    prorated = round(daily_rate * days_remaining, 2)
    note = (
        f"Prorated {days_remaining} days "
        f"({start_date.strftime('%b %d')}–{cycle_end_date.strftime('%b %d')}) "
        f"@ ${monthly_amount:.2f}/mo"
    )
    return prorated, note


def advance_billing_date(current_date: date, cycle: models.BillingCycle) -> date:
    from dateutil.relativedelta import relativedelta
    cycle_deltas = {
        models.BillingCycle.monthly: relativedelta(months=1),
        models.BillingCycle.quarterly: relativedelta(months=3),
        models.BillingCycle.semi_annual: relativedelta(months=6),
        models.BillingCycle.annual: relativedelta(years=1),
        models.BillingCycle.multi_year: relativedelta(years=2),
    }
    return current_date + cycle_deltas.get(cycle, relativedelta(months=1))
