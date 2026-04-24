# PrecisionPros Accounting — Production Deployment Prompt

## Your job
Deploy the PrecisionPros accounting app to the production VPS so it runs at
`accounting.precisionpros.com`. Execute every step yourself. Do not ask me to
do anything that you are capable of doing. If a step fails, stop and report
the full error — do not attempt workarounds that could affect other services.

---

## CRITICAL — DO NOT TOUCH THESE (live games in production use)

These paths, services, and configs are **completely off-limits**. Do not read,
modify, restart, or interact with them in any way for any reason:

| What | Location |
|------|----------|
| WordPro app files | `/home/accounting/games/` |
| ConnectPro app files | `/home/accounting/games_dev/` |
| WordPro service | `games.service` |
| ConnectPro service | `connectpro.service` |
| Shared Python env | `/home/accounting/accounting_program/env` |
| Existing nginx site configs | Any pre-existing file in `/etc/nginx/sites-available/` (read only to understand structure, never edit) |
| Games databases | Any existing MySQL database other than `precisionpros` |

If any step would require touching any of the above, **stop and tell me** instead
of proceeding.

### Safe shared resources (handle with care)
- **nginx**: You may ADD a new config file only. Before any `nginx reload`,
  always run `nginx -t` first. If the test fails, delete the new config and
  stop — do NOT reload. Never use `nginx restart` (use `reload` only).
- **MySQL**: You may CREATE a new database and user only. Never drop, alter, or
  query existing databases.
- **systemd**: You may add and enable a new `accounting.service` only.

---

## Server details

- **VPS IP**: `108.61.216.123`
- **SSH**: Connect as root: `ssh root@108.61.216.123`
- **User switching**: Use `su - accounting` for all file operations under
  `/home/accounting/`. Return to root with `exit` for systemd/nginx/certbot/MySQL.
- **Rule of thumb**:
  - `root`: systemd, nginx, certbot, MySQL admin commands, chown
  - `accounting`: git clone, venv creation, pip install, writing app files
- **File transfers**: scp as root to `/tmp/`, then move/chown as needed

---

## Deployment target

| Property | Value |
|----------|-------|
| App path on VPS | `/home/accounting/accounting_program` |
| Domain | `accounting.precisionpros.com` |
| Backend port | `8010` |
| Service name | `accounting.service` |
| Python venv | `/home/accounting/accounting_program/backend/venv` |
| Frontend dist | `/home/accounting/accounting_program/frontend/dist` |

---

## Pre-flight checks (run these BEFORE any deployment steps)

### On the local Mac:

1. Verify Node.js and npm are available:
   ```bash
   node --version && npm --version
   ```
   If either is missing, stop and report.

2. Retrieve and display the GitHub repo URL:
   ```bash
   git -C ~/accounting remote get-url origin
   ```
   Save this — you'll need it for the clone step.

3. Retrieve and display the full contents of the dev `.env`:
   ```bash
   cat ~/accounting/backend/.env
   ```
   You will use this to construct the production `.env` in Step 3.

4. Verify the mark user exists in the dev database (used for end-to-end test):
   ```bash
   mysql -u ppros -p precisionpros -e "SELECT id, username FROM users WHERE username='mark';"
   ```
   If no row is returned, note this — the end-to-end test in Step 8 will need
   a different valid username.

### On the server (ssh root@108.61.216.123):

5. Confirm port 8010 is not already in use:
   ```bash
   ss -tlnp | grep 8010
   ```
   If anything is listening on 8010, stop and report.

6. Confirm MySQL is running:
   ```bash
   systemctl status mysql --no-pager
   ```

7. Confirm nginx is running:
   ```bash
   systemctl status nginx --no-pager
   ```

8. Test MySQL root access:
   ```bash
   if ! mysql -u root -e "SELECT 1;" > /dev/null 2>&1; then
     echo "Passwordless root access failed. Try: mysql -u root -p<PASSWORD> -e 'SELECT 1;'"
     echo "If that doesn't work either, stop and report."
     exit 1
   fi
   echo "MySQL root access OK"
   ```

9. Verify git is installed on the server:
   ```bash
   git --version
   ```

