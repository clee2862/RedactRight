# RedactRight

A FastAPI web app to redact common PII patterns from text or uploaded PDFs and store redaction run history in Oracle.

## Assumption used
`PRD.md` is still the default blank template, so this app was generated as a practical default for the `RedactRight` folder name.

## Features
- Redact email, phone, SSN, credit-card-like strings, and IPv4 addresses
- Redact directly on uploaded PDFs and download a redacted PDF artifact
- Save each redaction run in Oracle
- Browse run history
- View original vs redacted text, inspect findings, and download redacted output as `.txt` or `.pdf`

## Files
- `app/main.py` - routes + pages
- `app/redactor.py` - text and PDF redaction engine
- `app/repository.py` - Oracle queries
- `app/db.py` - Oracle thick-mode pool setup
- `app/schema.sql` - DB table DDL

## Setup
```bash
cd /home/opc/RedactRight
python3.9 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The PDF workflow uses `PyMuPDF`, so be sure dependencies are reinstalled after pulling changes.

## DB schema
```bash
sql -name hktr1g12
@/home/opc/RedactRight/app/schema.sql
```

## Run
```bash
export DB_USER='HKTR1G12'
export DB_PASSWORD='Hk1_ePBC_KlbRLORwiPW'
export DB_DSN='hkt202602_high'
export DB_CONFIG_DIR='/home/opc/wallet'
export DB_WALLET_LOCATION='/home/opc/wallet'
export DB_WALLET_PASSWORD='Hk1_ePBC_KlbRLORwiPW'
export ORACLE_CLIENT_LIB_DIR='/usr/lib/oracle/23/client64/lib'
uvicorn app.main:app --host 0.0.0.0 --port 3001 --reload
```

Open: `http://<host>:3001/redact`
