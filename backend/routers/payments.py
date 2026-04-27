from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, field_validator
from datetime import date
from decimal import Decimal
import asyncio

import models
from database import get_db
from auth import get_current_user
from services.email import send_receipt_email
from services.journal import post_journal_entries, reverse_journal_entries

router = APIRouter()


class PaymentIn(BaseModel):
    invoice_id: int
    payment_date: date
    amount: float
    method: models.PaymentMethod
    reference_number: Optional[str] = None
    notes: Optional[str] = None

    @field_validator('invoice_id')
    @classmethod
    def invoice_id_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Invoice ID must be greater than 0')
        return v

    @field_validator('amount')
    @classmethod
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Payment amount must be greater than 0')
        return v


@router.post("/", status_code=201)
async def record_payment(
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

    # Create journal entries for payment
    journal_entries = [
        {
            'date': data.payment_date,
            'code': '1000',
            'name': 'Cash - Chase Checking',
            'debit': Decimal(str(data.amount)),
            'credit': Decimal('0'),
            'description': f'Payment for {invoice.invoice_number} — {client.company_name}',
            'reference': invoice.invoice_number,
            'source': 'payment'
        },
        {
            'date': data.payment_date,
            'code': '1200',
            'name': 'Accounts Receivable',
            'debit': Decimal('0'),
            'credit': Decimal(str(data.amount)),
            'description': f'Payment for {invoice.invoice_number} — {client.company_name}',
            'reference': invoice.invoice_number,
            'source': 'payment'
        }
    ]
    post_journal_entries(db, journal_entries)

    # Automatically create corresponding bank transaction in Chase Checking
    chase_checking = db.query(models.BankAccount).filter_by(account_name='Chase Checking').first()
    if chase_checking:
        bank_txn = models.BankTransaction(
            bank_account_id=chase_checking.id,
            transaction_date=data.payment_date,
            transaction_type=models.TransactionType.payment,
            description=client.company_name,
            gl_account='Accounts Receivable',
            amount=Decimal(str(data.amount)),  # Positive amount for deposit
            matched_payment_id=payment.id,
            reconciled=False,
            import_batch='manual_entry'
        )
        db.add(bank_txn)

    db.commit()
    db.refresh(payment)

    # Send receipt email
    if client.email:
        try:
            asyncio.create_task(send_receipt_email(payment, invoice, client))
        except Exception as e:
            print(f"Error sending receipt email: {e}")

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


@router.delete("/{payment_id}")
def delete_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    payment = db.query(models.Payment).filter_by(id=payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    invoice = db.query(models.Invoice).filter_by(id=payment.invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    client = db.query(models.Client).filter_by(id=payment.client_id).first()

    # Delete associated bank transaction
    db.query(models.BankTransaction).filter_by(matched_payment_id=payment_id).delete()

    # Update client balance
    if client:
        client.account_balance = Decimal(str(client.account_balance)) + Decimal(str(payment.amount))

    # Recalculate invoice status
    remaining_payments = db.query(models.Payment).filter_by(invoice_id=invoice.id).filter(
        models.Payment.id != payment_id
    ).all()
    total_paid = sum(Decimal(str(p.amount)) for p in remaining_payments)
    invoice.amount_paid = total_paid
    invoice.balance_due = Decimal(str(invoice.total)) - total_paid

    if invoice.balance_due >= invoice.total:
        invoice.status = models.InvoiceStatus.sent
    elif total_paid > 0:
        invoice.status = models.InvoiceStatus.partially_paid
    else:
        invoice.status = models.InvoiceStatus.sent

    # Log the action
    log = models.ActivityLog(
        entity_type="payment", entity_id=payment_id, client_id=payment.client_id,
        action="payment_deleted", performed_by_id=current_user.id,
        performed_by_name=current_user.full_name,
        notes=f"${payment.amount:.2f} via {payment.method.value} — Invoice {invoice.invoice_number}"
    )
    db.add(log)

    # Reverse journal entries for the payment
    reverse_journal_entries(db, invoice.invoice_number, "payment")

    db.delete(payment)
    db.commit()

    return {"status": "deleted", "payment_id": payment_id}