10. Test git access to the GitHub repo (use the URL retrieved in pre-flight #2):
    ```bash
    git ls-remote <REPO_URL> HEAD
    ```
    If this fails (auth error, not found), stop and report — the clone will fail.

11. Verify OPERATIONS.md exists on the local Mac:
    ```bash
    if [ ! -f ~/games_dev/OPERATIONS.md ]; then
      echo "ERROR: ~/games_dev/OPERATIONS.md not found — ensure games_dev repo is cloned locally"
      exit 1
    fi
    echo "OPERATIONS.md found OK"
    ```

12. Check if `/home/accounting/accounting_program` already exists and has content:
    ```bash
    ls /home/accounting/accounting_program 2>/dev/null && echo "EXISTS" || echo "CLEAR"
    ```
    If it exists and is non-empty, report before proceeding.

---

## Step 1 — Database migration

### On the local Mac:

1. Read the DB password from the dev `.env`:
   ```bash
   grep DB_PASSWORD ~/accounting/backend/.env
   ```
   Note this password — you'll use it for the dump and for creating the
   production user.

2. Dump the database:
   ```bash
   mysqldump -u ppros -p precisionpros > /tmp/precisionpros_dump.sql
   echo "Dump size: $(wc -l < /tmp/precisionpros_dump.sql) lines"
   ```
   Verify the line count is non-trivial (should be tens of thousands of lines
   given 4,000+ invoices). If the file is suspiciously small (< 1000 lines),
   stop and report.

3. Transfer the dump to the server:
   ```bash
   scp /tmp/precisionpros_dump.sql root@108.61.216.123:/tmp/precisionpros_dump.sql
   ```

### On the server (as root):

4. Check if the `precisionpros` database already exists on the server:
   ```bash
   mysql -u root -e "SHOW DATABASES LIKE 'precisionpros';"
   ```
   - If it **does not exist**: proceed to step 5 (create fresh)
   - If it **already exists**: back it up first before importing:
     ```bash
     mysqldump -u root precisionpros > /tmp/precisionpros_backup_$(date +%Y%m%d_%H%M%S).sql
     ```
     Then proceed to step 5.

5. Create the database and user. Set the password variable first so it's
   explicit and not buried in a heredoc:
   ```bash
   DB_PASS="<password from pre-flight step 1>"
   mysql -u root -e "
   CREATE DATABASE IF NOT EXISTS precisionpros
     CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER IF NOT EXISTS 'ppros'@'localhost' IDENTIFIED BY '$DB_PASS';
   GRANT ALL PRIVILEGES ON precisionpros.* TO 'ppros'@'localhost';
   FLUSH PRIVILEGES;
   "
   echo "Database and user created OK"
   ```

6. Import the dump:
   ```bash
   mysql -u ppros -p precisionpros < /tmp/precisionpros_dump.sql
   ```

7. Verify the import looks correct — check row counts across key tables:
   ```bash
   mysql -u ppros -p precisionpros -e "
   SELECT table_name, table_rows
   FROM information_schema.tables
   WHERE table_schema = 'precisionpros'
   ORDER BY table_rows DESC;"
   ```
   Expect: invoices ~4000+ rows, clients ~200 rows, invoice_line_items ~10000+ rows.
   If all tables show 0 rows, the import failed — stop and report.

8. Clean up:
   ```bash
   rm /tmp/precisionpros_dump.sql
   ```
   (Keep any backup file you created in step 4.)

---

## Step 2 — Clone repo and set up backend

### On the server, switch to the accounting user for all file operations:
```bash
su - accounting
```

1. Clone the GitHub repo (use the URL from pre-flight step 2):
   ```bash
   cd /home/accounting
   git clone <REPO_URL> accounting_program
   cd accounting_program
   ```

2. Create a dedicated Python venv — do NOT use the shared env at
   `/home/accounting/accounting_program/env`:
   ```bash
   cd /home/accounting/accounting_program/backend
   python3 -m venv venv
   source venv/bin/activate
   # Verify the venv is active:
   python -c "import sys; print(sys.prefix)" | grep -q venv || { echo "venv not active!"; exit 1; }
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. Create the production `.env` file. Start from the dev `.env` contents
   retrieved in pre-flight step 3, then modify only the fields listed below:
   ```bash
   cat > /home/accounting/accounting_program/backend/.env <<'ENVEOF'
   PASTE_FULL_CONTENTS_OF_DEV_ENV_HERE
   ENVEOF
   ```
   After creating it, update these specific fields:
   ```bash
   # View current values:
   cat /home/accounting/accounting_program/backend/.env

   # Fields to change for production:
   # DB_HOST → localhost  (if not already)
   # DB_NAME → precisionpros  (if not already)
   # DB_USER → ppros  (if not already)
   # DB_PASSWORD → <same password used in Step 1>
   # SECRET_KEY → generate a new one:
   python3 -c "import secrets; print(secrets.token_hex(32))"
   # ^^^ Copy this output and set SECRET_KEY to this value in the .env
   # All SMTP/email settings → keep identical to dev
   # Any DEBUG flag → set to False
   ```
   **Important**: Print the generated SECRET_KEY and save it to a secure location
   before continuing. If the service ever needs to be rebuilt, you'll need it to
   keep existing JWT sessions valid.

   Verify the .env looks correct:
   ```bash
   cat /home/accounting/accounting_program/backend/.env
   ```

4. Run Alembic migrations to ensure the schema matches the current codebase
   (even though the dump was imported, migrations ensure any schema additions
   in the codebase are applied):
   ```bash
   cd /home/accounting/accounting_program/backend
   source venv/bin/activate
   alembic upgrade head
   ```
   If this errors with "already at head" or "no new migrations", that's fine —
   it means the dump already has the latest schema. Any other error: stop and report.

5. Test that the backend starts cleanly:
   ```bash
   cd /home/accounting/accounting_program/backend
   source venv/bin/activate
   uvicorn main:app --host 127.0.0.1 --port 8010 > /tmp/uvicorn_test.log 2>&1 &
   UVICORN_PID=$!
   sleep 4
   HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8010/api/auth/me)
   kill $UVICORN_PID 2>/dev/null
   wait $UVICORN_PID 2>/dev/null
   echo "Response code: $HTTP_CODE"
   ```
   A 401 or 422 response means the backend started correctly (auth required).
   A 000 or 5xx means it crashed — show the log: `cat /tmp/uvicorn_test.log`
   and stop.

---

## Step 3 — Systemd service

Exit back to root (`exit` from accounting user), then create the service file:

```bash
cat > /etc/systemd/system/accounting.service <<'EOF'
[Unit]
Description=PrecisionPros Accounting Backend
After=network.target mysql.service

