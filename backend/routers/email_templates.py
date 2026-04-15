"""
Email Template Management API Routes
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import EmailTemplate, EmailTemplateType
from pydantic import BaseModel
from typing import List
from datetime import datetime

router = APIRouter(prefix="/api/email-templates", tags=["email-templates"])


class EmailTemplateUpdate(BaseModel):
    """Request model for updating email template."""
    subject: str
    body: str
    is_active: bool = True

    class Config:
        json_schema_extra = {
            "example": {
                "subject": "Invoice {invoice_number} from {company_name}",
                "body": "<html>...</html>",
                "is_active": True
            }
        }


class EmailTemplateResponse(BaseModel):
    """Response model for email template."""
    id: int
    template_type: str
    subject: str
    body: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=List[EmailTemplateResponse])
async def list_templates(
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    List all email templates.

    Query parameters:
    - active_only: If true, only return active templates
    """
    query = db.query(EmailTemplate)

    if active_only:
        query = query.filter(EmailTemplate.is_active == True)

    templates = query.all()
    return templates


@router.get("/{template_type}", response_model=EmailTemplateResponse)
async def get_template(
    template_type: str,
    db: Session = Depends(get_db)
):
    """Get a specific email template by type."""
    try:
        enum_type = EmailTemplateType[template_type]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid template type: {template_type}. Valid types: {[t.value for t in EmailTemplateType]}"
        )

    template = db.query(EmailTemplate).filter(
        EmailTemplate.template_type == enum_type
    ).first()

    if not template:
        raise HTTPException(
            status_code=404,
            detail=f"Template not found for type: {template_type}"
        )

    return template


@router.put("/{template_type}", response_model=EmailTemplateResponse)
async def update_template(
    template_type: str,
    update_data: EmailTemplateUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an email template by type.

    The template must already exist. Subject and body can contain
    Jinja2 template variables like {client_name}, {invoice_number}, etc.
    """
    try:
        enum_type = EmailTemplateType[template_type]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid template type: {template_type}. Valid types: {[t.value for t in EmailTemplateType]}"
        )

    template = db.query(EmailTemplate).filter(
        EmailTemplate.template_type == enum_type
    ).first()

    if not template:
        raise HTTPException(
            status_code=404,
            detail=f"Template not found for type: {template_type}"
        )

    # Update fields
    template.subject = update_data.subject
    template.body = update_data.body
    template.is_active = update_data.is_active

    db.commit()
    db.refresh(template)

    return template


@router.get("/types/available")
async def get_available_types():
    """Get list of all available template types."""
    return {
        "types": [t.value for t in EmailTemplateType],
        "descriptions": {
            "new_invoice": "Sent when a new invoice is created",
            "reminder_invoice": "Sent as a payment reminder before due date",
            "invoice_past_due": "Sent when an invoice becomes overdue",
            "suspension_invoice": "Sent as account suspension warning",
            "cancellation_invoice": "Sent when account is cancelled",
            "paid_invoice": "Sent when payment is received",
            "credit_memo_issued": "Sent when a credit memo is issued",
            "payment_failed": "Sent when payment attempt fails (e.g., CC declined)",
            "default": "Default template for unexpected cases"
        }
    }


@router.get("/variables/supported")
async def get_supported_variables():
    """Get list of supported template variables."""
    return {
        "variables": {
            "common": [
                "{client_name}",
                "{company_name}",
                "{invoice_number}",
                "{memo_number}",
                "{amount_due}",
                "{total}",
                "{balance_due}",
                "{due_date}",
                "{payment_date}",
                "{payment_amount}"
            ],
            "memo_specific": [
                "{credit_amount}",
                "{reason}"
            ],
            "note": "Use double braces like {variable_name} to insert dynamic values"
        }
    }
