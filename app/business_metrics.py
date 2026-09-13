"""Deterministic business KPIs from the uploaded sales table. No LLM numbers."""

from __future__ import annotations

import pandas as pd


def _has(df: pd.DataFrame, *cols: str) -> bool:
    return all(c in df.columns for c in cols)


def _safe_sum(df: pd.DataFrame, col: str) -> float:
    if col not in df.columns:
        return 0.0
    return float(pd.to_numeric(df[col], errors="coerce").fillna(0).sum())


def compute_business_profile(df: pd.DataFrame) -> dict:
    work = df.copy()
    date_min = date_max = None
    if "date" in work.columns:
        work["date"] = pd.to_datetime(work["date"], errors="coerce")
        valid = work["date"].dropna()
        if not valid.empty:
            date_min = valid.min().date().isoformat()
            date_max = valid.max().date().isoformat()

    products = int(work["product"].nunique()) if "product" in work.columns else 0
    categories = int(work["category"].nunique()) if "category" in work.columns else 0

    return {
        "row_count": int(len(work)),
        "column_count": int(len(work.columns)),
        "missing_values": int(work.isna().sum().sum()),
        "duplicate_rows": int(len(work) - len(work.drop_duplicates())) if len(work) else 0,
        "date_min": date_min,
        "date_max": date_max,
        "total_revenue": round(_safe_sum(work, "revenue"), 2),
        "total_cost": round(_safe_sum(work, "cost"), 2),
        "total_profit": round(_safe_sum(work, "profit"), 2),
        "total_quantity": round(_safe_sum(work, "quantity"), 2),
        "product_count": products,
        "category_count": categories,
    }


def revenue_over_time(df: pd.DataFrame) -> pd.DataFrame:
    if not _has(df, "date", "revenue"):
        return pd.DataFrame(columns=["date", "revenue"])
    work = df.copy()
    work["date"] = pd.to_datetime(work["date"], errors="coerce")
    work["revenue"] = pd.to_numeric(work["revenue"], errors="coerce")
    out = (
        work.dropna(subset=["date"])
        .groupby(work["date"].dt.to_period("M").dt.to_timestamp(), dropna=True)["revenue"]
        .sum()
        .reset_index()
    )
    out.columns = ["date", "revenue"]
    return out


def profit_over_time(df: pd.DataFrame) -> pd.DataFrame:
    if not _has(df, "date", "profit"):
        return pd.DataFrame(columns=["date", "profit"])
    work = df.copy()
    work["date"] = pd.to_datetime(work["date"], errors="coerce")
    work["profit"] = pd.to_numeric(work["profit"], errors="coerce")
    out = (
        work.dropna(subset=["date"])
        .groupby(work["date"].dt.to_period("M").dt.to_timestamp(), dropna=True)["profit"]
        .sum()
        .reset_index()
    )
    out.columns = ["date", "profit"]
    return out


def top_products(df: pd.DataFrame, metric: str = "revenue", n: int = 10) -> pd.DataFrame:
    if not _has(df, "product", metric):
        return pd.DataFrame(columns=["product", metric])
    work = df.copy()
    work[metric] = pd.to_numeric(work[metric], errors="coerce").fillna(0)
    return (
        work.groupby("product", as_index=False)[metric]
        .sum()
        .sort_values(metric, ascending=False)
        .head(n)
        .reset_index(drop=True)
    )


def category_performance(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in ("revenue", "profit", "quantity") if c in df.columns]
    if not _has(df, "category") or not cols:
        return pd.DataFrame(columns=["category", *cols])
    work = df.copy()
    for c in cols:
        work[c] = pd.to_numeric(work[c], errors="coerce").fillna(0)
    return (
        work.groupby("category", as_index=False)[cols]
        .sum()
        .sort_values(cols[0], ascending=False)
        .reset_index(drop=True)
    )


def money(value: float) -> str:
    return f"Rs {value:,.0f}"
