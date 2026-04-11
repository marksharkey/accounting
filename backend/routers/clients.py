from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from pydantic import BaseModel
from datetime import datetime, date

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
    billing_type: models.BillingType = models.BillingType.fixed_recurring
    authnet_customer_id: Optional[str] = None
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


class BillingScheduleCreate(BaseModel):
    description: str
    amount: float
    cycle: models.BillingCycle
    next_bill_date: date
    authnet_recurring: bool = False
    service_id: Optional[int] = None
    notes: Optional[str] = None


class BillingScheduleResponse(BillingScheduleCreate):
    id: int
    client_id: int
    is_active: bool
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
    for key, value in data.model_dump().items():
        setattr(client, key, value)
    log = models.ActivityLog(
        entity_type="client", entity_id=client_id, client_id=client_id,
        action="updated", performed_by_id=current_user.id,
        performed_by_name=current_user.full_name
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


@router.get("/{client_id}/billing-schedules")
def get_billing_schedules(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return db.query(models.BillingSchedule).filter_by(
        client_id=client_id, is_active=True
    ).all()


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
    schedule = models.BillingSchedule(client_id=client_id, **data.model_dump())
    db.add(schedule)
    db.flush()
    log = models.ActivityLog(
        entity_type="billing_schedule", entity_id=schedule.id, client_id=client_id,
        action="created", performed_by_id=current_user.id,
        performed_by_name=current_user.full_name
    )
    db.add(log)
    db.commit()
    db.refresh(schedule)
    return schedule


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
