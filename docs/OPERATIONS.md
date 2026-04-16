# Operations Guide

## Local development checklist

1. Create and activate the virtual environment.
2. Install `requirements.txt`.
3. Export Oracle connection environment variables.
4. Apply `app/schema.sql` if the table does not exist yet.
5. Start the app with Uvicorn or `run_redactright.sh`.

## Useful commands

Install dependencies:

```bash
cd /home/opc/RedactRight
python3.9 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run locally:

```bash
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 3001 --reload
```

Run with helper script:

```bash
./run_redactright.sh
```

Apply schema:

```bash
sql -name hktr1g12
@/home/opc/RedactRight/app/schema.sql
```

## Deployment notes

- The app currently expects Oracle thick mode and a valid wallet path
- Temporary draft files are written to `/tmp/redactright_drafts`
- Port `3001` must be reachable if the app is demoed remotely

## Operational risks

- Sensitive source files may be stored in Oracle and temporary disk drafts
- There is no retention policy or cleanup job yet
- There is no auth layer protecting run history

## Recommended next hardening steps

1. Move secrets out of helper scripts and into deployment-managed env vars.
2. Add authentication before exposing the app publicly.
3. Add cleanup for stale draft files in `/tmp/redactright_drafts`.
4. Add tests for redaction edge cases and PDF handling.