[Service]
User=accounting
WorkingDirectory=/home/accounting/accounting_program/backend
ExecStart=/home/accounting/accounting_program/backend/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8010
Restart=on-failure
RestartSec=5
EnvironmentFile=/home/accounting/accounting_program/backend/.env

[Install]
WantedBy=multi-user.target
EOF
```

Enable and start:
```bash
systemctl daemon-reload
systemctl enable accounting
systemctl start accounting
sleep 3
systemctl status accounting --no-pager

if ! systemctl is-active --quiet accounting; then
  echo "ERROR: accounting.service failed to start"
  journalctl -u accounting -n 50 --no-pager
  exit 1
fi
echo "Service is active"
```

Confirm the backend is responding:
```bash
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8010/api/auth/me)
echo "Backend health check: $HTTP_CODE"
if [[ "$HTTP_CODE" != "401" && "$HTTP_CODE" != "422" ]]; then
  echo "ERROR: Unexpected response ($HTTP_CODE) — backend may not be healthy"
  journalctl -u accounting -n 30 --no-pager
  exit 1
fi
echo "Backend responding correctly"
```

---

## Step 4 — Build and transfer frontend

### On the local Mac:

1. Verify Node.js is available and build the React app:
   ```bash
   cd ~/accounting/frontend
   node --version && npm --version
   npm run build
   ```

2. Verify the build succeeded:
   ```bash
   if [ ! -f ~/accounting/frontend/dist/index.html ]; then
     echo "ERROR: Build failed — dist/index.html not found"
     ls -la ~/accounting/frontend/dist/ 2>/dev/null || echo "dist/ folder doesn't exist"
     exit 1
   fi
   echo "Build OK — $(find ~/accounting/frontend/dist -type f | wc -l) files"
   ```
   If the build failed or produced no files, stop and report the ls output.

3. Transfer built files to server:
   ```bash
   scp -r ~/accounting/frontend/dist root@108.61.216.123:/tmp/accounting_dist
   ```

### On the server (as root):

4. Move the dist into place and fix ownership:
   ```bash
   mkdir -p /home/accounting/accounting_program/frontend
   mv /tmp/accounting_dist /home/accounting/accounting_program/frontend/dist
   chown -R accounting:accounting /home/accounting/accounting_program/frontend/dist
   ```

5. Verify the dist is in place:
   ```bash
   ls /home/accounting/accounting_program/frontend/dist/index.html && echo "OK"
   ```

---

## Step 5 — nginx config

On the server (as root):

1. Create the new nginx site config:
   ```bash
   cat > /etc/nginx/sites-available/accounting.precisionpros.com <<'EOF'
   server {
       listen 80;
       server_name accounting.precisionpros.com;

       root /home/accounting/accounting_program/frontend/dist;
       index index.html;

       location / {
           try_files $uri $uri/ /index.html;
       }

       location /api/ {
           proxy_pass http://127.0.0.1:8010;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
           proxy_read_timeout 60s;
       }
   }
   EOF
   ```

2. Enable the site:
   ```bash
   ln -s /etc/nginx/sites-available/accounting.precisionpros.com \
         /etc/nginx/sites-enabled/accounting.precisionpros.com
   ```

3. **Test the nginx config — if this fails, remove the symlink and stop:**
   ```bash
   nginx -t
   ```
   If the test fails:
   ```bash
   rm /etc/nginx/sites-enabled/accounting.precisionpros.com
   echo "nginx config failed — NOT reloading. Report the error above."
   ```

4. Only if the test passes, reload nginx:
   ```bash
   systemctl reload nginx
   ```

5. **Immediately verify the games sites are still healthy:**
   ```bash
   GAMES=$(curl -s -o /dev/null -w "%{http_code}" https://games.precisionpros.com)
   CONNECT=$(curl -s -o /dev/null -w "%{http_code}" https://connectpro.precisionpros.com)
   echo "games.precisionpros.com: $GAMES"
   echo "connectpro.precisionpros.com: $CONNECT"
   ```
   If either returns 000 or 502, the reload affected the games configs —
   immediately remove the new symlink, reload nginx again to restore, and stop:
   ```bash
   rm /etc/nginx/sites-enabled/accounting.precisionpros.com
   systemctl reload nginx
   echo "ROLLED BACK — report this error"
   ```

---

## Step 6 — SSL certificate

On the server (as root):

```bash
certbot --nginx -d accounting.precisionpros.com --non-interactive \
  --agree-tos -m billing@precisionpros.com
```

After certbot runs:
1. Verify the nginx config is still valid: `nginx -t`
2. Verify HTTPS is working:
   ```bash
   curl -s -o /dev/null -w "%{http_code}" https://accounting.precisionpros.com
   ```
   Expect 200.
3. Re-verify the games are still healthy:
   ```bash
   echo "games: $(curl -s -o /dev/null -w "%{http_code}" https://games.precisionpros.com)"
   echo "connectpro: $(curl -s -o /dev/null -w "%{http_code}" https://connectpro.precisionpros.com)"
   ```

---

## Step 7 — End-to-end verification

1. Test the login API over HTTPS.
   If pre-flight confirmed `mark` exists in the DB, use:
   ```bash
   curl -s -X POST https://accounting.precisionpros.com/api/auth/token \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=mark&password=mark"
   ```
   If pre-flight showed `mark` does NOT exist, substitute a valid
   username/password found in the dev DB during pre-flight step 4.

   Either way, the response should be a JSON object containing `access_token`.
   If it returns an error, run `journalctl -u accounting -n 30 --no-pager`
   and report.

2. Confirm all three services are independently active:
   ```bash
   for svc in accounting games connectpro; do
     echo "$svc: $(systemctl is-active $svc)"
   done
   ```
   All three must show `active`.

---

## Step 8 — Update OPERATIONS.md

On the local Mac, update `~/games_dev/OPERATIONS.md`:

Add the accounting app to the Quick Reference table at the top:
```markdown
| Accounting | accounting.precisionpros.com | /home/accounting/accounting_program | accounting.service | 8010 |
```

Add a full section after the ConnectPro entry:
```markdown
### Accounting (live)
| Property | Value |
|----------|-------|
| Domain | accounting.precisionpros.com |
| VPS path | /home/accounting/accounting_program |
| Backend path | /home/accounting/accounting_program/backend |
| Frontend dist | /home/accounting/accounting_program/frontend/dist |
| Service | `accounting.service` (uvicorn, 127.0.0.1:8010) |
| Python venv | /home/accounting/accounting_program/backend/venv |
```

Add the accounting deploy procedure to the operations doc:
```markdown
### Accounting deploy procedure

| What changed | Steps |
|---|---|
| Backend only | `ssh root@108.61.216.123` → `su - accounting` → `cd accounting_program && git pull` → `exit` → `systemctl restart accounting` |
| Frontend only | Local: `cd ~/accounting/frontend && npm run build` → verify `dist/index.html` exists → `scp -r dist/ root@108.61.216.123:/tmp/accounting_dist` → on server: `mv /tmp/accounting_dist /home/accounting/accounting_program/frontend/dist && chown -R accounting:accounting /home/accounting/accounting_program/frontend/dist` |
| Both | Backend steps first, then frontend steps |
| DB schema change | SSH → `su - accounting` → `cd accounting_program && git pull && source backend/venv/bin/activate && alembic upgrade head` → `exit` → `systemctl restart accounting` |
```

---

## If anything goes wrong

| Problem | Action |
|---------|--------|
| Service won't start | `journalctl -u accounting -n 50 --no-pager` — report full output, stop |
| nginx -t fails | Delete the new symlink, do NOT reload, report the error |
| Games site returns 000 or 502 after nginx reload | Remove accounting symlink, `systemctl reload nginx`, verify games recover, report |
| Database import produces 0 rows | Do not proceed — report error, restore from backup if one was made |
| Git clone fails | Report auth error — do not proceed |
| Alembic errors (not "already at head") | Report full error — do not proceed |
