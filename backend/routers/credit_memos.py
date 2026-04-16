from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, field_validator
from datetime import date, datetime
from decimal import Decimal
import asyncio

import models
from database import get_db
from auth import get_current_user
from services.billing import next_credit_memo_number
from services.email import send_credit_memo_email
from services.pdf import generate_credit_memo_pdf

router = APIRouter()


class LineItemIn(BaseModel):
    description: str
    quantity: float = 1.0
    unit_amount: float
    sort_order: int = 0

    @field_validator('quantity')
    @classmethod
    def quantity_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be greater than 0')
        return v

    @field_validator('unit_amount')
    @classmethod
    def unit_amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Unit amount must be greater than 0')
        return v

    @field_validator('description')
    @classmethod
    def description_cannot_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Description cannot be empty')
        return v


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

    @field_validator('client_id')
    @classmethod
    def client_id_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Client ID must be greater than 0')
        return v

    @field_validator('line_items')
    @classmethod
    def line_items_cannot_be_empty(cls, v):
        if not v:
            raise ValueError('Credit memo must have at least one line item')
        return v


@router.get("/")
def list_credit_memos(
    client_id: Optional[int] = None,
    status: Optional[models.CreditMemoStatus] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    sort_by: str = "created_date",
    sort_order: str = "desc",
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

    # Apply sorting
    sort_column = getattr(models.CreditMemo, sort_by, models.CreditMemo.created_date)
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    total = query.count()
    memos = query.offset(skip).limit(limit).all()
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

    # Calculate total using Decimal for precision
    total = sum(
        Decimal(str(item.quantity)) * Decimal(str(item.unit_amount))
        for item in data.line_items
    ) if data.line_items else Decimal("0.00")

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
        amount = Decimal(str(item.quantity)) * Decimal(str(item.unit_amount))
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


@router.post("/{memo_id}/send")
async def send_credit_memo(
    memo_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Send credit memo and email to client"""
    memo = db.query(models.CreditMemo).filter_by(id=memo_id).first()
    if not memo:
        raise HTTPException(status_code=404, detail="Credit memo not found")

    # Update status and sent date
    memo.status = models.CreditMemoStatus.sent
    memo.sent_date = datetime.now()
    db.commit()

    # Send email asynchronously
    client = memo.client
    if client and client.email:
        try:
            asyncio.create_task(send_credit_memo_email(memo, client))
        except Exception as e:
            print(f"Error sending credit memo email: {e}")

    db.refresh(memo)
    return memo


@router.post("/{memo_id}/mark-sent")
def mark_credit_memo_sent(
    memo_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Mark credit memo as sent without sending email"""
    memo = db.query(models.CreditMemo).filter_by(id=memo_id).first()
    if not memo:
        raise HTTPException(status_code=404, detail="Credit memo not found")

    memo.status = models.CreditMemoStatus.sent
    memo.sent_date = datetime.now()
    db.commit()
    db.refresh(memo)
    return memo


@router.get("/{memo_id}/pdf")
def download_credit_memo_pdf(
    memo_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Download credit memo as PDF"""
    memo = db.query(models.CreditMemo).filter_by(id=memo_id).first()
    if not memo:
        raise HTTPException(status_code=404, detail="Credit memo not found")

    client = memo.client
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    try:
        pdf_buffer = generate_credit_memo_pdf(memo, client, db)
        return StreamingResponse(
            iter([pdf_buffer.getvalue()]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=\"credit-memo-{memo.memo_number}.pdf\""
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")
