from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, date
from decimal import Decimal

import models
from database import get_db
from auth import get_current_user

router = APIRouter()


class ClientBase(BaseModel):
    company_name: str
    contact_name: Optional[str] = None
    email: str
    email_cc: Optional[str] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    autocc_recurring: bool = False
    autocc_customer_id: Optional[str] = None
    late_fee_type: models.LateFeeType = models.LateFeeType.none
    late_fee_amount: float = 0.00
    late_fee_grace_days: int = 0
    collections_exempt: bool = False
    auto_send_invoices: bool = False
    notes: Optional[str] = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(ClientBase):
    pass


class LineItemIn(BaseModel):
    description: str
    quantity: float = 1.0
    unit_amount: float
    service_id: Optional[int] = None
    domain_id: Optional[int] = None
    sort_order: int = 0


class LineItemResponse(LineItemIn):
    id: int
    billing_schedule_id: int
    amount: float

    class Config:
        from_attributes = True


class BillingScheduleCreate(BaseModel):
    cycle: models.BillingCycle
    next_bill_date: date
    autocc_recurring: bool = False
    notes: Optional[str] = None
    line_items: List[LineItemIn]


class BillingScheduleUpdate(BaseModel):
    cycle: models.BillingCycle
    next_bill_date: date
    autocc_recurring: bool = False
    notes: Optional[str] = None
    line_items: List[LineItemIn]


