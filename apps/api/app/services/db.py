from contextlib import contextmanager

import psycopg

from app.core.config import get_settings


def psycopg_url() -> str:
    return get_settings().database_url.replace("postgresql+psycopg://", "postgresql://")


@contextmanager
def get_conn():
    conn = psycopg.connect(psycopg_url())
    try:
        yield conn
    finally:
        conn.close()
