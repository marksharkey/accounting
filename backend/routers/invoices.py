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
from services.email import send_invoice_email, send_invoice_email_with_type, _get_template, _render_template_string, _build_invoice_context
from services.pdf import generate_invoice_pdf
from config import get_settings

settings = get_settings()
router = APIRouter()


# Valid invoice status transitions
VALID_STATUS_TRANSITIONS = {
    models.InvoiceStatus.draft: {models.InvoiceStatus.ready, models.InvoiceStatus.sent, models.InvoiceStatus.voided},
    models.InvoiceStatus.ready: {models.InvoiceStatus.sent, models.InvoiceStatus.voided},
    models.InvoiceStatus.sent: {models.InvoiceStatus.partially_paid, models.InvoiceStatus.paid, models.InvoiceStatus.voided},
    models.InvoiceStatus.partially_paid: {models.InvoiceStatus.paid, models.InvoiceStatus.voided},
    models.InvoiceStatus.paid: set(),  # Terminal state
    models.InvoiceStatus.voided: set(),  # Terminal state
}


def validate_status_transition(current_status: models.InvoiceStatus, new_status: models.InvoiceStatus) -> tuple[bool, str]:
    """Validate if a status transition is allowed. Returns (is_valid, reason)"""
    if current_status == new_status:
        return True, "No change needed"

    allowed_transitions = VALID_STATUS_TRANSITIONS.get(current_status, set())
    if new_status not in allowed_transitions:
        allowed = ", ".join(s.value for s in allowed_transitions) if allowed_transitions else "none"
        return False, f"Cannot transition from {current_status.value} to {new_status.value}. Allowed transitions: {allowed}"

    return True, ""


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
    autocc_verified: bool
    autocc_transaction_id: Optional[str]
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
    autocc_verified: bool = False
    autocc_transaction_id: Optional[str] = None
    previous_balance: float = 0.0
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    billing_schedule_ids: Optional[List[int]] = None

    class Config:
        use_enum_values = False


class AutoccBatchItem(BaseModel):
    invoice_id: int
    paid: bool


class AutoccBatchRequest(BaseModel):
    items: List[AutoccBatchItem]


class AutoccBatchClient(BaseModel):
    id: int
    company_name: str
    email: str
    invoice_id: Optional[int] = None
    invoice_number: Optional[str] = None
    invoice_total: Optional[float] = None
    invoice_status: Optional[models.InvoiceStatus] = None

    class Config:
        from_attributes = True


class AutoccBatchResponse(BaseModel):
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


