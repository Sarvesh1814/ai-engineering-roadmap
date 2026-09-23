import re

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import pandas as pd

from config.settings import get_settings

load_dotenv()

_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9_]+$")


def _validate_identifier(name: str) -> str:
    """Validate that a SQL identifier (table/view name) is safe to interpolate."""
    if not _SAFE_IDENTIFIER.match(name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return name


def get_engine():
    settings = get_settings()
    password = settings.mysql_password or ""
    DATABASE_URL = (
        f"mysql+pymysql://{settings.mysql_user}:{password}@"
        f"{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database}"
    )
    return create_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )


def load_view(view_name: str | None = None, chunk_size: int | None = None):
    settings = get_settings()
    view = _validate_identifier(view_name or settings.mysql_ingestion_view)
    size = chunk_size or settings.mysql_batch_size

    query = f"SELECT * FROM `{view}`"
    engine = get_engine()

    return pd.read_sql(
        query,
        engine,
        chunksize=size,
    )


def _get_timestamp_column(engine, view: str) -> str:
    """Find the timestamp column present in the view."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"DESCRIBE `{view}`"))
            cols = [r[0] for r in result.fetchall()]
            for cand in ["updated_at", "updated_time", "modified_time", "OH_last_update"]:
                if cand in cols:
                    return cand
    except Exception:
        pass
    return "updated_at"


def get_max_updated_at(view_name: str | None = None) -> str | None:
    """Get the maximum updated timestamp from the view for checkpointing."""
    settings = get_settings()
    view = _validate_identifier(view_name or settings.mysql_ingestion_view)
    engine = get_engine()
    ts_col = _get_timestamp_column(engine, view)

    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT MAX(`{ts_col}`) FROM `{view}`"))
        row = result.fetchone()
        return row[0] if row and row[0] else None


def load_view_incremental(
    view_name: str | None = None,
    chunk_size: int | None = None,
    since: str | None = None,
):
    """Load only records updated since the given timestamp."""
    settings = get_settings()
    view = _validate_identifier(view_name or settings.mysql_ingestion_view)
    size = chunk_size or settings.mysql_batch_size

    engine = get_engine()

    if since:
        ts_col = _get_timestamp_column(engine, view)
        query = text(f"SELECT * FROM `{view}` WHERE `{ts_col}` > :since")
        return pd.read_sql(query, engine, params={"since": since}, chunksize=size)
    else:
        query = f"SELECT * FROM `{view}`"
        return pd.read_sql(query, engine, chunksize=size)