from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from datetime import date, datetime
from decimal import Decimal

import models
from database import get_db
from auth import get_current_user

router = APIRouter()


class JournalEntryIn(BaseModel):
    transaction_date: date
    gl_account_code: str
    gl_account_name: str
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    description: Optional[str] = None
    reference_number: Optional[str] = None
    source: str = "manual"


class JournalEntryOut(BaseModel):
    id: int
    transaction_date: date
    gl_account_code: str
    gl_account_name: str
    debit: Decimal
    credit: Decimal
    description: Optional[str] = None
    reference_number: Optional[str] = None
    source: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("/")
def list_journal_entries(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    account_code: Optional[str] = None,
    source: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.JournalEntry)
    if from_date:
        query = query.filter(models.JournalEntry.transaction_date >= from_date)
    if to_date:
        query = query.filter(models.JournalEntry.transaction_date <= to_date)
    if account_code:
        query = query.filter(models.JournalEntry.gl_account_code.ilike(f"%{account_code}%"))
    if source:
        query = query.filter(models.JournalEntry.source == source)
    total = query.count()
    entries = query.order_by(models.JournalEntry.transaction_date.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": [JournalEntryOut.from_orm(e) for e in entries]}


@router.post("/", status_code=201)
def create_journal_entry(
    data: JournalEntryIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    entry = models.JournalEntry(**data.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return JournalEntryOut.from_orm(entry)


@router.put("/{entry_id}")
def update_journal_entry(
    entry_id: int,
    data: JournalEntryIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    from fastapi import HTTPException
    entry = db.query(models.JournalEntry).filter_by(id=entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    for key, value in data.model_dump().items():
        setattr(entry, key, value)
    db.commit()
    db.refresh(entry)
    return JournalEntryOut.from_orm(entry)


@router.delete("/{entry_id}")
def delete_journal_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    from fastapi import HTTPException
    entry = db.query(models.JournalEntry).filter_by(id=entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    db.delete(entry)
    db.commit()
    return {"message": "Journal entry deleted"}
