"""Load and validate CSV/Excel business datasets without crashing the app."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd

REQUIRED_FOR_BUSINESS = ("date", "product", "quantity")
PRICE_OR_REVENUE = ("unit_price", "revenue")
COST_OR_PROFIT = ("unit_cost", "cost", "profit")
INVENTORY_COL = "inventory"

COLUMN_ALIASES = {
    "date": ["date", "order_date", "sale_date", "invoice_date"],
    "product": ["product", "item", "product_name", "sku_name"],
    "category": ["category", "product_category"],
    "quantity": ["quantity", "qty", "units", "units_sold"],
    "unit_price": ["unit_price", "price", "selling_price"],
    "unit_cost": ["unit_cost", "cost_price"],
    "discount": ["discount", "discount_rate"],
    "revenue": ["revenue", "sales", "amount", "total"],
    "cost": ["cost", "total_cost"],
    "profit": ["profit", "gross_profit"],
    "inventory": ["inventory", "stock", "current_stock", "qty_on_hand"],
    "customer_type": ["customer_type", "customer_segment"],
    "region": ["region", "city"],
    "supplier": ["supplier", "vendor"],
}


def _friendly_read_error(exc: Exception, file_name: str) -> str:
    name = file_name.lower()
    msg = str(exc)
    if name.endswith(".csv"):
        return f"Could not read this CSV. Check the file is not empty or corrupted. Details: {msg}"
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return f"Could not read this Excel file. Export a .xlsx/.xls sheet with a header row. Details: {msg}"
    return f"Unsupported or unreadable file '{file_name}'. Use .csv, .xlsx, or .xls. Details: {msg}"


def _normalize_column_name(name: str) -> str:
    return str(name).strip().lower().replace(" ", "_").replace("-", "_")


def canonicalize_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Rename known aliases to canonical names. Never invent columns."""
    out = df.copy()
    out.columns = [_normalize_column_name(c) for c in out.columns]
    notes: list[str] = []
    used_targets: set[str] = set()

    for canonical, aliases in COLUMN_ALIASES.items():
        if canonical in out.columns:
            used_targets.add(canonical)
            continue
        for alias in aliases:
            if alias in out.columns and canonical not in used_targets:
                out = out.rename(columns={alias: canonical})
                notes.append(f"Renamed '{alias}' to '{canonical}'.")
                used_targets.add(canonical)
                break
    return out, notes


def enrich_calculated_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Fill revenue/cost/profit only when source columns exist. No fake numbers."""
    out = df.copy()
    notes: list[str] = []

    if "date" in out.columns:
        parsed = pd.to_datetime(out["date"], errors="coerce")
        bad = int(parsed.isna().sum())
        out["date"] = parsed
        if bad:
            notes.append(f"{bad} row(s) have invalid dates and will be ignored in date-based charts.")

    for col in ("quantity", "unit_price", "unit_cost", "discount", "revenue", "cost", "profit", "inventory"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    if "revenue" not in out.columns and {"quantity", "unit_price"}.issubset(out.columns):
        discount = out["discount"] if "discount" in out.columns else 0
        out["revenue"] = (out["quantity"] * out["unit_price"] * (1 - discount.fillna(0))).round(2)
        notes.append("Calculated revenue = quantity × unit_price × (1 − discount).")

    if "cost" not in out.columns and {"quantity", "unit_cost"}.issubset(out.columns):
        out["cost"] = (out["quantity"] * out["unit_cost"]).round(2)
        notes.append("Calculated cost = quantity × unit_cost.")

    if "profit" not in out.columns and {"revenue", "cost"}.issubset(out.columns):
        out["profit"] = (out["revenue"] - out["cost"]).round(2)
        notes.append("Calculated profit = revenue − cost.")

    return out, notes


def validate_dataset(df: pd.DataFrame) -> dict[str, Any]:
    missing_required = [c for c in REQUIRED_FOR_BUSINESS if c not in df.columns]
    has_money = any(c in df.columns for c in PRICE_OR_REVENUE)
    has_profit_inputs = any(c in df.columns for c in COST_OR_PROFIT)
    has_inventory = INVENTORY_COL in df.columns

    errors: list[str] = []
    warnings: list[str] = []

    if df.empty:
        errors.append("The dataset has no rows.")
    if len(df.columns) == 0:
        errors.append("The dataset has no columns.")
    if missing_required:
        errors.append(
            "Missing required business columns: "
            + ", ".join(missing_required)
            + ". Need at least: date, product, quantity."
        )
    if not has_money:
        errors.append("Need unit_price or revenue to calculate sales.")
    if not has_profit_inputs:
        warnings.append("No unit_cost / cost / profit column. Profit KPIs will be unavailable.")
    if not has_inventory:
        warnings.append("No inventory column. Stockout recommendations will be unavailable.")
    if "date" in df.columns and df["date"].notna().sum() == 0:
        errors.append("The date column could not be parsed. Use YYYY-MM-DD.")

    dtypes = {str(c): str(t) for c, t in df.dtypes.items()}
    missing_by_col = {str(c): int(df[c].isna().sum()) for c in df.columns}

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "column_names": [str(c) for c in df.columns],
        "dtypes": dtypes,
        "missing_values": int(df.isna().sum().sum()),
        "missing_by_column": missing_by_col,
        "duplicate_rows": int(len(df) - len(df.drop_duplicates())) if len(df) else 0,
        "business_ready": len(errors) == 0,
        "has_profit": "profit" in df.columns,
        "has_inventory": has_inventory,
    }


def load_table_from_bytes(file_name: str, file_bytes: bytes) -> tuple[pd.DataFrame | None, str | None]:
    name = file_name.lower()
    try:
        buffer = BytesIO(file_bytes)
        if name.endswith(".csv"):
            df = pd.read_csv(buffer)
        elif name.endswith(".xlsx") or name.endswith(".xls"):
            df = pd.read_excel(buffer)
        else:
            return None, f"Unsupported file type '{file_name}'. Upload .csv, .xlsx, or .xls."
        return df, None
    except Exception as exc:
        return None, _friendly_read_error(exc, file_name)


def load_table_from_path(path: Path) -> tuple[pd.DataFrame | None, str | None]:
    try:
        data = path.read_bytes()
    except Exception as exc:
        return None, f"Could not open sample file at {path}: {exc}"
    return load_table_from_bytes(path.name, data)


def prepare_dataset(raw_df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any], list[str]]:
    notes: list[str] = []
    df, rename_notes = canonicalize_columns(raw_df)
    notes.extend(rename_notes)
    df, calc_notes = enrich_calculated_columns(df)
    notes.extend(calc_notes)
    report = validate_dataset(df)
    return df, report, notes