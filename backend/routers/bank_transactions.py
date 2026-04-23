from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from datetime import date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel
import models
from database import get_db
from auth import get_current_user

router = APIRouter()


class BankAccountOut(BaseModel):
    id: int
    account_name: str
    account_number: Optional[str]
    account_type: str
    opening_balance: Decimal
    is_active: bool

    class Config:
        from_attributes = True


class BankTransactionOut(BaseModel):
    id: int
    bank_account_id: int
    transaction_date: date
    transaction_type: str
    transaction_number: Optional[str]
    description: Optional[str]
    gl_account: Optional[str]
    amount: Decimal
    balance: Optional[Decimal]
    reconciled: bool
    matched_payment_id: Optional[int]

    class Config:
        from_attributes = True


class BankTransactionIn(BaseModel):
    transaction_date: date
    transaction_type: str
    amount: float
    description: Optional[str] = None
    transaction_number: Optional[str] = None
    gl_account: Optional[str] = None


class BankTransactionUpdate(BaseModel):
    transaction_date: Optional[date] = None
    transaction_type: Optional[str] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    transaction_number: Optional[str] = None
    gl_account: Optional[str] = None


class BankReconciliationOut(BaseModel):
    id: int
    bank_account_id: int
    reconciliation_date: date
    statement_balance: Decimal
    cleared_amount: Decimal
    difference: Decimal
    is_complete: bool
    notes: Optional[str]

    class Config:
        from_attributes = True


