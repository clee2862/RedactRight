#!/usr/bin/env bash
set -euo pipefail
cd /home/opc/RedactRight
source .venv/bin/activate
export DB_USER='HKTR1G12'
export DB_PASSWORD='Hk1_ePBC_KlbRLORwiPW'
export DB_DSN='hkt202602_high'
export DB_CONFIG_DIR='/home/opc/wallet'
export DB_WALLET_LOCATION='/home/opc/wallet'
export DB_WALLET_PASSWORD='Hk1_ePBC_KlbRLORwiPW'
export ORACLE_CLIENT_LIB_DIR='/usr/lib/oracle/23/client64/lib'
exec uvicorn app.main:app --host 0.0.0.0 --port 3001
