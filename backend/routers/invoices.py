from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from typing import Optional, List
from pydantic import BaseModel
from datetime import date, timedelta, datetime
from decimal import Decimal
import asyncio

import models
from database import get_db
from auth import get_current_user
from services.billing import next_invoice_number
from services.email import send_invoice_email
from services.pdf import generate_invoice_pdf
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


class LineItemOut(BaseModel):
    id: int
    description: str
    quantity: float
    unit_amount: float
    amount: float
    is_prorated: bool
    prorate_note: Optional[str] = None

    class Config:
        from_attributes = True


class PaymentOut(BaseModel):
    id: int
    payment_date: date
    amount: float
    method: str
    reference_number: Optional[str]

    class Config:
        from_attributes = True


class ClientOut(BaseModel):
    id: int
    company_name: str
    contact_name: Optional[str]
    email: str
    phone: Optional[str]
    address_line1: Optional[str]
    address_line2: Optional[str]
    city: Optional[str]
    state: Optional[str]
    zip_code: Optional[str]

    class Config:
        from_attributes = True


class InvoiceOut(BaseModel):
    id: int
    invoice_number: str
    client_id: int
    client: Optional[ClientOut]
    created_date: date
    due_date: date
    sent_date: Optional[datetime] = None
    status: models.InvoiceStatus
    authnet_verified: bool
    authnet_transaction_id: Optional[str]
    subtotal: float
    late_fee_amount: float
    total: float
    amount_paid: float
    balance_due: float
    previous_balance: float
    notes: Optional[str]
    internal_notes: Optional[str]
    voided_reason: Optional[str]
    line_items: List[LineItemOut]
    payments: List[PaymentOut]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InvoiceCreate(BaseModel):
    client_id: int
    created_date: date
    due_date: date
    line_items: List[LineItemIn]
    status: models.InvoiceStatus = models.InvoiceStatus.draft
    authnet_verified: bool = False
    authnet_transaction_id: Optional[str] = None
    previous_balance: float = 0.0
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    billing_schedule_ids: Optional[List[int]] = None

    class Config:
        use_enum_values = False


class AnetBatchItem(BaseModel):
    invoice_id: int
    paid: bool


class AnetBatchRequest(BaseModel):
    items: List[AnetBatchItem]


class AnetBatchClient(BaseModel):
    id: int
    company_name: str
    email: str
    invoice_id: Optional[int] = None
    invoice_number: Optional[str] = None
    invoice_total: Optional[float] = None
    invoice_status: Optional[models.InvoiceStatus] = None

    class Config:
        from_attributes = True


class AnetBatchResponse(BaseModel):
    paid_count: int
    declined_count: int
    paid_invoices: List[str]
    declined_clients: List[str]


