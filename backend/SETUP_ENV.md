# Setting Up .env for Master Import Runner

**Required before running** `run_full_import.py`

---

## Step 1: Copy the Template

```bash
cd ~/accounting/backend
cp .env.example .env
```

---

## Step 2: Edit .env with Your Credentials

```bash
nano .env
```

or use your preferred editor. The file should look like:

```ini
DB_HOST=localhost
DB_PORT=3306
DB_NAME=precisionpros
DB_USER=ppros
DB_PASSWORD=your_actual_password_here
```

**Update the values:**
- `DB_HOST` — MySQL server hostname (usually `localhost` if running locally)
- `DB_PORT` — MySQL port (default is `3306`)
- `DB_NAME` — Database name (default is `precisionpros`)
- `DB_USER` — MySQL username (default is `ppros`)
- `DB_PASSWORD` — MySQL password (replace with actual password)

---

## Step 3: Verify Credentials Work

Test the connection:

```bash
mysql -u ppros -pyour_password -h localhost -P 3306 -e "SELECT 1;" precisionpros
```

If you see `1`, the connection works. If you get an error, check:
- Is MySQL running? `ps aux | grep mysql`
- Are credentials correct? `echo $DB_PASSWORD`
- Does the database exist? `mysql -u ppros -p... -e "SHOW DATABASES;"`

---

## Step 4: Secure .env

Make sure .env is not readable by others:

```bash
chmod 600 ~/.env
```

And ensure it's NOT committed to git:

```bash
echo ".env" >> ~/.gitignore
git config --local core.excludesfile ~/.gitignore
```

---

## Step 5: Run the Import

Now you can run the master import:

```bash
cd ~/accounting/backend

# Preview
python3 run_full_import.py --dry-run

# Execute
python3 run_full_import.py --commit
```

The script will:
1. Read credentials from `.env`
2. Connect to MySQL non-interactively (no password prompts)
3. Run all import steps
4. Generate a log file with timestamp

---

## Troubleshooting

### "Access denied for user 'ppros'"
- Check password in .env is correct
- Verify user exists in MySQL: `mysql -u root -p... -e "SELECT user FROM mysql.user;"`
- Reset user password if needed: `ALTER USER 'ppros'@'localhost' IDENTIFIED BY 'newpassword';`

### "Can't connect to MySQL server"
- Is MySQL running? `brew services start mysql` (on Mac)
- Check host/port: `mysql -h localhost -P 3306 -e "SELECT 1;"`
- Try with root: `mysql -u root -p...`

### "Unknown database 'precisionpros'"
- Create it: `mysql -u root -p... -e "CREATE DATABASE precisionpros;"`
- Or update .env to match actual database name

### "Script still asks for password"
- Ensure .env file is in the same directory as the script
- Check that DB_PASSWORD is set and has no spaces: `echo "$DB_PASSWORD"`
- Verify no `-p` flag is being added alone (fixed in recent update)

---

## .env Variables Reference

| Variable | Default | Required | Notes |
|----------|---------|----------|-------|
| DB_HOST | localhost | Yes | IP or hostname of MySQL server |
| DB_PORT | 3306 | Yes | MySQL port (usually 3306) |
| DB_NAME | precisionpros | Yes | Database name to import into |
| DB_USER | ppros | Yes | MySQL username |
| DB_PASSWORD | (empty) | No | MySQL password (leave empty if no password) |

---

## Security Notes

⚠️ **DO NOT:**
- Commit .env to git
- Share .env with others
- Hardcode credentials in scripts
- Use weak passwords

✅ **DO:**
- Keep .env in `.gitignore`
- Use strong passwords
- Restrict .env file permissions (`chmod 600`)
- Store .env securely

---

## After Setup

Once .env is configured, you can run the import repeatedly without typing passwords:

```bash
cd ~/accounting/backend
python3 run_full_import.py --commit
```

The script handles all the MySQL authentication non-interactively.

---

*Setup guide created April 14, 2026*
