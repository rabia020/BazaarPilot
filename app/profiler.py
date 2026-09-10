import duckdb
import pandas as pd


def profile_dataset(con: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> dict:
    """Return dataset-level profiling metrics using DuckDB + Pandas."""

    row_count = con.execute(
        "SELECT COUNT(*) FROM uploaded_data"
    ).fetchone()[0]

    column_count = len(df.columns)

    missing_values = int(df.isna().sum().sum())

    duplicate_rows = int(
        len(df) - len(df.drop_duplicates())
    ) if row_count else 0

    return {
        "row_count": int(row_count),
        "column_count": int(column_count),
        "missing_values": missing_values,
        "duplicate_rows": duplicate_rows,
    }


def profile_columns(con: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> pd.DataFrame:
    """Build a column-level profiling table."""

    rows = []

    for column in df.columns:
        # Quote the column safely for DuckDB.
        escaped = '"' + str(column).replace('"', '""') + '"'

        non_null = con.execute(
            f"SELECT COUNT({escaped}) FROM uploaded_data"
        ).fetchone()[0]

        unique = con.execute(
            f"SELECT COUNT(DISTINCT {escaped}) FROM uploaded_data"
        ).fetchone()[0]

        missing = int(df[column].isna().sum())

        rows.append(
            {
                "column": str(column),
                "data_type": str(df[column].dtype),
                "non_null": int(non_null),
                "missing": missing,
                "missing_%": round((missing / len(df)) * 100, 2),
                "unique": int(unique),
            }
        )

    return pd.DataFrame(rows)


def get_sample_rows(con: duckdb.DuckDBPyConnection, limit: int = 100) -> pd.DataFrame:
    """Return a sample of records through DuckDB."""
    return con.execute(
        f"SELECT * FROM uploaded_data LIMIT {int(limit)}"
    ).df()
