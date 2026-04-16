from contextlib import contextmanager

import oracledb

from app.config import settings

_pool = None
_thick_initialized = False


def init_pool() -> None:
    global _pool, _thick_initialized
    if _pool is not None:
        return

    if not _thick_initialized:
        oracledb.init_oracle_client(
            lib_dir=settings.oracle_client_lib_dir,
            config_dir=settings.db_config_dir,
        )
        _thick_initialized = True

    _pool = oracledb.create_pool(
        user=settings.db_user,
        password=settings.db_password,
        dsn=settings.db_dsn,
        config_dir=settings.db_config_dir,
        wallet_location=settings.db_wallet_location,
        wallet_password=settings.db_wallet_password,
        min=1,
        max=5,
        increment=1,
        getmode=oracledb.POOL_GETMODE_TIMEDWAIT,
        wait_timeout=3000,
        ping_timeout=2000,
    )


@contextmanager
def get_conn():
    if _pool is None:
        init_pool()
    conn = _pool.acquire()
    try:
        yield conn
    finally:
        _pool.release(conn)
