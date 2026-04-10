from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from config import get_settings
from database import get_db, engine
import models
from auth import authenticate_user, create_access_token, get_current_user, get_password_hash
from routers import clients, services, invoices, payments, expenses, reports, collections

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
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
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
    }


app.include_router(clients.router,     prefix="/api/clients",     tags=["Clients"])
app.include_router(services.router,    prefix="/api/services",    tags=["Service Catalog"])
app.include_router(invoices.router,    prefix="/api/invoices",    tags=["Invoices"])
app.include_router(payments.router,    prefix="/api/payments",    tags=["Payments"])
app.include_router(expenses.router,    prefix="/api/expenses",    tags=["Expenses"])
app.include_router(reports.router,     prefix="/api/reports",     tags=["Reports"])
app.include_router(collections.router, prefix="/api/collections", tags=["Collections"])


@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}


@app.post("/api/setup/init-users", include_in_schema=False)
def init_users(db: Session = Depends(get_db)):
    """One-time setup only — remove after first run."""
    users_data = [
        {"username": "mark", "full_name": "Mark Sharkey", "email": "mark@precisionpros.com", "password": "mark"},
        {"username": "candace", "full_name": "Candace Sharkey", "email": "candace@precisionpros.com", "password": "candace"},
    ]
    created = []
    for u in users_data:
        if not db.query(models.User).filter_by(username=u["username"]).first():
            db.add(models.User(
                username=u["username"],
                full_name=u["full_name"],
                email=u["email"],
                hashed_password=get_password_hash(u["password"]),
            ))
            created.append(u["username"])
    db.commit()
    return {"created": created, "message": "Change passwords immediately and remove this endpoint."}
