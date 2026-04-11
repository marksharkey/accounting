from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import date
from decimal import Decimal
import calendar
import asyncio

import models
from database import get_db
from auth import get_current_user
from services.email import (
    send_late_fee_notice_email,
    send_suspension_warning_email,
    send_deletion_warning_email
)

router = APIRouter()


def _invoice_summary(inv: models.Invoice) -> dict:
    return {
        "invoice_id": inv.id,
        "invoice_number": inv.invoice_number,
        "client_id": inv.client_id,
        "client_name": inv.client.company_name,
        "due_date": inv.due_date,
        "days_overdue": (date.today() - inv.due_date).days,
        "balance_due": float(inv.balance_due),
    }


@router.get("/daily-queue")
def daily_action_queue(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    today = date.today()
    overdue = db.query(models.Invoice).join(models.Client).filter(
        and_(
            models.Invoice.due_date < today,
            models.Invoice.status.in_([
                models.InvoiceStatus.sent,
                models.InvoiceStatus.partially_paid
            ]),
            models.Client.collections_exempt == False,
            models.Client.collections_paused == False,
        )
    ).all()

    late_fee_candidates = [
        inv for inv in overdue
        if (today - inv.due_date).days >= 10
        and float(inv.late_fee_amount) == 0
        and inv.client.late_fee_type != models.LateFeeType.none
    ]
    suspension_candidates = [
        inv for inv in overdue
        if (today - inv.due_date).days >= 20
    ]
    last_day = calendar.monthrange(today.year, today.month)[1]
    deletion_candidates = [
        inv for inv in overdue
        if (today - inv.due_date).days >= 30 and (last_day - today.day) <= 3
    ]

    return {
        "date": today,
        "overdue_count": len(overdue),
        "late_fee_candidates": [_invoice_summary(i) for i in late_fee_candidates],
        "suspension_candidates": [_invoice_summary(i) for i in suspension_candidates],
        "deletion_candidates": [_invoice_summary(i) for i in deletion_candidates],
    }


@router.post("/apply-late-fee/{invoice_id}")
async def apply_late_fee(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    invoice = db.query(models.Invoice).filter_by(id=invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    client = invoice.client
    if client.late_fee_type == models.LateFeeType.none:
        raise HTTPException(status_code=400, detail="Client has no late fee configured")

    if client.late_fee_type == models.LateFeeType.flat:
        fee = Decimal(str(client.late_fee_amount))
    else:
        fee = Decimal(str(invoice.balance_due)) * (Decimal(str(client.late_fee_amount)) / 100)
    fee = fee.quantize(Decimal("0.01"))

    invoice.late_fee_amount = fee
    invoice.total = Decimal(str(invoice.subtotal)) + fee
    invoice.balance_due = invoice.total - Decimal(str(invoice.amount_paid))

    li = models.InvoiceLineItem(
        invoice_id=invoice_id,
        description="Late Fee",
        quantity=1,
        unit_amount=fee,
        amount=fee,
        sort_order=999,
    )
    db.add(li)

    event = models.CollectionsEvent(
        client_id=client.id, invoice_id=invoice_id,
        event_type=models.CollectionsEventType.late_fee_applied,
        performed_by=current_user.full_name,
        notes=f"Late fee ${fee:.2f} applied"
    )
    db.add(event)
    log = models.ActivityLog(
        entity_type="invoice", entity_id=invoice_id, client_id=client.id,
        action="late_fee_applied", performed_by_id=current_user.id,
        performed_by_name=current_user.full_name,
        notes=f"Late fee ${fee:.2f} applied to {invoice.invoice_number}"
    )
    db.add(log)
    db.commit()

    # Send late fee notice email
    if client.email:
        try:
            asyncio.create_task(send_late_fee_notice_email(
                client_email=client.email,
                client_name=client.company_name,
                invoice_number=invoice.invoice_number,
                late_fee=float(fee),
                balance_due=float(invoice.balance_due)
            ))
        except Exception as e:
            print(f"Error sending late fee email: {e}")

    return {"invoice_id": invoice_id, "late_fee": float(fee), "new_total": float(invoice.total)}


@router.post("/update-account-status/{client_id}")
async def update_account_status(
    client_id: int,
    new_status: models.AccountStatus,
    notes: str = "",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    client = db.query(models.Client).filter_by(id=client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    old_status = client.account_status
    client.account_status = new_status

    action_map = {
        models.AccountStatus.suspended: models.CollectionsEventType.suspended,
        models.AccountStatus.deleted: models.CollectionsEventType.deleted,
        models.AccountStatus.active: models.CollectionsEventType.collections_resumed,
    }
    if new_status in action_map:
        db.add(models.CollectionsEvent(
            client_id=client_id,
            event_type=action_map[new_status],
            performed_by=current_user.full_name,
            notes=notes
        ))

    db.add(models.ActivityLog(
        entity_type="client", entity_id=client_id, client_id=client_id,
        action="account_status_changed", performed_by_id=current_user.id,
        performed_by_name=current_user.full_name,
        notes=f"Status: {old_status} → {new_status}. {notes}"
    ))
    db.commit()

    # Send appropriate warning emails
    if client.email:
        try:
            if new_status == models.AccountStatus.suspended and old_status != models.AccountStatus.suspended:
                asyncio.create_task(send_suspension_warning_email(
                    client_email=client.email,
                    client_name=client.company_name
                ))
            elif new_status == models.AccountStatus.deleted and old_status != models.AccountStatus.deleted:
                asyncio.create_task(send_deletion_warning_email(
                    client_email=client.email,
                    client_name=client.company_name
                ))
        except Exception as e:
            print(f"Error sending status change email: {e}")

    return {"client_id": client_id, "old_status": old_status, "new_status": new_status}
