from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
import os
import shutil
from pathlib import Path

import models
from database import get_db
from auth import get_current_user
from config import get_settings

router = APIRouter()

# Ensure uploads directory exists
UPLOADS_DIR = Path("uploads/logos")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


class CompanyInfoUpdate(BaseModel):
    company_name: str
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website_url: Optional[str] = None


class CompanyInfoResponse(BaseModel):
    id: int
    company_name: str
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website_url: Optional[str] = None
    logo_filename: Optional[str] = None
    logo_url: Optional[str] = None
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        data = super().from_orm(obj)
        if obj.logo_filename:
            settings = get_settings()
            data.logo_url = f"{settings.api_base_url}/uploads/logos/{obj.logo_filename}"
        return data


@router.get("/", response_model=CompanyInfoResponse)
def get_company_info(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    info = db.query(models.CompanyInfo).first()
    if not info:
        raise HTTPException(status_code=404, detail="Company info not found. Please create one first.")
    response = CompanyInfoResponse.from_orm(info)
    return response


@router.put("/", response_model=CompanyInfoResponse)
def upsert_company_info(
    data: CompanyInfoUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    info = db.query(models.CompanyInfo).first()

    if not info:
        # Create new record
        info = models.CompanyInfo(**data.model_dump())
        db.add(info)
    else:
        # Update existing record
        for key, value in data.model_dump().items():
            setattr(info, key, value)

    db.flush()

    # Log the activity
    log = models.ActivityLog(
        entity_type="company_info",
        entity_id=info.id,
        action="updated",
        performed_by_id=current_user.id,
        performed_by_name=current_user.full_name
    )
    db.add(log)
    db.commit()
    db.refresh(info)

    response = CompanyInfoResponse.from_orm(info)
    return response


@router.post("/logo")
def upload_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    info = db.query(models.CompanyInfo).first()
    if not info:
        raise HTTPException(status_code=404, detail="Company info not found. Please create one first.")

    # Validate file type
    allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}")

    # Delete old logo if exists
    if info.logo_filename:
        old_path = UPLOADS_DIR / info.logo_filename
        if old_path.exists():
            old_path.unlink()

    # Save new logo
    filename = f"company_logo_{datetime.utcnow().timestamp()}{file_ext}"
    file_path = UPLOADS_DIR / filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    info.logo_filename = filename

    log = models.ActivityLog(
        entity_type="company_info",
        entity_id=info.id,
        action="logo_uploaded",
        performed_by_id=current_user.id,
        performed_by_name=current_user.full_name
    )
    db.add(log)
    db.commit()
    db.refresh(info)

    response = CompanyInfoResponse.from_orm(info)
    return response
