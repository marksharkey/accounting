from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import date, timedelta
import csv
import io

import models
from database import get_db
from auth import get_current_user
from config import get_settings

router = APIRouter()


class DomainBase(BaseModel):
    domain_name: str
    client_id: int
    registrar: models.Registrar
    expiration_date: date
    renewal_cost: float = 25.00
    auto_renew: bool = False
    notes: Optional[str] = None


class CloudflareCredentials(BaseModel):
    api_key: str
    email: str
    account_id: str


class DomainResponse(DomainBase):
    id: int
    cloudflare_id: Optional[str] = None
    created_at: str
    updated_at: str
    client: dict

    class Config:
        from_attributes = True


@router.get("/")
def list_domains(
    client_id: Optional[int] = None,
    registrar: Optional[str] = None,
    days_until_expiry: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List domains with optional filtering.

    days_until_expiry: if set, only return domains expiring within N days
    """
    query = db.query(models.Domain)

    if client_id:
        query = query.filter(models.Domain.client_id == client_id)

    if registrar:
        query = query.filter(models.Domain.registrar == registrar)

    domains = query.order_by(models.Domain.expiration_date).all()

    if days_until_expiry:
        from datetime import datetime, timedelta
        cutoff = datetime.now().date() + timedelta(days=days_until_expiry)
        domains = [d for d in domains if d.expiration_date <= cutoff]

    items = []
    for d in domains:
        item = {k: v for k, v in d.__dict__.items() if not k.startswith('_')}
        if d.client:
            item["client"] = {"id": d.client.id, "company_name": d.client.company_name}
        else:
            item["client"] = None
        items.append(item)

    return {
        "total": len(domains),
        "items": items
    }


@router.get("/{domain_id}")
def get_domain(
    domain_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    domain = db.query(models.Domain).filter_by(id=domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    result = {k: v for k, v in domain.__dict__.items() if not k.startswith('_')}
    if domain.client:
        result["client"] = {"id": domain.client.id, "company_name": domain.client.company_name}
    else:
        result["client"] = None
    return result


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_domain(
    data: DomainBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Check domain doesn't already exist
    existing = db.query(models.Domain).filter_by(domain_name=data.domain_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Domain already exists")

    # Check client exists
    client = db.query(models.Client).filter_by(id=data.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    domain = models.Domain(**data.model_dump())
    db.add(domain)
    db.commit()
    db.refresh(domain)

    result = {k: v for k, v in domain.__dict__.items() if not k.startswith('_')}
    if domain.client:
        result["client"] = {"id": domain.client.id, "company_name": domain.client.company_name}
    else:
        result["client"] = None
    return result


@router.put("/{domain_id}")
def update_domain(
    domain_id: int,
    data: DomainBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    domain = db.query(models.Domain).filter_by(id=domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    for key, value in data.model_dump().items():
        setattr(domain, key, value)

    db.commit()
    db.refresh(domain)

    result = {k: v for k, v in domain.__dict__.items() if not k.startswith('_')}
    if domain.client:
        result["client"] = {"id": domain.client.id, "company_name": domain.client.company_name}
    else:
        result["client"] = None
    return result


@router.delete("/{domain_id}", status_code=204)
def delete_domain(
    domain_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    domain = db.query(models.Domain).filter_by(id=domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    db.delete(domain)
    db.commit()


@router.post("/import/csv")
def import_domains_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Import domains from CSV file.

    CSV format: domain_name, client_name, registrar, expiration_date, renewal_cost (optional)
    Dates should be in YYYY-MM-DD format.
    """
    try:
        contents = file.file.read().decode('utf-8')
        reader = csv.reader(io.StringIO(contents))

        imported = 0
        skipped = 0
        errors = []

        for row_num, row in enumerate(reader, 1):
            if row_num == 1:  # Skip header
                continue

            if len(row) < 4:
                errors.append(f"Row {row_num}: Missing fields")
                skipped += 1
                continue

            domain_name = row[0].strip().lower()
            client_name = row[1].strip()
            registrar = row[2].strip().lower()
            expiration_str = row[3].strip()
            renewal_cost = float(row[4]) if len(row) > 4 and row[4].strip() else 25.00

            try:
                expiration_date = date.fromisoformat(expiration_str)
            except ValueError:
                errors.append(f"Row {row_num}: Invalid date format (use YYYY-MM-DD)")
                skipped += 1
                continue

            # Find client
            client = db.query(models.Client).filter(
                models.Client.company_name.ilike(client_name)
            ).first()

            if not client:
                errors.append(f"Row {row_num}: Client '{client_name}' not found")
                skipped += 1
                continue

            # Map registrar string to enum
            registrar_map = {
                'cloudflare': models.Registrar.cloudflare,
                'godaddy': models.Registrar.godaddy,
                'hosting.com': models.Registrar.hosting_com,
                'other': models.Registrar.other,
            }

            if registrar not in registrar_map:
                errors.append(f"Row {row_num}: Unknown registrar '{registrar}'")
                skipped += 1
                continue

            # Check if domain already exists
            existing = db.query(models.Domain).filter_by(domain_name=domain_name).first()
            if existing:
                errors.append(f"Row {row_num}: Domain '{domain_name}' already exists")
                skipped += 1
                continue

            # Create domain
            domain = models.Domain(
                domain_name=domain_name,
                client_id=client.id,
                registrar=registrar_map[registrar],
                expiration_date=expiration_date,
                renewal_cost=renewal_cost,
            )
            db.add(domain)
            imported += 1

        db.commit()

        return {
            "imported": imported,
            "skipped": skipped,
            "errors": errors,
            "message": f"Imported {imported} domains"
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")


@router.post("/cloudflare/test")
def test_cloudflare_credentials(
    creds: CloudflareCredentials,
    save: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Test Cloudflare API credentials by fetching account info.

    If save=true and test passes, save credentials to .env file.
    """
    try:
        import requests
        from pathlib import Path

        headers = {
            "X-Auth-Key": creds.api_key,
            "X-Auth-Email": creds.email,
            "Content-Type": "application/json"
        }

        # Test by fetching account details
        url = f"https://api.cloudflare.com/client/v4/accounts/{creds.account_id}"
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            raise Exception(f"API returned {response.status_code}: {response.text}")

        data = response.json()
        if not data.get("success"):
            raise Exception(f"Cloudflare error: {data.get('errors', 'Unknown error')}")

        account = data.get("result", {})

        # Save to .env if requested
        if save:
            _save_cloudflare_to_env(creds)

        return {
            "success": True,
            "message": "Credentials valid",
            "saved": save,
            "account_id": account.get("id"),
            "account_name": account.get("name"),
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cloudflare test failed: {str(e)}")


def _save_cloudflare_to_env(creds: CloudflareCredentials):
    """Save Cloudflare credentials to .env file."""
    from pathlib import Path

    env_path = Path(__file__).parent.parent / ".env"

    # Read existing .env
    env_lines = []
    if env_path.exists():
        with open(env_path, 'r') as f:
            env_lines = f.readlines()

    # Keys to update
    keys_to_update = {
        'CLOUDFLARE_API_KEY': creds.api_key,
        'CLOUDFLARE_API_EMAIL': creds.email,
        'CLOUDFLARE_ACCOUNT_ID': creds.account_id,
    }

    # Update existing keys or mark for addition
    updated_keys = set()
    for i, line in enumerate(env_lines):
        for key, value in keys_to_update.items():
            if line.strip().startswith(f"{key}="):
                env_lines[i] = f"{key}={value}\n"
                updated_keys.add(key)
                break

    # Add missing keys
    for key, value in keys_to_update.items():
        if key not in updated_keys:
            env_lines.append(f"{key}={value}\n")

    # Write back
    with open(env_path, 'w') as f:
        f.writelines(env_lines)


@router.post("/sync/cloudflare")
def sync_cloudflare_domains(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    settings=Depends(get_settings),
    creds: Optional[CloudflareCredentials] = None
):
    """Sync domains from Cloudflare account.

    Can use credentials from request body or .env (CLOUDFLARE_API_KEY, CLOUDFLARE_API_EMAIL, CLOUDFLARE_ACCOUNT_ID).
    For domains not found in local DB, will create placeholder entries (client_id=null initially).
    """
    # Use provided credentials or fall back to .env
    api_key = creds.api_key if creds else settings.cloudflare_api_key
    email = creds.email if creds else settings.cloudflare_api_email
    account_id = creds.account_id if creds else settings.cloudflare_account_id

    if not api_key or not email or not account_id:
        raise HTTPException(
            status_code=400,
            detail="Cloudflare credentials not configured. Add CLOUDFLARE_API_KEY, CLOUDFLARE_API_EMAIL, and CLOUDFLARE_ACCOUNT_ID to .env, or pass credentials in request."
        )

    try:
        import requests
        from datetime import datetime, timedelta

        # Get domains from Cloudflare API
        headers = {
            "X-Auth-Key": api_key,
            "X-Auth-Email": email,
            "Content-Type": "application/json"
        }

        # List domain registrations through Cloudflare Registrar
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/registrar/registrations"
        domains_data = []
        cursor = None
        per_page = 50

        while True:
            params = {"per_page": per_page}
            if cursor:
                params["cursor"] = cursor

            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code != 200:
                raise Exception(f"Cloudflare API error: {response.text}")

            data = response.json()
            if not data.get("success"):
                raise Exception(f"Cloudflare error: {data.get('errors', 'Unknown error')}")

            page_results = data.get("result", [])
            if not page_results:
                break

            domains_data.extend(page_results)

            # Check for next page cursor
            result_info = data.get("result_info", {})
            cursor = result_info.get("cursor")

            if not cursor:
                break


        imported = 0
        updated = 0
        skipped = 0

        for cf_domain in domains_data:
            domain_name = cf_domain.get("domain_name")
            expiration_str = cf_domain.get("expires_at")

            if not domain_name or not expiration_str:
                skipped += 1
                continue

            try:
                expiration_date = datetime.fromisoformat(expiration_str.replace('Z', '+00:00')).date()
            except Exception as e:
                skipped += 1
                continue

            # Check if domain exists locally
            existing = db.query(models.Domain).filter_by(domain_name=domain_name.lower()).first()

            try:
                if existing:
                    # Update existing domain
                    existing.expiration_date = expiration_date
                    existing.auto_renew = cf_domain.get("auto_renew", False)
                    existing.cloudflare_id = cf_domain.get("id")
                    db.commit()
                    updated += 1
                else:
                    # Create new domain entry (client_id will need to be assigned manually)
                    domain = models.Domain(
                        domain_name=domain_name.lower(),
                        client_id=None,  # Will need to be set manually
                        registrar=models.Registrar.cloudflare,
                        expiration_date=expiration_date,
                        cloudflare_id=cf_domain.get("id"),
                        auto_renew=cf_domain.get("auto_renew", False),
                        notes="Imported from Cloudflare - client_id needs to be assigned"
                    )
                    db.add(domain)
                    db.commit()
                    imported += 1
            except Exception as e:
                # Skip if duplicate or other constraint error
                db.rollback()
                skipped += 1
                continue

        return {
            "imported": imported,
            "updated": updated,
            "skipped": skipped,
            "total": len(domains_data),
            "message": f"Synced {imported + updated} Cloudflare domains"
        }

    except Exception as e:
        error_msg = str(e)
        print(f"SYNC ERROR: {error_msg}")
        raise HTTPException(status_code=400, detail=f"Cloudflare sync failed: {error_msg}")


@router.get("/scheduling/unscheduled")
def get_unscheduled_domains_with_recommendations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get unscheduled domains with recommended billing schedule info."""
    # Find domains not in any billing schedule
    scheduled_domain_ids = db.query(models.BillingScheduleLineItem.domain_id).filter(
        models.BillingScheduleLineItem.domain_id != None
    ).all()
    scheduled_ids = set(d[0] for d in scheduled_domain_ids)

    query = db.query(models.Domain)
    if scheduled_ids:
        query = query.filter(~models.Domain.id.in_(scheduled_ids))

    unscheduled = query.order_by(models.Domain.expiration_date).all()

    recommendations = []
    for domain in unscheduled:
        if not domain.client_id:
            continue

        client = domain.client
        # Calculate due date: 60 days before expiration
        invoice_due_date = domain.expiration_date - timedelta(days=60)

        # Round down to 1st of month (invoice due dates are always 1st)
        if invoice_due_date.day != 1:
            if invoice_due_date.month == 12:
                invoice_due_date = invoice_due_date.replace(year=invoice_due_date.year + 1, month=1, day=1)
            else:
                invoice_due_date = invoice_due_date.replace(month=invoice_due_date.month + 1, day=1)

        # Check if client has existing annual schedule near this date
        existing_schedules = db.query(models.BillingSchedule).filter(
            models.BillingSchedule.client_id == domain.client_id,
            models.BillingSchedule.is_active == True,
            models.BillingSchedule.cycle == models.BillingCycle.annual
        ).all()

        recommended_schedule = None
        for sched in existing_schedules:
            if sched.next_bill_date <= invoice_due_date:
                recommended_schedule = {
                    "schedule_id": sched.id,
                    "cycle": "annual",
                    "action": "add_to_existing"
                }
                break

        if not recommended_schedule:
            recommended_schedule = {
                "schedule_id": None,
                "cycle": "annual",
                "action": "create_new"
            }

        recommendations.append({
            "domain_id": domain.id,
            "domain_name": domain.domain_name,
            "expiration_date": domain.expiration_date.isoformat(),
            "renewal_cost": float(domain.renewal_cost),
            "client_id": domain.client_id,
            "client_name": client.company_name if client else None,
            "recommended_due_date": invoice_due_date.isoformat(),
            "recommended_schedule": recommended_schedule,
        })

    return {"unscheduled_count": len(recommendations), "domains": recommendations}


class BatchScheduleRequest(BaseModel):
    domain_ids: List[int]


@router.post("/scheduling/batch-schedule")
def batch_schedule_domains(
    request: BatchScheduleRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Schedule multiple domains to their recommended billing schedules."""
    from decimal import Decimal

    results = {
        "scheduled": [],
        "failed": [],
        "created_schedules": []
    }

    for domain_id in request.domain_ids:
        try:
            domain = db.query(models.Domain).filter_by(id=domain_id).first()
            if not domain or not domain.client_id:
                results["failed"].append({"domain_id": domain_id, "reason": "Domain or client not found"})
                continue

            # Calculate invoice due date
            invoice_due_date = domain.expiration_date - timedelta(days=60)
            if invoice_due_date.day != 1:
                if invoice_due_date.month == 12:
                    invoice_due_date = invoice_due_date.replace(year=invoice_due_date.year + 1, month=1, day=1)
                else:
                    invoice_due_date = invoice_due_date.replace(month=invoice_due_date.month + 1, day=1)

            # Find or create annual schedule for this specific due date
            schedule = db.query(models.BillingSchedule).filter(
                models.BillingSchedule.client_id == domain.client_id,
                models.BillingSchedule.is_active == True,
                models.BillingSchedule.cycle == models.BillingCycle.annual,
                models.BillingSchedule.next_bill_date == invoice_due_date
            ).first()

            if not schedule:
                # Create new annual schedule with this domain's due date
                schedule = models.BillingSchedule(
                    client_id=domain.client_id,
                    cycle=models.BillingCycle.annual,
                    next_bill_date=invoice_due_date,
                    autocc_recurring=domain.client.autocc_recurring if domain.client else False,
                    amount=0,
                    notes=f"Domain renewal - due {invoice_due_date.isoformat()}"
                )
                db.add(schedule)
                db.flush()
                results["created_schedules"].append({
                    "client_id": domain.client_id,
                    "due_date": invoice_due_date.isoformat(),
                    "schedule_id": schedule.id
                })

            # Add domain as line item
            line_item = models.BillingScheduleLineItem(
                billing_schedule_id=schedule.id,
                domain_id=domain.id,
                description=f"Domain renewal: {domain.domain_name}",
                quantity=1,
                unit_amount=Decimal(str(domain.renewal_cost)),
                amount=Decimal(str(domain.renewal_cost)),
                sort_order=0
            )
            db.add(line_item)

            results["scheduled"].append({
                "domain_id": domain_id,
                "domain_name": domain.domain_name,
                "schedule_id": schedule.id,
                "due_date": invoice_due_date.isoformat()
            })

        except Exception as e:
            results["failed"].append({"domain_id": domain_id, "reason": str(e)})

    # Update all schedule amounts based on their line items
    unique_schedules = set(r["schedule_id"] for r in results["scheduled"])
    for schedule_id in unique_schedules:
        schedule = db.query(models.BillingSchedule).filter_by(id=schedule_id).first()
        if schedule:
            schedule.amount = sum(
                Decimal(str(item.quantity)) * Decimal(str(item.unit_amount))
                for item in schedule.line_items
            )

    db.commit()
    return results
