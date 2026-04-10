from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from datetime import date

import models
from database import get_db
from auth import get_current_user

router = APIRouter()


class ExpenseIn(BaseModel):
    expense_date: date
    vendor: str
    description: Optional[str] = None
    amount: float
    category_id: Optional[int] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class CategoryInfo(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class ExpenseOut(BaseModel):
    id: int
    expense_date: date
    vendor: str
    description: Optional[str] = None
    amount: float
    category_id: Optional[int] = None
    category: Optional[CategoryInfo] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/")
def list_expenses(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    category_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.Expense)
    if from_date:
        query = query.filter(models.Expense.expense_date >= from_date)
    if to_date:
        query = query.filter(models.Expense.expense_date <= to_date)
    if category_id:
        query = query.filter_by(category_id=category_id)
    total = query.count()
    expenses = query.order_by(models.Expense.expense_date.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": [ExpenseOut.from_orm(e) for e in expenses]}


@router.post("/", status_code=201)
def create_expense(
    data: ExpenseIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    expense = models.Expense(**data.model_dump(), recorded_by_id=current_user.id)
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.put("/{expense_id}")
def update_expense(
    expense_id: int,
    data: ExpenseIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    from fastapi import HTTPException
    expense = db.query(models.Expense).filter_by(id=expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    for key, value in data.model_dump().items():
        setattr(expense, key, value)
    db.commit()
    db.refresh(expense)
    return expense


@router.delete("/{expense_id}")
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    from fastapi import HTTPException
    expense = db.query(models.Expense).filter_by(id=expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    db.delete(expense)
    db.commit()
    return {"message": "Expense deleted"}
