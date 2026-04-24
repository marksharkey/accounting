# CLAUDE.md — PrecisionPros Accounting System

This document is the authoritative guide for Claude Code working on the PrecisionPros accounting system. It documents the development and production environments, deployment procedures, and constraints.

---

## Environments Overview

| Property | Development (Mac) | Production (VPS) |
|----------|-----------|----------|
| **Frontend** | React + Vite on port 5173 | Static dist/ served by nginx |
| **Backend** | FastAPI/Uvicorn on port 8010 | FastAPI/Uvicorn on 127.0.0.1:8010 |
| **Database** | Local MySQL on localhost:3306 | MySQL on VPS (same server) |
| **Domain** | localhost:5173 | https://accounting.precisionpros.com |
| **Service** | Manual startup (npm/uvicorn) | systemd service: `accounting.service` |
| **URL Pattern** | http://localhost:5173 | https://accounting.precisionpros.com |
| **API Base** | http://localhost:8010/api | https://accounting.precisionpros.com/api |
| **VPS IP** | N/A | 108.61.216.123 |
| **App Path** | ~/accounting | /home/accounting/accounting_program |

---

## Post-Change Verification (REQUIRED)

After making **any** code changes, Claude must always:

1. **Restart affected services** (if backend or frontend code changed):
   - Backend: kill the uvicorn process and restart it; wait for "Application startup complete"
   - Frontend: the Vite dev server hot-reloads automatically; only restart if config files changed
   - Confirm backend is alive: `curl http://localhost:8010/api/health`

2. **Verify the change worked**:
   - Backend route added → confirm it appears in `curl http://localhost:8010/openapi.json`
   - DB migration added → run `alembic upgrade head` and confirm it applied
   - Frontend page/component added → run `npm run build` and confirm no errors

3. **Check nothing broke**:
   - `curl http://localhost:8010/api/health` → `{"status":"ok"}`
   - `npm run build` in `frontend/` → no errors (chunk size warning is expected/pre-existing)
   - Backend log (`/tmp/backend.log`) shows no tracebacks or import errors

**Never report a task as complete without completing these steps.**

---

## Quick Start: Development Environment

### Prerequisites
- Node.js and npm installed
- MySQL running locally (port 3306)
- Python 3 with pip

### First-Time Setup

1. **Configure the database**:
   ```bash
   # Check or create the database
   mysql -u root -e "CREATE DATABASE IF NOT EXISTS precisionpros;"
   mysql -u root -e "CREATE USER IF NOT EXISTS 'ppros'@'localhost' IDENTIFIED BY 'ppros';"
   mysql -u root -e "GRANT ALL PRIVILEGES ON precisionpros.* TO 'ppros'@'localhost';"
   ```

2. **Set up the backend**:
   ```bash
   cd ~/accounting/backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env with your database credentials
   ```

3. **Run migrations**:
   ```bash
   cd ~/accounting/backend
   source venv/bin/activate
   alembic upgrade head
   ```

4. **Set up the frontend**:
   ```bash
   cd ~/accounting/frontend
   npm install
   ```

### Development Startup (each session)

**Terminal 1 — Backend**:
```bash
cd ~/accounting/backend
source venv/bin/activate
uvicorn main:app --port 8010 --reload
```
Runs on http://localhost:8010/api

**Terminal 2 — Frontend**:
```bash
cd ~/accounting/frontend
npm run dev
```
Runs on http://localhost:5173

### Default Dev Credentials
- Username: `mark`
- Password: `mark`

---

## Production Deployment

### ⚠️ CRITICAL CONSTRAINTS

**DO NOT TOUCH — these are live and used by other services**:
- `/home/accounting/games/` — WordPro app (live games)
- `/home/accounting/games_dev/` — ConnectPro app (live games)
- `games.service` — WordPro systemd service
- `connectpro.service` — ConnectPro systemd service
- `/home/accounting/accounting_program/env` — Shared Python env for games
- Existing MySQL databases other than `precisionpros`
- Any pre-existing nginx site configs (read-only)

**Safe to modify**:
- `/home/accounting/accounting_program/` — Our app directory
- `accounting.service` — Our systemd service
- `/etc/nginx/sites-available/accounting.precisionpros.com` — Our nginx config
- `precisionpros` MySQL database and `ppros` user

### Deployment Workflows

