import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = "RedactRight"
    db_user: str = os.getenv("DB_USER", "HKTR1G12")
    db_password: str = os.getenv("DB_PASSWORD", "")
    db_dsn: str = os.getenv("DB_DSN", "hkt202602_high")
    db_config_dir: str = os.getenv("DB_CONFIG_DIR", "/home/opc/wallet")
    db_wallet_location: str = os.getenv("DB_WALLET_LOCATION", "/home/opc/wallet")
    db_wallet_password: str = os.getenv("DB_WALLET_PASSWORD", "")
    oracle_client_lib_dir: str = os.getenv("ORACLE_CLIENT_LIB_DIR", "/usr/lib/oracle/23/client64/lib")


settings = Settings()
