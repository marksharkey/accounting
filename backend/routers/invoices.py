from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, List
from pydantic import BaseModel
from datetime import date, timedelta
from decimal import Decimal
import asyncio

import models
from database import get_db
from auth import get_current_user
from services.billing import next_invoice_number
from services.email import send_invoice_email
from config import get_settings

settings = get_settings()
router = APIRouter()


class LineItemIn(BaseModel):
    description: str
    quantity: float = 1.0
    unit_amount: float
    service_id: Optional[int] = None
    is_prorated: bool = False
    prorate_note: Optional[str] = None
    sort_order: int = 0


class InvoiceCreate(BaseModel):
    client_id: int
    created_date: date
    due_date: date
    line_items: List[LineItemIn]
    status: models.InvoiceStatus = models.InvoiceStatus.draft
    authnet_verified: bool = False
    authnet_transaction_id: Optional[str] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None


@router.get("/")
def list_invoices(
    client_id: Optional[int] = None,
    status: Optional[models.InvoiceStatus] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.Invoice)
    if client_id:
        query = query.filter_by(client_id=client_id)
    if status:
        query = query.filter_by(status=status)
    if from_date:
        query = query.filter(models.Invoice.created_date >= from_date)
    if to_date:
        query = query.filter(models.Invoice.created_date <= to_date)
    total = query.count()
    invoices = query.order_by(models.Invoice.created_date.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": invoices}


@router.get("/due-for-billing")
def clients_due_for_billing(
    days_ahead: int = 7,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    cutoff = date.today() + timedelta(days=days_ahead)
    schedules = db.query(models.BillingSchedule).filter(
        and_(
            models.BillingSchedule.is_active == True,
            models.BillingSchedule.next_bill_date <= cutoff
        )
    ).all()
    client_map = {}
    for s in schedules:
        if s.client_id not in client_map:
            client_map[s.client_id] = {"client": s.client, "schedules": []}
        client_map[s.client_id]["schedules"].append(s)
    return list(client_map.values())


@router.post("/prefill/{client_id}")
def prefill_invoice(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    client = db.query(models.Client).filter_by(id=client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    schedules = db.query(models.BillingSchedule).filter_by(
        client_id=client_id, is_active=True
    ).all()
    line_items = [{
        "description": s.description,
        "quantity": 1.0,
        "unit_amount": float(s.amount),
        "amount": float(s.amount),
        "service_id": s.service_id,
    } for s in schedules]
    today = date.today()
    if today.month == 12:
        due_date = today.replace(year=today.year + 1, month=1, day=1)
    else:
        due_date = today.replace(month=today.month + 1, day=1)
    return {"client": client, "suggested_due_date": due_date, "line_items": line_items}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_invoice(
    data: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    client = db.query(models.Client).filter_by(id=data.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    invoice_number = next_invoice_number(db)
    invoice = models.Invoice(
        invoice_number=invoice_number,
        client_id=data.client_id,
        created_date=data.created_date,
        due_date=data.due_date,
        status=data.status,
        authnet_verified=data.authnet_verified,
        authnet_transaction_id=data.authnet_transaction_id,
        notes=data.notes,
        internal_notes=data.internal_notes,
        created_by_id=current_user.id,
    )
    db.add(invoice)
    db.flush()

    subtotal = Decimal("0.00")
    for i, item in enumerate(data.line_items):
        amount = Decimal(str(item.quantity)) * Decimal(str(item.unit_amount))
        li = models.InvoiceLineItem(
            invoice_id=invoice.id,
            description=item.description,
            quantity=item.quantity,
            unit_amount=item.unit_amount,
            amount=amount,
            service_id=item.service_id,
            is_prorated=item.is_prorated,
            prorate_note=item.prorate_note,
            sort_order=i,
        )
        db.add(li)
        subtotal += amount

    invoice.subtotal = subtotal
    invoice.total = subtotal
    invoice.balance_due = subtotal

    log = models.ActivityLog(
        entity_type="invoice", entity_id=invoice.id, client_id=data.client_id,
        action="created", performed_by_id=current_user.id,
        performed_by_name=current_user.full_name,
        notes=f"Invoice {invoice_number} created"
    )
    db.add(log)
    db.commit()
    db.refresh(invoice)

    # Send email if invoice is marked as ready or authnet verified
    if (invoice.status == models.InvoiceStatus.ready or invoice.authnet_verified) and client.email:
        try:
            asyncio.create_task(send_invoice_email(
                client_email=client.email,
                client_name=client.company_name,
                invoice_number=invoice_number,
                total=float(invoice.total)
            ))
        except Exception as e:
            print(f"Error sending invoice email: {e}")

    return invoice


@router.get("/{invoice_id}")
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    invoice = db.query(models.Invoice).filter_by(id=invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.put("/{invoice_id}/status")
async def update_invoice_status(
    invoice_id: int,
    new_status: models.InvoiceStatus,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    invoice = db.query(models.Invoice).filter_by(id=invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    old_status = invoice.status
    invoice.status = new_status
    log = models.ActivityLog(
        entity_type="invoice", entity_id=invoice_id, client_id=invoice.client_id,
        action="status_changed", performed_by_id=current_user.id,
        performed_by_name=current_user.full_name,
        notes=f"Status: {old_status} → {new_status}"
    )
    db.add(log)
    db.commit()

    # Send email if transitioning to ready
    if old_status != models.InvoiceStatus.ready and new_status == models.InvoiceStatus.ready:
        client = invoice.client
        if client and client.email:
            try:
                asyncio.create_task(send_invoice_email(
                    client_email=client.email,
                    client_name=client.company_name,
                    invoice_number=invoice.invoice_number,
                    total=float(invoice.total)
                ))
            except Exception as e:
                print(f"Error sending invoice email: {e}")

    return {"invoice_id": invoice_id, "status": new_status}


@router.post("/{invoice_id}/verify-authnet")
def verify_authnet(
    invoice_id: int,
    transaction_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    invoice = db.query(models.Invoice).filter_by(id=invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    invoice.authnet_verified = True
    if transaction_id:
        invoice.authnet_transaction_id = transaction_id
    log = models.ActivityLog(
        entity_type="invoice", entity_id=invoice_id, client_id=invoice.client_id,
        action="authnet_verified", performed_by_id=current_user.id,
        performed_by_name=current_user.full_name,
        notes=f"A.net transaction ID: {transaction_id or 'not provided'}"
    )
    db.add(log)
    db.commit()
    return {"verified": True, "transaction_id": transaction_id}


@router.post("/{invoice_id}/void")
def void_invoice(
    invoice_id: int,
    reason: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    invoice = db.query(models.Invoice).filter_by(id=invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status == models.InvoiceStatus.paid:
        raise HTTPException(status_code=400, detail="Cannot void a paid invoice. Issue a credit memo instead.")
    invoice.status = models.InvoiceStatus.voided
    invoice.voided_reason = reason
    log = models.ActivityLog(
        entity_type="invoice", entity_id=invoice_id, client_id=invoice.client_id,
        action="voided", performed_by_id=current_user.id,
        performed_by_name=current_user.full_name, notes=reason
    )
    db.add(log)
    db.commit()
    return {"voided": True, "reason": reason}