class BillingScheduleResponse(BaseModel):
    id: int
    client_id: int
    amount: float
    cycle: models.BillingCycle
    next_bill_date: date
    autocc_recurring: bool
    is_active: bool
    notes: Optional[str]
    line_items: List[LineItemResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClientResponse(ClientBase):
    id: int
    account_status: models.AccountStatus
    account_balance: float
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("/")
def list_clients(
    search: Optional[str] = None,
    active_only: bool = True,
    status: Optional[models.AccountStatus] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.Client)
    if active_only:
        query = query.filter(models.Client.is_active == True)
    if status:
        query = query.filter(models.Client.account_status == status)
    if search:
        query = query.filter(
            or_(
                models.Client.company_name.ilike(f"%{search}%"),
                models.Client.contact_name.ilike(f"%{search}%"),
                models.Client.email.ilike(f"%{search}%"),
            )
        )
    total = query.count()
    clients = query.order_by(models.Client.company_name).offset(skip).limit(limit).all()
    return {"total": total, "items": clients}


@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    data: ClientCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    client = models.Client(**data.model_dump())
    db.add(client)
    db.flush()
    log = models.ActivityLog(
        entity_type="client", entity_id=client.id, client_id=client.id,
        action="created", performed_by_id=current_user.id,
        performed_by_name=current_user.full_name
    )
    db.add(log)
    db.commit()
    db.refresh(client)
    return client


@router.get("/{client_id}/billing-schedules", response_model=List[BillingScheduleResponse])
def get_billing_schedules(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return db.query(models.BillingSchedule).filter_by(
        client_id=client_id, is_active=True
    ).order_by(models.BillingSchedule.next_bill_date).all()


def validate_domain_billing_window(db: Session, line_items: List[LineItemIn], due_date: date):
    """Validate that domains are billed at least 60 days before expiration."""
    from datetime import timedelta
    min_due_date = due_date + timedelta(days=60)

    warnings = []
    for item in line_items:
        if item.domain_id:
            domain = db.query(models.Domain).filter_by(id=item.domain_id).first()
            if domain and domain.expiration_date < min_due_date:
                days_short = (min_due_date - domain.expiration_date).days
                warnings.append(f"Domain {domain.domain_name} expires {days_short} days before the 60-day buffer (expires {domain.expiration_date})")

    return warnings


@router.post("/{client_id}/billing-schedules", response_model=BillingScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_billing_schedule(
    client_id: int,
    data: BillingScheduleCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    client = db.query(models.Client).filter_by(id=client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Validate domain billing windows
    warnings = validate_domain_billing_window(db, data.line_items, data.next_bill_date)
    for warning in warnings:
        import logging
        logging.warning(f"Billing schedule warning for client {client_id}: {warning}")

    # Calculate total amount from line items
    total_amount = sum(
        Decimal(str(item.quantity)) * Decimal(str(item.unit_amount))
        for item in data.line_items
    )

    schedule = models.BillingSchedule(
        client_id=client_id,
        cycle=data.cycle,
        next_bill_date=data.next_bill_date,
        autocc_recurring=data.autocc_recurring,
        notes=data.notes,
        amount=total_amount
    )
    db.add(schedule)
    db.flush()

    # Create line items
    for idx, item in enumerate(data.line_items):
        line_amount = Decimal(str(item.quantity)) * Decimal(str(item.unit_amount))
        line_item = models.BillingScheduleLineItem(
            billing_schedule_id=schedule.id,
            description=item.description,
            quantity=item.quantity,
            unit_amount=item.unit_amount,
            amount=line_amount,
            service_id=item.service_id,
            domain_id=item.domain_id,
            sort_order=item.sort_order if item.sort_order else idx
        )
        db.add(line_item)

    log = models.ActivityLog(
        entity_type="billing_schedule", entity_id=schedule.id, client_id=client_id,
        action="created", performed_by_id=current_user.id,
        performed_by_name=current_user.full_name
    )
    db.add(log)
    db.commit()
    db.refresh(schedule)
    return schedule


@router.put("/{client_id}/billing-schedules/{schedule_id}", response_model=BillingScheduleResponse)
def update_billing_schedule(
    client_id: int,
    schedule_id: int,
    data: BillingScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    schedule = db.query(models.BillingSchedule).filter_by(
        id=schedule_id, client_id=client_id
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Billing schedule not found")

    # Validate domain billing windows
    warnings = validate_domain_billing_window(db, data.line_items, data.next_bill_date)
    for warning in warnings:
        import logging
        logging.warning(f"Billing schedule warning for client {client_id}: {warning}")

    # Calculate total amount from line items
    total_amount = sum(
        Decimal(str(item.quantity)) * Decimal(str(item.unit_amount))
        for item in data.line_items
    )

    # Track changes for activity log
    changes = []
    if schedule.cycle != data.cycle:
        changes.append(f"Cycle: {schedule.cycle} → {data.cycle}")
    if schedule.next_bill_date != data.next_bill_date:
        changes.append(f"Next Bill Date: {schedule.next_bill_date} → {data.next_bill_date}")
    if schedule.autocc_recurring != data.autocc_recurring:
        changes.append(f"AutoCC Recurring: {schedule.autocc_recurring} → {data.autocc_recurring}")
    if schedule.amount != total_amount:
        changes.append(f"Amount: ${float(schedule.amount):.2f} → ${float(total_amount):.2f}")
    if schedule.notes != data.notes:
        changes.append(f"Notes updated")

    # Update schedule header
    schedule.cycle = data.cycle
    schedule.next_bill_date = data.next_bill_date
    schedule.autocc_recurring = data.autocc_recurring
    schedule.notes = data.notes
    schedule.amount = total_amount

    # Delete existing line items and recreate
    db.query(models.BillingScheduleLineItem).filter_by(billing_schedule_id=schedule_id).delete()

    # Create new line items
    for idx, item in enumerate(data.line_items):
        line_amount = Decimal(str(item.quantity)) * Decimal(str(item.unit_amount))
        line_item = models.BillingScheduleLineItem(
            billing_schedule_id=schedule_id,
            description=item.description,
            quantity=item.quantity,
            unit_amount=item.unit_amount,
            amount=line_amount,
            service_id=item.service_id,
            domain_id=item.domain_id,
            sort_order=item.sort_order if item.sort_order else idx
        )
        db.add(line_item)

    # Create activity log with detailed changes
    notes = "; ".join(changes) if changes else "No changes"
    log = models.ActivityLog(
        entity_type="billing_schedule", entity_id=schedule_id, client_id=client_id,
        action="updated", performed_by_id=current_user.id,
        performed_by_name=current_user.full_name,
        notes=notes
    )
    db.add(log)
    db.commit()
    db.refresh(schedule)
    return schedule


@router.delete("/{client_id}/billing-schedules/{schedule_id}")
def delete_billing_schedule(
    client_id: int,
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    schedule = db.query(models.BillingSchedule).filter_by(
        id=schedule_id, client_id=client_id
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Billing schedule not found")

    schedule.is_active = False

    log = models.ActivityLog(
        entity_type="billing_schedule", entity_id=schedule_id, client_id=client_id,
        action="deactivated", performed_by_id=current_user.id,
        performed_by_name=current_user.full_name
    )
    db.add(log)
    db.commit()
    return {"message": "Billing schedule deactivated"}


@router.get("/{client_id}/invoices")
def get_client_invoices(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return db.query(models.Invoice).filter_by(client_id=client_id)\
        .order_by(models.Invoice.created_date.desc()).all()


@router.get("/{client_id}/activity")
def get_client_activity(
    client_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return db.query(models.ActivityLog).filter_by(client_id=client_id)\
        .order_by(models.ActivityLog.timestamp.desc()).limit(limit).all()


@router.get("/{client_id}")
def get_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    client = db.query(models.Client).filter_by(id=client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.put("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: int,
    data: ClientUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    client = db.query(models.Client).filter_by(id=client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Track changes for activity log
    changes = []
    for key, value in data.model_dump().items():
        old_value = getattr(client, key)
        if old_value != value:
            # Format the field name for display
            field_name = key.replace('_', ' ').title()
            changes.append(f"{field_name}: {old_value} → {value}")
        setattr(client, key, value)

    # Create activity log with detailed changes
    notes = "; ".join(changes) if changes else "No changes"
    log = models.ActivityLog(
        entity_type="client", entity_id=client_id, client_id=client_id,
        action="updated", performed_by_id=current_user.id,
        performed_by_name=current_user.full_name,
        notes=notes
    )
    db.add(log)
    db.commit()
    db.refresh(client)
    return client


@router.delete("/{client_id}")
def deactivate_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    client = db.query(models.Client).filter_by(id=client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    client.is_active = False
    log = models.ActivityLog(
        entity_type="client", entity_id=client_id, client_id=client_id,
        action="deactivated", performed_by_id=current_user.id,
        performed_by_name=current_user.full_name
    )
    db.add(log)
    db.commit()
    return {"message": "Client deactivated"}
