from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from datetime import date
from decimal import Decimal

import models
from database import get_db
from auth import get_current_user

router = APIRouter()


class PaymentIn(BaseModel):
    invoice_id: int
    payment_date: date
    amount: float
    method: models.PaymentMethod
    reference_number: Optional[str] = None
    notes: Optional[str] = None


@router.post("/", status_code=201)
def record_payment(
    data: PaymentIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    invoice = db.query(models.Invoice).filter_by(id=data.invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status == models.InvoiceStatus.voided:
        raise HTTPException(status_code=400, detail="Cannot record payment on a voided invoice")

    payment = models.Payment(
        invoice_id=data.invoice_id,
        client_id=invoice.client_id,
        payment_date=data.payment_date,
        amount=data.amount,
        method=data.method,
        reference_number=data.reference_number,
        notes=data.notes,
        recorded_by_id=current_user.id,
    )
    db.add(payment)
    db.flush()

    total_paid = sum(Decimal(str(p.amount)) for p in invoice.payments)
    invoice.amount_paid = total_paid
    invoice.balance_due = Decimal(str(invoice.total)) - total_paid

    if invoice.balance_due <= 0:
        invoice.status = models.InvoiceStatus.paid
    elif total_paid > 0:
        invoice.status = models.InvoiceStatus.partially_paid

    client = db.query(models.Client).filter_by(id=invoice.client_id).first()
    client.account_balance = Decimal(str(client.account_balance)) - Decimal(str(data.amount))

    log = models.ActivityLog(
        entity_type="payment", entity_id=payment.id, client_id=invoice.client_id,
        action="payment_recorded", performed_by_id=current_user.id,
        performed_by_name=current_user.full_name,
        notes=f"${data.amount:.2f} via {data.method.value} — Invoice {invoice.invoice_number}"
    )
    db.add(log)
    db.commit()
    db.refresh(payment)
    return payment


@router.get("/")
def list_payments(
    client_id: Optional[int] = None,
    invoice_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.Payment)
    if client_id:
        query = query.filter_by(client_id=client_id)
    if invoice_id:
        query = query.filter_by(invoice_id=invoice_id)
    total = query.count()
    payments = query.order_by(models.Payment.payment_date.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": payments}
