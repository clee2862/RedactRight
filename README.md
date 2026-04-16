# RedactRight

RedactRight is a FastAPI application that redacts sensitive information from pasted text and uploaded PDF files, stores each redaction run in Oracle Autonomous Database, and lets users review or download the redacted output afterward.

## What it does

- Redacts common PII patterns such as email addresses, phone numbers, SSNs, credit-card-like values, and IPv4 addresses
- Supports custom names or phrases for exact-match redaction
- Detects likely person names for human review before redaction
- Redacts uploaded PDFs in-place and saves the generated PDF artifact
- Persists run history, detector settings, findings, and downloadable artifacts in Oracle

## Tech stack

- Python 3.9
- FastAPI
- Jinja2 templates
- PyMuPDF for PDF parsing and redaction
- python-oracledb for Oracle connectivity
- Oracle Autonomous Database 26ai

## Project layout

```text
RedactRight/
├── app/
│   ├── config.py        # Environment-based settings
│   ├── db.py            # Oracle client initialization and pool management
│   ├── main.py          # FastAPI routes, request handling, downloads
│   ├── redactor.py      # Text and PDF redaction engine
│   ├── repository.py    # Oracle persistence layer
│   └── schema.sql       # Table definition for redaction history
├── static/              # Stylesheets
├── templates/           # Jinja page templates
├── .env.example         # Sample environment variable template
├── ARCHITECTURE.md      # System design and data flow
├── PRD.md               # Product requirements and demo framing
└── run_redactright.sh   # Convenience launcher
```

## Core user flow

1. A user pastes text or uploads a TXT/CSV/JSON/PDF file.
2. The app optionally detects likely person names for review.
3. The user selects detectors and custom terms.
4. The app redacts the content and stores the run in Oracle.
5. The user reviews the saved run and downloads redacted output or a findings report.

## Prerequisites

- Python 3.9 available as `python3.9`
- Oracle wallet files available on the machine
- Oracle Instant Client installed if using thick mode
- Access to an Oracle schema with permission to create tables

## Local setup

```bash
cd /home/opc/RedactRight
python3.9 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Export the required environment variables before starting the app:

```bash
export DB_USER='your_schema_user'
export DB_PASSWORD='your_schema_password'
export DB_DSN='your_tns_service'
export DB_CONFIG_DIR='/path/to/wallet'
export DB_WALLET_LOCATION='/path/to/wallet'
export DB_WALLET_PASSWORD='your_wallet_password'
export ORACLE_CLIENT_LIB_DIR='/usr/lib/oracle/23/client64/lib'
```

## Database bootstrap

Create the table with SQLcl:

```bash
sql -name hktr1g12
@/home/opc/RedactRight/app/schema.sql
```

At startup, the app also checks whether the artifact columns exist and adds them if they are missing.

## Running the app

Development server:

```bash
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 3001 --reload
```

Convenience script:

```bash
./run_redactright.sh
```

Open the app at `http://<host>:3001/redact`.

## Main routes

- `GET /redact`: redaction form
- `POST /redact`: detect names or redact and save a run
- `GET /runs`: run history
- `GET /runs/{run_id}`: run detail view
- `GET /runs/{run_id}/download`: download redacted text
- `GET /runs/{run_id}/download-pdf`: download redacted PDF when available
- `GET /runs/{run_id}/download-report`: download JSON findings report

## Current limitations

- Detection is regex- and heuristic-based, not ML-based
- PDF redaction works best for digitally generated PDFs with extractable text
- There is no authentication or tenant isolation yet
- Large files and concurrent workloads have not been optimized yet

## Additional docs

- `ARCHITECTURE.md`
- `PRD.md`
- `docs/OPERATIONS.md`