@router.get("/bank-accounts")
def list_bank_accounts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List all bank accounts."""
    accounts = db.query(models.BankAccount).filter_by(is_active=True).all()
    return accounts


@router.post("/bank-accounts")
def create_bank_account(
    account_name: str,
    account_type: str = "Checking",
    account_number: Optional[str] = None,
    opening_balance: Decimal = Decimal("0.00"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new bank account."""
    account = models.BankAccount(
        account_name=account_name,
        account_type=account_type,
        account_number=account_number,
        opening_balance=opening_balance,
        is_active=True
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.post("/transactions/{account_id}")
def create_transaction(
    account_id: int,
    data: BankTransactionIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a manual bank transaction entry."""
    account = db.query(models.BankAccount).filter_by(id=account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")

    # Map string transaction_type to enum
    try:
        txn_type = models.TransactionType[data.transaction_type.lower()]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transaction type. Must be one of: {', '.join([t.value for t in models.TransactionType])}"
        )

    transaction = models.BankTransaction(
        bank_account_id=account_id,
        transaction_date=data.transaction_date,
        transaction_type=txn_type,
        transaction_number=data.transaction_number,
        description=data.description,
        gl_account=data.gl_account,
        amount=Decimal(str(data.amount)),
        reconciled=False,
        import_batch='manual_entry'
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("/check-register/{account_id}")
def get_check_register(
    account_id: int,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    transaction_type: Optional[str] = None,
    reconciled_only: bool = False,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get check register for a bank account."""
    account = db.query(models.BankAccount).filter_by(id=account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")

    query = db.query(models.BankTransaction).filter_by(bank_account_id=account_id)

    if from_date:
        query = query.filter(models.BankTransaction.transaction_date >= from_date)
    if to_date:
        query = query.filter(models.BankTransaction.transaction_date <= to_date)
    if transaction_type:
        query = query.filter(models.BankTransaction.transaction_type == transaction_type)
    if reconciled_only:
        query = query.filter(models.BankTransaction.reconciled == True)

    total = query.count()
    transactions = query.order_by(
        desc(models.BankTransaction.transaction_date),
        desc(models.BankTransaction.id)
    ).offset(skip).limit(limit).all()

    return {
        "account": account,
        "total": total,
        "items": transactions
    }


@router.get("/transactions/{transaction_id}")
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get a single transaction."""
    txn = db.query(models.BankTransaction).filter_by(id=transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn


@router.put("/transactions/{transaction_id}/reconcile")
def toggle_transaction_reconciled(
    transaction_id: int,
    reconciled: bool,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Toggle reconciliation status of a transaction."""
    txn = db.query(models.BankTransaction).filter_by(id=transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    txn.reconciled = reconciled
    db.commit()
    db.refresh(txn)
    return txn


@router.put("/transactions/{transaction_id}")
def update_transaction(
    transaction_id: int,
    data: BankTransactionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update a bank transaction."""
    txn = db.query(models.BankTransaction).filter_by(id=transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Update only provided fields
    if data.transaction_date is not None:
        txn.transaction_date = data.transaction_date
    if data.transaction_type is not None:
        try:
            txn.transaction_type = models.TransactionType[data.transaction_type.lower()]
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid transaction type. Must be one of: {', '.join([t.value for t in models.TransactionType])}"
            )
    if data.amount is not None:
        txn.amount = Decimal(str(data.amount))
    if data.description is not None:
        txn.description = data.description
    if data.transaction_number is not None:
        txn.transaction_number = data.transaction_number
    if data.gl_account is not None:
        txn.gl_account = data.gl_account

    db.commit()
    db.refresh(txn)
    return txn


@router.delete("/transactions/{transaction_id}")
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Delete a bank transaction."""
    txn = db.query(models.BankTransaction).filter_by(id=transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(txn)
    db.commit()
    return {"status": "deleted", "transaction_id": transaction_id}


@router.post("/reconciliations/{account_id}")
def create_reconciliation(
    account_id: int,
    statement_balance: Decimal,
    reconciliation_date: date,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Start a new bank reconciliation."""
    account = db.query(models.BankAccount).filter_by(id=account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")

    reconciliation = models.BankReconciliation(
        bank_account_id=account_id,
        reconciliation_date=reconciliation_date,
        statement_balance=statement_balance,
        cleared_amount=Decimal("0.00"),
        difference=statement_balance,
        is_complete=False,
        notes=notes
    )
    db.add(reconciliation)
    db.commit()
    db.refresh(reconciliation)
    return reconciliation


@router.get("/reconciliations/{account_id}")
def get_reconciliations(
    account_id: int,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get reconciliations for an account."""
    account = db.query(models.BankAccount).filter_by(id=account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")

    reconciliations = db.query(models.BankReconciliation).filter_by(
        bank_account_id=account_id
    ).order_by(desc(models.BankReconciliation.reconciliation_date)).offset(skip).limit(limit).all()

    return reconciliations


@router.put("/reconciliations/{reconciliation_id}/complete")
def complete_reconciliation(
    reconciliation_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Mark reconciliation as complete."""
    reconciliation = db.query(models.BankReconciliation).filter_by(id=reconciliation_id).first()
    if not reconciliation:
        raise HTTPException(status_code=404, detail="Reconciliation not found")

    # Calculate cleared amount from reconciled transactions
    cleared_txns = db.query(models.BankTransaction).filter(
        models.BankTransaction.bank_account_id == reconciliation.bank_account_id,
        models.BankTransaction.transaction_date <= reconciliation.reconciliation_date,
        models.BankTransaction.reconciled == True
    ).all()

    cleared_amount = sum(Decimal(str(t.amount)) for t in cleared_txns)
    difference = reconciliation.statement_balance - cleared_amount

    reconciliation.cleared_amount = cleared_amount
    reconciliation.difference = difference
    reconciliation.is_complete = True

    db.commit()
    db.refresh(reconciliation)
    return reconciliation


@router.get("/reconciliations/{reconciliation_id}/summary")
def get_reconciliation_summary(
    reconciliation_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get reconciliation summary with cleared and uncleared items."""
    reconciliation = db.query(models.BankReconciliation).filter_by(id=reconciliation_id).first()
    if not reconciliation:
        raise HTTPException(status_code=404, detail="Reconciliation not found")

    # Get all transactions up to reconciliation date
    txns = db.query(models.BankTransaction).filter(
        models.BankTransaction.bank_account_id == reconciliation.bank_account_id,
        models.BankTransaction.transaction_date <= reconciliation.reconciliation_date
    ).order_by(models.BankTransaction.transaction_date).all()

    cleared = [t for t in txns if t.reconciled]
    uncleared = [t for t in txns if not t.reconciled]

    cleared_amount = sum(Decimal(str(t.amount)) for t in cleared)
    uncleared_amount = sum(Decimal(str(t.amount)) for t in uncleared)

    return {
        "reconciliation": reconciliation,
        "cleared_transactions": {
            "count": len(cleared),
            "amount": cleared_amount,
            "items": cleared
        },
        "uncleared_transactions": {
            "count": len(uncleared),
            "amount": uncleared_amount,
            "items": uncleared
        },
        "statement_balance": reconciliation.statement_balance,
        "calculated_balance": cleared_amount,
        "difference": reconciliation.statement_balance - cleared_amount
    }
