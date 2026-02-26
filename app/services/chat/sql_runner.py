import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.engine import SessionLocal

STATEMENT_TIMEOUT_MS = 10000
FORBIDDEN_SQL = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke)\b",
    re.IGNORECASE,
)


def _to_json_safe(value: Any):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def validate_read_only_sql(sql: str) -> str:
    if not isinstance(sql, str) or not sql.strip():
        raise ValueError("SQL must be a non-empty string")

    normalized = sql.strip()
    lowered = normalized.lower()

    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise ValueError("Only SELECT/WITH queries are allowed")

    if FORBIDDEN_SQL.search(lowered):
        raise ValueError("Only read-only SQL is allowed")

    if ";" in normalized[:-1]:
        raise ValueError("Multiple SQL statements are not allowed")

    return normalized


def run_sql_query(sql: str) -> dict:
    safe_sql = validate_read_only_sql(sql)

    try:
        with SessionLocal() as session:
            # Guard against slow/expensive generated queries (best-effort for managed DBs).
            try:
                session.execute(
                    text(f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}")
                )
            except SQLAlchemyError:
                session.rollback()
            result = session.execute(text(safe_sql))
            rows = result.mappings().all()
    except SQLAlchemyError as exc:
        raise ValueError(f"Database query failed: {exc}") from exc

    serialized_rows = [
        {key: _to_json_safe(value) for key, value in row.items()} for row in rows
    ]

    return {
        "sql": safe_sql,
        "row_count": len(serialized_rows),
        "rows": serialized_rows,
    }