**Full Production Deploy** (first-time setup):
See `CLAUDECODE_DEPLOY.md` for complete step-by-step instructions. This is a ~1 hour process covering:
- Database migration
- Clone and backend setup
- Systemd service creation
- Frontend build and transfer
- nginx configuration
- SSL certificate setup

**Quick Deploy — Backend Code Only**:
```bash
ssh root@108.61.216.123
su - accounting
cd /home/accounting/accounting_program
git pull
exit
systemctl restart accounting
```
Verify: `curl https://accounting.precisionpros.com/api/auth/me` should return 401

**Quick Deploy — Frontend Only**:
```bash
# Local Mac
cd ~/accounting/frontend
npm run build
scp -r dist/ root@108.61.216.123:/tmp/accounting_dist

# On server (ssh root@108.61.216.123)
mv /tmp/accounting_dist /home/accounting/accounting_program/frontend/dist
chown -R accounting:accounting /home/accounting/accounting_program/frontend/dist
```
Verify: `https://accounting.precisionpros.com` should load the UI

**Quick Deploy — Database Schema Change**:
```bash
ssh root@108.61.216.123
su - accounting
cd /home/accounting/accounting_program
git pull
source backend/venv/bin/activate
alembic upgrade head
exit
systemctl restart accounting
```

### Deployment Checklist

Before deploying anything to production:

- [ ] Code has been tested locally (dev environment)
- [ ] No `.env` files are being committed
- [ ] Database migrations are in `backend/alembic/versions/`
- [ ] Frontend build completes without errors: `npm run build`
- [ ] Backend starts without errors after `alembic upgrade head`
- [ ] Backend responds to `curl http://localhost:8010/api/auth/me` (should be 401)

After deployment:

- [ ] HTTPS endpoint responds: `curl https://accounting.precisionpros.com`
- [ ] Login still works with valid credentials
- [ ] Both games sites still healthy:
  - `https://games.precisionpros.com` (should return 200)
  - `https://connectpro.precisionpros.com` (should return 200)
- [ ] systemd service is active: `systemctl is-active accounting`

---

## Architecture & Code Organization

### Backend (FastAPI)
- **Path**: `backend/`
- **Entry point**: `backend/main.py`
- **Port**: 8010 (dev) / 127.0.0.1:8010 (prod)
- **Database**: SQLAlchemy ORM, Alembic migrations
- **Auth**: JWT tokens (Bearer in Authorization header)
- **API docs**: http://localhost:8010/api/docs (Swagger) or /api/redoc (ReDoc)

Key modules:
- `main.py` — FastAPI app setup, route registration
- `models/` — SQLAlchemy ORM models
- `routes/` — API endpoints grouped by domain
- `alembic/` — Database migrations
- `requirements.txt` — Python dependencies

### Frontend (React + Vite)
- **Path**: `frontend/`
- **Entry point**: `src/main.jsx`
- **Port**: 5173 (dev)
- **Build output**: `dist/` (production)
- **Auth**: JWT stored in localStorage as `pp_token`

Key modules:
- `src/pages/` — Page components
- `src/components/` — Reusable UI components
- `src/api/` — API client, request interceptors
- `src/store/` — Zustand state management
- `package.json` — npm dependencies

### Database
- **Engine**: MySQL 5.7+ (must support utf8mb4)
- **Charset**: utf8mb4_unicode_ci
- **Dev**: `precisionpros` on localhost:3306
- **Prod**: `precisionpros` on VPS MySQL
- **Migrations**: Alembic (backend/alembic/)

### Authentication
- **Mechanism**: JWT (JSON Web Token)
- **Token field**: `Authorization: Bearer <token>`
- **Token storage (frontend)**: localStorage as `pp_token`
- **Token expiry**: Configured in backend `.env` (SECRET_KEY)
- **Login endpoint**: POST /api/auth/token

---

## Deployment References

### Full deployment procedure
See `CLAUDECODE_DEPLOY.md` for complete, detailed step-by-step instructions.

### Operations and monitoring
See `~/games_dev/OPERATIONS.md` for the shared operations runbook (includes accounting app procedures).

### Quick import/export tools
- Export from dev: `backend/export_database.py`
- Import to dev: `backend/run_full_import.py`

---

## Environment Variables

