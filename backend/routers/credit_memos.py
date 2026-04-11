from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import date, datetime
from decimal import Decimal

import models
from database import get_db
from auth import get_current_user
from services.billing import next_credit_memo_number

router = APIRouter()


class LineItemIn(BaseModel):
    description: str
    quantity: float = 1.0
    unit_amount: float
    sort_order: int = 0


class LineItemOut(BaseModel):
    id: int
    description: str
    quantity: float
    unit_amount: float
    amount: float

    class Config:
        from_attributes = True


class ClientOut(BaseModel):
    id: int
    company_name: str
    contact_name: Optional[str]
    email: str
    phone: Optional[str]

    class Config:
        from_attributes = True


class CreditMemoOut(BaseModel):
    id: int
    memo_number: str
    client_id: int
    client: Optional[ClientOut]
    created_date: date
    sent_date: Optional[datetime] = None
    status: models.CreditMemoStatus
    total: float
    reason: Optional[str]
    notes: Optional[str]
    line_items: List[LineItemOut]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CreditMemoCreate(BaseModel):
    client_id: int
    created_date: date
    line_items: List[LineItemIn]
    reason: Optional[str] = None
    notes: Optional[str] = None
    status: models.CreditMemoStatus = models.CreditMemoStatus.draft


@router.get("/")
def list_credit_memos(
    client_id: Optional[int] = None,
    status: Optional[models.CreditMemoStatus] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.CreditMemo)
    if client_id:
        query = query.filter_by(client_id=client_id)
    if status:
        query = query.filter_by(status=status)
    if from_date:
        query = query.filter(models.CreditMemo.created_date >= from_date)
    if to_date:
        query = query.filter(models.CreditMemo.created_date <= to_date)
    total = query.count()
    memos = query.order_by(models.CreditMemo.created_date.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": memos}


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_credit_memo(
    data: CreditMemoCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    client = db.query(models.Client).filter_by(id=data.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    memo_number = next_credit_memo_number(db)

    # Calculate total
    total = sum(item.quantity * item.unit_amount for item in data.line_items)

    memo = models.CreditMemo(
        memo_number=memo_number,
        client_id=data.client_id,
        created_date=data.created_date,
        status=data.status,
        total=total,
        reason=data.reason,
        notes=data.notes,
        created_by_id=current_user.id,
    )
    db.add(memo)
    db.flush()

    for idx, item in enumerate(data.line_items):
        amount = item.quantity * item.unit_amount
        line_item = models.CreditLineItem(
            credit_memo_id=memo.id,
            description=item.description,
            quantity=item.quantity,
            unit_amount=item.unit_amount,
            amount=amount,
            sort_order=item.sort_order or idx,
        )
        db.add(line_item)

    db.commit()
    db.refresh(memo)
    return memo


@router.get("/{memo_id}", response_model=CreditMemoOut)
def get_credit_memo(
    memo_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    memo = db.query(models.CreditMemo).filter_by(id=memo_id).first()
    if not memo:
        raise HTTPException(status_code=404, detail="Credit memo not found")
    return memo


@router.put("/{memo_id}/status")
def update_credit_memo_status(
    memo_id: int,
    status: models.CreditMemoStatus,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    memo = db.query(models.CreditMemo).filter_by(id=memo_id).first()
    if not memo:
        raise HTTPException(status_code=404, detail="Credit memo not found")

    memo.status = status
    if status == models.CreditMemoStatus.sent:
        memo.sent_date = datetime.now()

    db.commit()
    db.refresh(memo)
    return memo