@router.get("/autocc-batch")
def get_anet_batch(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get all autocc_recurring clients with their latest invoice (for batch processing)."""
    # Get all autocc clients
    clients = db.query(models.Client).filter(
        models.Client.autocc_recurring == True,
        models.Client.is_active == True
    ).all()

    if not clients:
        return []

    client_ids = [c.id for c in clients]

    # Get the latest invoice for each client (any status, ordered by created_date)
    invoices = db.query(models.Invoice).filter(
        models.Invoice.client_id.in_(client_ids)
    ).order_by(
        models.Invoice.client_id,
        models.Invoice.created_date.desc()
    ).all()

    # Build a dict of client_id -> latest invoice (since ordered by date desc, first match is latest)
    latest_invoices = {}
    for invoice in invoices:
        if invoice.client_id not in latest_invoices:
            latest_invoices[invoice.client_id] = invoice

    result = []
    for client in clients:
        invoice = latest_invoices.get(client.id)
        batch_item = AutoccBatchClient(
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


@router.post("/autocc-batch/process")
async def process_anet_batch(
    request: AutoccBatchRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Process AutoCC batch payment decisions."""
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
            # Calculate amount still owed before updating amount_paid
            current_amount_paid = Decimal(str(invoice.amount_paid or 0))
            remaining_amount = invoice.total - current_amount_paid

            invoice.status = models.InvoiceStatus.paid
            invoice.amount_paid = invoice.total
            invoice.balance_due = 0
            db.add(invoice)
            db.flush()

            # Update client balance - decrease by remaining amount owed
            client.account_balance = Decimal(str(client.account_balance or 0)) - remaining_amount
            db.add(client)
            db.flush()

            # Log activity
            log = models.ActivityLog(
                entity_type="invoice",
                entity_id=invoice.id,
                client_id=invoice.client_id,
                action="marked_paid_via_autocc_batch",
                performed_by_id=current_user.id,
                notes="Marked as paid via AutoCC batch process"
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
                action="autocc_charge_declined",
                performed_by_id=current_user.id,
                notes=f"AutoCC charge declined for invoice {invoice.invoice_number}"
            )
            db.add(log)

    db.commit()

    return AutoccBatchResponse(
        paid_count=len(paid_invoices),
        declined_count=len(declined_clients),
        paid_invoices=paid_invoices,
        declined_clients=declined_clients
    )


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
    """Get line items from the most recent non-paid invoice for this client."""
    client = db.query(models.Client).filter_by(id=client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Get the most recent non-paid, non-voided invoice
    # Prefer draft/ready > sent/partially_paid
    previous_invoice = db.query(models.Invoice).filter(
        models.Invoice.client_id == client_id,
        models.Invoice.status.in_([
            models.InvoiceStatus.draft,
            models.InvoiceStatus.ready,
            models.InvoiceStatus.sent,
            models.InvoiceStatus.partially_paid
        ])
    ).order_by(models.Invoice.created_date.desc()).first()

    if not previous_invoice:
        # Fall back to most recent paid/voided if no open invoices exist
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
        autocc_verified=data.autocc_verified,
        autocc_transaction_id=data.autocc_transaction_id,
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

    # Validate transition
    is_valid, reason = validate_status_transition(invoice.status, new_status)
    if not is_valid:
        raise HTTPException(status_code=400, detail=reason)

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


@router.post("/{invoice_id}/verify-autocc")
def verify_autocc(
    invoice_id: int,
    transaction_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    invoice = db.query(models.Invoice).filter_by(id=invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    invoice.autocc_verified = True
    if transaction_id:
        invoice.autocc_transaction_id = transaction_id
    log = models.ActivityLog(
        entity_type="invoice", entity_id=invoice_id, client_id=invoice.client_id,
        action="autocc_verified", performed_by_id=current_user.id,
        performed_by_name=current_user.full_name,
        notes=f"AutoCC transaction ID: {transaction_id or 'not provided'}"
    )
    db.add(log)
    db.commit()
    return {"verified": True, "transaction_id": transaction_id}


@router.get("/{invoice_id}/email-preview")
async def preview_invoice_email(
    invoice_id: int,
    template_type: str = "new_invoice",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get a preview of the rendered email template for an invoice."""
    try:
        invoice = db.query(models.Invoice).filter_by(id=invoice_id).first()
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        client = invoice.client
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        # Convert string to enum
        try:
            enum_type = models.EmailTemplateType[template_type]
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid template type: {template_type}"
            )

        # Build context for template rendering inline
        context = {
            "client_name": client.company_name,
            "invoice_number": invoice.invoice_number,
            "amount_due": f"${float(invoice.total):.2f}",
            "due_date": invoice.due_date.strftime("%B %d, %Y"),
            "company_name": getattr(settings, 'company_name', 'Our Company') or "Our Company",
        }

        # Get template and render
        template = await _get_template(enum_type)
        if not template:
            raise HTTPException(status_code=404, detail=f"Template not found for type: {template_type}")

        subject = _render_template_string(template.subject, context)
        body = _render_template_string(template.body, context)

        return {
            "subject": subject,
            "body": body,
            "template_type": template_type
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in preview_invoice_email: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating preview: {str(e)}")


@router.post("/{invoice_id}/send")
async def send_invoice(
    invoice_id: int,
    template_type: str = "new_invoice",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    invoice = db.query(models.Invoice).filter_by(id=invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Validate can transition to sent
    is_valid, reason = validate_status_transition(invoice.status, models.InvoiceStatus.sent)
    if not is_valid:
        raise HTTPException(status_code=400, detail=reason)

    client = invoice.client
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Convert string to enum
    try:
        enum_type = models.EmailTemplateType[template_type]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid template type: {template_type}"
        )

    old_status = invoice.status
    invoice.status = models.InvoiceStatus.sent
    invoice.sent_date = datetime.utcnow()

    # Update client account balance only if transitioning from draft/ready to sent
    if old_status in [models.InvoiceStatus.draft, models.InvoiceStatus.ready]:
        client.account_balance = Decimal(str(client.account_balance or 0)) + Decimal(str(invoice.total))
        db.add(client)

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
            asyncio.create_task(send_invoice_email_with_type(invoice, client, enum_type))
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

    # Validate can transition to sent
    is_valid, reason = validate_status_transition(invoice.status, models.InvoiceStatus.sent)
    if not is_valid:
        raise HTTPException(status_code=400, detail=reason)

    old_status = invoice.status
    invoice.status = models.InvoiceStatus.sent
    invoice.sent_date = datetime.utcnow()

    # Update client account balance only if transitioning from draft/ready to sent
    if old_status in [models.InvoiceStatus.draft, models.InvoiceStatus.ready]:
        client = invoice.client
        client.account_balance = Decimal(str(client.account_balance or 0)) + Decimal(str(invoice.total))
        db.add(client)

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
    template_type: str = "new_invoice",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    invoice = db.query(models.Invoice).filter_by(id=invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    client = invoice.client
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Convert string to enum
    try:
        enum_type = models.EmailTemplateType[template_type]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid template type: {template_type}"
        )

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
            asyncio.create_task(send_invoice_email_with_type(invoice, client, enum_type))
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

    old_status = invoice.status
    invoice.status = models.InvoiceStatus.voided
    invoice.voided_reason = reason

    # Update client account balance: remove the invoice amount if it was sent
    if old_status in [models.InvoiceStatus.sent, models.InvoiceStatus.partially_paid]:
        client = invoice.client
        # Decrease by remaining balance due (what client still owes on this invoice)
        client.account_balance = Decimal(str(client.account_balance or 0)) - Decimal(str(invoice.balance_due or 0))
        db.add(client)

    log = models.ActivityLog(
        entity_type="invoice", entity_id=invoice_id, client_id=invoice.client_id,
        action="voided", performed_by_id=current_user.id,
        performed_by_name=current_user.full_name, notes=reason
    )
    db.add(log)
    db.commit()
    return {"voided": True, "reason": reason}


@router.delete("/{invoice_id}")
def delete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    invoice = db.query(models.Invoice).filter_by(id=invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status != models.InvoiceStatus.draft:
        raise HTTPException(status_code=400, detail="Only draft invoices can be deleted")

    client_id = invoice.client_id
    invoice_number = invoice.invoice_number

    # Delete related line items
    db.query(models.InvoiceLineItem).filter_by(invoice_id=invoice_id).delete()

    # Delete the invoice
    db.delete(invoice)

    # Log activity
    log = models.ActivityLog(
        entity_type="invoice", entity_id=invoice_id, client_id=client_id,
        action="deleted", performed_by_id=current_user.id,
        performed_by_name=current_user.full_name,
        notes=f"Draft invoice {invoice_number} deleted"
    )
    db.add(log)
    db.commit()

    return {"deleted": True, "invoice_number": invoice_number}


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


