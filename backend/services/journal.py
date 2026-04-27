"""Journal entry service for automatic double-entry bookkeeping."""

from sqlalchemy.orm import Session
from datetime import date
from decimal import Decimal
import models


def post_journal_entries(
    db: Session,
    entries: list[dict],
    commit: bool = False
) -> None:
    """
    Create journal entries. Caller handles commit unless commit=True.

    Args:
        db: Database session
        entries: List of dicts with keys:
            - date: transaction date
            - code: GL account code (e.g., "1200")
            - name: GL account name
            - debit: debit amount (Decimal or float)
            - credit: credit amount (Decimal or float)
            - description: optional description
            - reference: optional reference number (invoice/payment id)
            - source: source type (e.g., "invoice", "payment", "late_fee")
        commit: If True, commit after adding (default: False, caller commits)
    """
    for entry in entries:
        je = models.JournalEntry(
            transaction_date=entry['date'],
            gl_account_code=entry['code'],
            gl_account_name=entry['name'],
            debit=Decimal(str(entry.get('debit', 0))),
            credit=Decimal(str(entry.get('credit', 0))),
            description=entry.get('description'),
            reference_number=entry.get('reference'),
            source=entry.get('source', 'manual')
        )
        db.add(je)

    if commit:
        db.commit()


def reverse_journal_entries(
    db: Session,
    reference_number: str,
    source: str,
    commit: bool = False
) -> None:
    """
    Reverse (negate) all journal entries with given reference and source.
    Creates new entries with debit/credit swapped.

    Args:
        db: Database session
        reference_number: Reference to match (e.g., invoice number)
        source: Source type to match
        commit: If True, commit after adding (default: False, caller commits)
    """
    # Find entries to reverse
    entries = db.query(models.JournalEntry).filter(
        models.JournalEntry.reference_number == reference_number,
        models.JournalEntry.source == source
    ).all()

    for entry in entries:
        # Create reversal entry (swap debit and credit)
        je = models.JournalEntry(
            transaction_date=entry.transaction_date,
            gl_account_code=entry.gl_account_code,
            gl_account_name=entry.gl_account_name,
            debit=entry.credit,
            credit=entry.debit,
            description=f"Reversal: {entry.description}" if entry.description else None,
            reference_number=entry.reference_number,
            source=entry.source
        )
        db.add(je)

    if commit:
        db.commit()
