# WeasyPrint Setup for Linux (Production)

WeasyPrint requires several system libraries to generate PDFs. On the production VPS (Linux), these need to be installed via apt.

## Install System Dependencies

```bash
# On the VPS, as root
apt-get update
apt-get install -y \
  libffi-dev \
  libcairo2-dev \
  libpango-1.0-0 \
  libpango-cairo-1.0-0 \
  libgdk-pixbuf2.0-0 \
  libffi8 \
  libcairo2 \
  libjpeg-turbo-progs \
  libpng-tools
```

## Verify Installation

After installing system dependencies, test that WeasyPrint can import:

```bash
cd /home/accounting/accounting_program
source backend/venv/bin/activate
python3 -c "from weasyprint import HTML; print('WeasyPrint imported successfully')"
```

If successful, you should see:
```
WeasyPrint imported successfully
```

If you see an error about missing libraries, check that all packages above are installed.

## Notes

- These libraries are only needed for PDF generation
- The production startup script (`start_backend.sh`) will NOT set macOS paths on Linux
- Both invoice PDFs and P&L report PDFs will work once these dependencies are installed
- No environment variables need to be manually set on Linux; pkg-config will find the libraries automatically

## Troubleshooting

If WeasyPrint still fails to import after installing packages:

1. Check that `libffi-dev` is installed: `dpkg -l | grep libffi`
2. Verify pkg-config can find the libraries:
   ```bash
   pkg-config --cflags libffi
   pkg-config --libs libffi
   ```
3. If pkg-config fails, the development headers weren't installed with apt-get