@router.get("/")
def list_invoices(
    invoice_number: Optional[str] = None,
    client_id: Optional[int] = None,
    status: Optional[models.InvoiceStatus] = None,
    overdue: Optional[bool] = None,
    is_open: Optional[bool] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    sort_by: str = "created_date",
    sort_order: str = "desc",
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.Invoice).options(joinedload(models.Invoice.client))
    if invoice_number:
        query = query.filter(models.Invoice.invoice_number.ilike(f"%{invoice_number}%"))
    if client_id:
        query = query.filter_by(client_id=client_id)
    if status:
        query = query.filter_by(status=status)
    if overdue:
        # Overdue invoices: due_date in the past and balance_due > 0
        today = date.today()
        query = query.filter(
            models.Invoice.due_date < today,
            models.Invoice.balance_due > 0
        )
    if is_open:
        # Open invoices: sent or partially_paid status and balance_due > 0
        query = query.filter(
            models.Invoice.status.in_([models.InvoiceStatus.sent, models.InvoiceStatus.partially_paid]),
            models.Invoice.balance_due > 0
        )
    if from_date:
        query = query.filter(models.Invoice.created_date >= from_date)
    if to_date:
        query = query.filter(models.Invoice.created_date <= to_date)
    total = query.count()

    # Handle sorting
    sort_column = getattr(models.Invoice, sort_by, models.Invoice.created_date)
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    invoices = query.offset(skip).limit(limit).all()
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
    due_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    client = db.query(models.Client).filter_by(id=client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Compute default due_date (first of next month) if not provided
    if not due_date:
        today = date.today()
        if today.month == 12:
            due_date = today.replace(year=today.year + 1, month=1, day=1)
        else:
            due_date = today.replace(month=today.month + 1, day=1)

    # Filter schedules by due date - only include those due by the invoice due date
    schedules = db.query(models.BillingSchedule).filter(
        models.BillingSchedule.client_id == client_id,
        models.BillingSchedule.is_active == True,
        models.BillingSchedule.next_bill_date <= due_date
    ).all()

    # Extract line items from matching billing schedules
    line_items = []
    schedule_ids = []
    for schedule in schedules:
        schedule_ids.append(schedule.id)
        for item in schedule.line_items:
            line_items.append({
                "description": item.description,
                "quantity": float(item.quantity),
                "unit_amount": float(item.unit_amount),
                "amount": float(item.amount),
                "service_id": item.service_id,
            })

    # Sort by description
    line_items = sorted(line_items, key=lambda x: x["description"])
    return {
        "client": client,
        "suggested_due_date": due_date,
        "line_items": line_items,
        "billing_schedule_ids": schedule_ids,
    }


@router.get("/duplicate-previous/{client_id}")
def duplicate_previous_invoice(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get line items from the most recent invoice for this client."""
    client = db.query(models.Client).filter_by(id=client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Get the most recent invoice
    previous_invoice = db.query(models.Invoice).filter(
        models.Invoice.client_id == client_id
    ).order_by(models.Invoice.created_date.desc()).first()

    if not previous_invoice:
        raise HTTPException(status_code=404, detail="No previous invoice found")

    # Extract line items from previous invoice
    line_items = [
        {
            "description": item.description,
            "quantity": float(item.quantity),
            "unit_amount": float(item.unit_amount),
            "amount": float(item.amount),
            "service_id": item.service_id,
        }
        for item in previous_invoice.line_items
    ]

    return {
        "client": client,
        "previous_invoice": {
            "number": previous_invoice.invoice_number,
            "date": previous_invoice.created_date,
        },
        "line_items": line_items,
    }


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
    previous_balance = float(client.account_balance) if client.account_balance else 0.0
    invoice = models.Invoice(
        invoice_number=invoice_number,
        client_id=data.client_id,
        created_date=data.created_date,
        due_date=data.due_date,
        status=data.status,
        authnet_verified=data.authnet_verified,
        authnet_transaction_id=data.authnet_transaction_id,
        previous_balance=previous_balance,
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

    # Advance billing schedule dates for any schedules that were included in this invoice
    if data.billing_schedule_ids and len(data.billing_schedule_ids) > 0:
        from services.billing import advance_billing_date
        schedules = db.query(models.BillingSchedule).filter(
            models.BillingSchedule.id.in_(data.billing_schedule_ids)
        ).all()
        for schedule in schedules:
            schedule.next_bill_date = advance_billing_date(schedule.next_bill_date, schedule.cycle)
        db.commit()

    return invoice


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    invoice = db.query(models.Invoice).options(
        joinedload(models.Invoice.client),
        joinedload(models.Invoice.line_items),
        joinedload(models.Invoice.payments)
    ).filter_by(id=invoice_id).first()
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


@router.post("/{invoice_id}/send")
async def send_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    invoice = db.query(models.Invoice).filter_by(id=invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    client = invoice.client
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    old_status = invoice.status
    invoice.status = models.InvoiceStatus.sent
    invoice.sent_date = datetime.utcnow()

    log = models.ActivityLog(
        entity_type="invoice", entity_id=invoice_id, client_id=invoice.client_id,
        action="sent", performed_by_id=current_user.id,
        performed_by_name=current_user.full_name,
        notes=f"Invoice sent to {client.email}"
    )
    db.add(log)
    db.commit()

    if client.email:
        try:
            asyncio.create_task(send_invoice_email(invoice, client))
        except Exception as e:
            print(f"Error sending invoice email: {e}")

    return {"invoice_id": invoice_id, "status": models.InvoiceStatus.sent}


@router.post("/{invoice_id}/mark-sent")
def mark_invoice_sent(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    invoice = db.query(models.Invoice).filter_by(id=invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice.status = models.InvoiceStatus.sent
    invoice.sent_date = datetime.utcnow()

    log = models.ActivityLog(
        entity_type="invoice", entity_id=invoice_id, client_id=invoice.client_id,
        action="marked_sent", performed_by_id=current_user.id,
        performed_by_name=current_user.full_name,
        notes="Invoice marked as sent without email"
    )
    db.add(log)
    db.commit()

    return {"invoice_id": invoice_id, "status": models.InvoiceStatus.sent}


@router.post("/{invoice_id}/resend")
async def resend_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    invoice = db.query(models.Invoice).filter_by(id=invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    client = invoice.client
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    log = models.ActivityLog(
        entity_type="invoice", entity_id=invoice_id, client_id=invoice.client_id,
        action="resent", performed_by_id=current_user.id,
        performed_by_name=current_user.full_name,
        notes=f"Invoice resent to {client.email}"
    )
    db.add(log)
    db.commit()

    if client.email:
        try:
            asyncio.create_task(send_invoice_email(invoice, client))
        except Exception as e:
            print(f"Error sending invoice email: {e}")

    return {"invoice_id": invoice_id, "resent": True}


@router.post("/{invoice_id}/void")
def void_invoice(
    invoice_id: int,
    reason: str = "",
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


@router.get("/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    invoice = db.query(models.Invoice).filter_by(id=invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    client = invoice.client
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    try:
        pdf_buffer = generate_invoice_pdf(invoice, client, db)
        return StreamingResponse(
            iter([pdf_buffer.getvalue()]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=\"{invoice.invoice_number}.pdf\""
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")


@router.get("/anet-batch")
def get_anet_batch(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get all authnet_recurring clients with their latest draft/sent invoice."""
    clients = db.query(models.Client).filter(
        models.Client.authnet_recurring == True,
        models.Client.is_active == True
    ).all()

    result = []
    for client in clients:
        # Find latest draft or sent invoice for this client
        invoice = db.query(models.Invoice).filter(
            models.Invoice.client_id == client.id,
            models.Invoice.status.in_([models.InvoiceStatus.draft, models.InvoiceStatus.sent])
        ).order_by(models.Invoice.created_date.desc()).first()

        batch_item = AnetBatchClient(
            id=client.id,
            company_name=client.company_name,
            email=client.email,
            invoice_id=invoice.id if invoice else None,
            invoice_number=invoice.invoice_number if invoice else None,
            invoice_total=invoice.total if invoice else None,
            invoice_status=invoice.status if invoice else None
        )
        result.append(batch_item)

    return result


@router.post("/anet-batch/process")
async def process_anet_batch(
    request: AnetBatchRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Process A.net batch payment decisions."""
    from services.email import send_invoice_email, send_cc_declined_email

    paid_invoices = []
    declined_clients = []

    for item in request.items:
        invoice = db.query(models.Invoice).filter_by(id=item.invoice_id).first()
        if not invoice:
            continue

        client = invoice.client
        if not client:
            continue

        if item.paid:
            # Mark invoice as paid
            invoice.status = models.InvoiceStatus.paid
            invoice.amount_paid = invoice.total
            invoice.balance_due = 0
            db.add(invoice)
            db.flush()

            # Update client balance
            client.account_balance -= invoice.total
            db.add(client)
            db.flush()

            # Log activity
            log = models.ActivityLog(
                entity_type="invoice",
                entity_id=invoice.id,
                client_id=invoice.client_id,
                action="marked_paid_via_anet_batch",
                performed_by_id=current_user.id,
                notes="Marked as paid via A.net batch process"
            )
            db.add(log)

            # Send invoice email
            try:
                await send_invoice_email(invoice, client)
                paid_invoices.append(invoice.invoice_number)
            except Exception as e:
                print(f"Error sending invoice email for {invoice.invoice_number}: {str(e)}")
        else:
            # Send CC declined email
            try:
                await send_cc_declined_email(client)
                declined_clients.append(client.company_name)
            except Exception as e:
                print(f"Error sending declined email for {client.company_name}: {str(e)}")

            # Log activity
            log = models.ActivityLog(
                entity_type="invoice",
                entity_id=invoice.id,
                client_id=invoice.client_id,
                action="anet_charge_declined",
                performed_by_id=current_user.id,
                notes=f"A.net charge declined for invoice {invoice.invoice_number}"
            )
            db.add(log)

    db.commit()

    return AnetBatchResponse(
        paid_count=len(paid_invoices),
        declined_count=len(declined_clients),
        paid_invoices=paid_invoices,
        declined_clients=declined_clients
    )
