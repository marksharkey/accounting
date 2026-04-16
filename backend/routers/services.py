from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

import models
from database import get_db
from auth import get_current_user

router = APIRouter()


class ServiceBase(BaseModel):
    name: str
    description: Optional[str] = None
    default_amount: float
    default_cycle: models.BillingCycle
    category: Optional[str] = None
    income_account_id: Optional[int] = None
    is_active: bool = True


@router.get("/")
def list_services(
    active_only: bool = True,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.ServiceCatalog)
    if active_only:
        query = query.filter_by(is_active=True)
    if category:
        query = query.filter_by(category=category)
    services = query.order_by(models.ServiceCatalog.category, models.ServiceCatalog.name).all()
    return {"total": len(services), "items": services}


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_service(
    data: ServiceBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    service = models.ServiceCatalog(**data.model_dump())
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


@router.put("/{service_id}")
def update_service(
    service_id: int,
    data: ServiceBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    service = db.query(models.ServiceCatalog).filter_by(id=service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    for key, value in data.model_dump().items():
        setattr(service, key, value)
    db.commit()
    db.refresh(service)
    return service


@router.get("/categories")
def list_categories(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    results = db.query(models.ServiceCatalog.category).distinct().all()
    return [r[0] for r in results if r[0]]


@router.get("/accounts")
def list_accounts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return db.query(models.ChartOfAccount).order_by(
        models.ChartOfAccount.account_type,
        models.ChartOfAccount.code
    ).all()


@router.post("/accounts", status_code=status.HTTP_201_CREATED)
def create_account(
    data: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    account = models.ChartOfAccount(**data)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.put("/accounts/{account_id}")
def update_account(
    account_id: int,
    data: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    account = db.query(models.ChartOfAccount).filter_by(id=account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    for key, value in data.items():
        setattr(account, key, value)
    db.commit()
    db.refresh(account)
    return account
