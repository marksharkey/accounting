from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import date, datetime
from decimal import Decimal

import models
from database import get_db
from auth import get_current_user
from services.billing import next_estimate_number

router = APIRouter()


class LineItemIn(BaseModel):
    description: str
    quantity: float = 1.0
    unit_amount: float
    service_id: Optional[int] = None
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


class EstimateOut(BaseModel):
    id: int
    estimate_number: str
    client_id: int
    client: Optional[ClientOut]
    created_date: date
    expiry_date: Optional[date]
    sent_date: Optional[datetime] = None
    status: models.EstimateStatus
    total: float
    notes: Optional[str]
    internal_notes: Optional[str]
    converted_to_invoice_id: Optional[int]
    line_items: List[LineItemOut]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EstimateCreate(BaseModel):
    client_id: int
    created_date: date
    expiry_date: Optional[date] = None
    line_items: List[LineItemIn]
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    status: models.EstimateStatus = models.EstimateStatus.draft


@router.get("/")
def list_estimates(
    client_id: Optional[int] = None,
    status: Optional[models.EstimateStatus] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.Estimate)
    if client_id:
        query = query.filter_by(client_id=client_id)
    if status:
        query = query.filter_by(status=status)
    if from_date:
        query = query.filter(models.Estimate.created_date >= from_date)
    if to_date:
        query = query.filter(models.Estimate.created_date <= to_date)
    total = query.count()
    estimates = query.order_by(models.Estimate.created_date.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": estimates}


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_estimate(
    data: EstimateCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    client = db.query(models.Client).filter_by(id=data.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    estimate_number = next_estimate_number(db)

    # Calculate total
    total = sum(item.quantity * item.unit_amount for item in data.line_items)

    estimate = models.Estimate(
        estimate_number=estimate_number,
        client_id=data.client_id,
        created_date=data.created_date,
        expiry_date=data.expiry_date,
        status=data.status,
        total=total,
        notes=data.notes,
        internal_notes=data.internal_notes,
        created_by_id=current_user.id,
    )
    db.add(estimate)
    db.flush()

    for idx, item in enumerate(data.line_items):
        amount = item.quantity * item.unit_amount
        line_item = models.EstimateLineItem(
            estimate_id=estimate.id,
            description=item.description,
            quantity=item.quantity,
            unit_amount=item.unit_amount,
            amount=amount,
            service_id=item.service_id,
            sort_order=item.sort_order or idx,
        )
        db.add(line_item)

    db.commit()
    db.refresh(estimate)
    return estimate


@router.get("/{estimate_id}", response_model=EstimateOut)
def get_estimate(
    estimate_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    estimate = db.query(models.Estimate).filter_by(id=estimate_id).first()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    return estimate


@router.put("/{estimate_id}/status")
def update_estimate_status(
    estimate_id: int,
    status: models.EstimateStatus,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    estimate = db.query(models.Estimate).filter_by(id=estimate_id).first()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")

    estimate.status = status
    if status == models.EstimateStatus.sent:
        estimate.sent_date = datetime.now()

    db.commit()
    db.refresh(estimate)
    return estimate


@router.post("/{estimate_id}/convert-to-invoice")
async def convert_estimate_to_invoice(
    estimate_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Convert an estimate to an invoice"""
    estimate = db.query(models.Estimate).filter_by(id=estimate_id).first()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")

    if estimate.converted_to_invoice_id:
        raise HTTPException(status_code=400, detail="This estimate has already been converted to an invoice")

    # Import here to avoid circular imports
    from services.billing import next_invoice_number

    invoice_number = next_invoice_number(db)

    # Create invoice with same line items
    invoice = models.Invoice(
        invoice_number=invoice_number,
        client_id=estimate.client_id,
        created_date=date.today(),
        due_date=estimate.expiry_date or date.today().replace(day=1, month=date.today().month + 1 if date.today().month < 12 else 1, year=date.today().year if date.today().month < 12 else date.today().year + 1),
        status=models.InvoiceStatus.draft,
        notes=estimate.notes,
        internal_notes=estimate.internal_notes,
        created_by_id=current_user.id,
        subtotal=estimate.total,
        total=estimate.total,
    )
    db.add(invoice)
    db.flush()

    # Copy line items from estimate
    for item in estimate.line_items:
        line_item = models.InvoiceLineItem(
            invoice_id=invoice.id,
            description=item.description,
            quantity=item.quantity,
            unit_amount=item.unit_amount,
            amount=item.amount,
            service_id=item.service_id,
            sort_order=item.sort_order,
        )
        db.add(line_item)

    # Mark estimate as converted
    estimate.converted_to_invoice_id = invoice.id
    estimate.status = models.EstimateStatus.accepted

    db.commit()
    db.refresh(invoice)
    return {"invoice": invoice, "message": "Estimate converted to invoice successfully"}
