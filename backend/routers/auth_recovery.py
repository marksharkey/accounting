"""Password and account recovery endpoints."""
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import User
from auth import get_password_hash
from services.email import send_forgot_username_email, send_password_reset_email

router = APIRouter()


class ForgotUsernameRequest(BaseModel):
    email: str


class ForgotPasswordRequest(BaseModel):
    email_or_username: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/forgot-username")
async def forgot_username(request: ForgotUsernameRequest, db: Session = Depends(get_db)):
    """
    Request username reminder via email.
    Returns vague success message to prevent user enumeration.
    """
    user = db.query(User).filter(User.email == request.email).first()

    if user and user.is_active:
        await send_forgot_username_email(user)

    # Always return same message regardless of whether user exists
    return {"message": "If that email is registered, your username has been sent."}


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Request password reset link via email.
    Accepts either email or username.
    Returns vague success message to prevent user enumeration.
    """
    user = db.query(User).filter(
        (User.email == request.email_or_username) | (User.username == request.email_or_username)
    ).first()

    if user and user.is_active:
        # Generate reset token
        token = secrets.token_urlsafe(32)
        expiry = datetime.utcnow() + timedelta(hours=1)

        user.reset_token = token
        user.reset_token_expiry = expiry
        db.commit()

        await send_password_reset_email(user, token)

    # Always return same message regardless of whether user exists
    return {"message": "If that account exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Reset password using reset token.
    Token must be valid and not expired.
    """
    user = db.query(User).filter(User.reset_token == request.token).first()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link.")

    # Check token expiry
    if user.reset_token_expiry < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired reset link.")

    # Update password and clear reset token
    user.hashed_password = get_password_hash(request.new_password)
    user.reset_token = None
    user.reset_token_expiry = None
    db.commit()

    return {"message": "Password updated successfully."}
