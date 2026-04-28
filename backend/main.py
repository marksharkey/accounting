from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from pathlib import Path

from config import get_settings
from database import get_db, engine
import models
from auth import authenticate_user, create_access_token, get_current_user, get_password_hash
from routers import clients, services, invoices, payments, expenses, journal_entries, reports, collections, credit_memos, company_info, email_templates, domains, bank_transactions, users, auth_recovery, qbo_auth

settings = get_settings()

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://accounting.precisionpros.com",
        "http://accounting.precisionpros.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/auth/token")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {"id": user.id, "username": user.username, "full_name": user.full_name}
    }


@app.get("/api/auth/me")
async def get_me(current_user: models.User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "is_admin": current_user.is_admin,
    }


app.include_router(clients.router,        prefix="/api/clients",        tags=["Clients"])
app.include_router(services.router,       prefix="/api/services",       tags=["Service Catalog"])
app.include_router(invoices.router,       prefix="/api/invoices",       tags=["Invoices"])
app.include_router(credit_memos.router,   prefix="/api/credit-memos",   tags=["Credit Memos"])
app.include_router(payments.router,       prefix="/api/payments",       tags=["Payments"])
app.include_router(expenses.router,       prefix="/api/expenses",       tags=["Expenses"])
app.include_router(journal_entries.router, prefix="/api/journal-entries", tags=["Journal Entries"])
app.include_router(reports.router,        prefix="/api/reports",        tags=["Reports"])
app.include_router(collections.router,    prefix="/api/collections",    tags=["Collections"])
app.include_router(company_info.router,   prefix="/api/company-info",   tags=["Company Info"])
app.include_router(domains.router,        prefix="/api/domains",        tags=["Domains"])
app.include_router(email_templates.router, tags=["Email Templates"])
app.include_router(bank_transactions.router, prefix="/api/bank", tags=["Bank Transactions"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(auth_recovery.router, prefix="/api/auth", tags=["Auth Recovery"])
app.include_router(qbo_auth.router)

# Mount static files for uploads
uploads_dir = Path("uploads")
uploads_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}
