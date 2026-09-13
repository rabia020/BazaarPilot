"""In-memory DuckDB helpers with read-only SQL validation."""

from __future__ import annotations

import re

import duckdb
import pandas as pd

TABLE_NAME = "sales"
LEGACY_TABLE_NAME = "uploaded_data"

FORBIDDEN = {
    "insert", "update", "delete", "drop", "alter", "create", "replace",
    "truncate", "attach", "detach", "copy", "install", "load", "call",
    "export", "import", "pragma", "grant", "revoke", "vacuum",
}


def clean_sql(raw: str) -> str:
    sql = raw.strip()
    sql = re.sub(r"^```sql\s*", "", sql, flags=re.I)
    sql = re.sub(r"^```\s*", "", sql)
    sql = re.sub(r"\s*```$", "", sql)
    return sql.split(";")[0].strip()


def validate_sql(sql: str) -> str:
    cleaned = clean_sql(sql)
    if not cleaned:
        raise ValueError("SQL is empty.")
    low = cleaned.lower()
    if not low.startswith(("select", "with")):
        raise ValueError("Only SELECT/WITH queries are allowed.")
    for word in FORBIDDEN:
        if re.search(rf"\b{re.escape(word)}\b", low):
            raise ValueError(f"Forbidden SQL operation: {word.upper()}")
    return cleaned


def connect_sales(df: pd.DataFrame) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(database=":memory:")
    con.register(TABLE_NAME, df)
    con.register(LEGACY_TABLE_NAME, df)
    return con


def execute_readonly(sql: str, df: pd.DataFrame) -> pd.DataFrame:
    safe_sql = validate_sql(sql)
    con = connect_sales(df)
    try:
        return con.execute(safe_sql).df()
    finally:
        con.close()