### Development (.env in backend/)
```
DB_HOST=localhost
DB_PORT=3306
DB_NAME=precisionpros
DB_USER=ppros
DB_PASSWORD=<your_password>
SECRET_KEY=<random_hex_string>
# Optional:
DEBUG=true
SMTP_SERVER=<email_server>
SMTP_PORT=<port>
SMTP_USERNAME=<user>
SMTP_PASSWORD=<password>
```

### Production (.env on VPS)
Same variables as dev, but:
- `SECRET_KEY` must be the **exact same value** as initial deployment (do not regenerate)
- All SMTP settings must be configured for production email
- `DEBUG=false`

**CRITICAL**: The production SECRET_KEY is frozen after initial deployment. If the service is rebuilt, the SECRET_KEY must be restored from backup to keep existing JWT sessions valid.

---

## Important Files & Locations

| File/Dir | Purpose |
|----------|---------|
| `CLAUDECODE_DEPLOY.md` | Full production deployment guide |
| `backend/SETUP_ENV.md` | Dev environment setup instructions |
| `backend/README.md` | Backend quick start |
| `frontend/README.md` | Frontend quick start |
| `backend/.env.example` | Template for environment variables |
| `backend/alembic/` | Database migrations |
| `backend/requirements.txt` | Python dependencies |
| `frontend/package.json` | Node.js dependencies |

---

## When to Consult the Detailed Deployment Guide

See `CLAUDECODE_DEPLOY.md` if you are:
- Deploying to production for the first time
- Setting up a new VPS or fresh environment
- Migrating the entire system
- Recovering from a production failure
- Setting up backup/restore procedures

Use the "Quick Deploy" sections above for regular updates to code or schema.

---

## Troubleshooting

### Backend won't start (dev)
```bash
# Check MySQL is running
mysql -u ppros -p -e "SELECT 1;" precisionpros

# Check .env exists and has correct credentials
cat ~/accounting/backend/.env

# Check Python venv is active
source ~/accounting/backend/venv/bin/activate
python -c "import sys; print(sys.prefix)"

# Try starting with verbose error output
uvicorn main:app --port 8010 --reload
```

### Frontend dev server won't start
```bash
# Check npm/Node are available
node --version && npm --version

# Clear cache and reinstall
cd ~/accounting/frontend
rm -rf node_modules package-lock.json
npm install

# Try starting
npm run dev
```

### Frontend can't reach backend
- Backend must be running on port 8010
- Check `frontend/src/api/client.js` — API base should be `http://localhost:8010`
- Check browser console for CORS errors
- In production: API requests should route through nginx proxy (no CORS headers needed)

### Production deployment issues
1. **nginx -t fails**: Do NOT reload; remove the config and report the error
2. **Service won't start**: Check logs with `journalctl -u accounting -n 50 --no-pager`
3. **Games sites go down**: Immediately remove accounting nginx config, reload, and report
4. **Database import fails**: Do not proceed; restore from backup if available

---

## Git Workflow

### Branches
- **main**: Production code; all commits here are deployable

### Commits
- Make small, focused commits
- Write clear commit messages explaining the "why"
- Never commit `.env` files or credentials

### Before Pushing
- Test locally (dev environment)
- Run any tests: `npm run test` (frontend) or `pytest` (backend)
- Verify database migrations work: `alembic upgrade head`
- Verify the build works: `npm run build` (frontend)

### After Merging to main
- Production can be deployed at any time
- Use the Quick Deploy procedures above for updates

---

## Security Notes

- **Never commit `.env` files**: They contain credentials
- **JWT tokens are sensitive**: Stored in localStorage; be careful with XSS
- **Database password**: Stored in .env; protect access to servers
- **Production SECRET_KEY**: Do not change after initial deployment; sessions will break
- **SSL certificate**: Auto-renewed by certbot on VPS; monitor renewal logs

---

## Support & Escalation

If you encounter:
- **Deployment failures**: Check `CLAUDECODE_DEPLOY.md` step-by-step; report the exact error
- **Unknown errors**: Check logs (dev: stdout; prod: `journalctl -u accounting`)
- **Something affects games services**: **STOP IMMEDIATELY** and report — do not continue
- **Git/auth failures**: Likely a credentials or repo-access issue; report

---

*Last updated: 2026-04-24*
*Architecture: React (frontend) + FastAPI (backend) + MySQL (database)*
*Deployment: systemd service on VPS with nginx reverse proxy and SSL*
