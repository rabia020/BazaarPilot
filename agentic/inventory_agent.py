import pandas as pd

REORDER_COVER_DAYS = 14
SAFETY_STOCK_DAYS = 3
CRITICAL_DAYS = 3
LOW_DAYS = 7


def _find_column(df, candidates):
    lower_map = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand in lower_map:
            return lower_map[cand]
    return None


def compute_inventory_table(df):
    """Returns per-product inventory rows. Shared by inventory_agent and
    recommendation_agent so both use identical stockout math."""
    if df is None or len(df) == 0:
        return []

    product_col = _find_column(df, ["product"])
    qty_col = _find_column(df, ["quantity", "qty", "units_sold"])
    inv_col = _find_column(df, ["inventory", "stock", "current_stock"])
    date_col = _find_column(df, ["date"])

    if not product_col or not qty_col or not inv_col:
        return []

    cols = [product_col, qty_col, inv_col] + ([date_col] if date_col else [])
    work = df[cols].copy()
    work[qty_col] = pd.to_numeric(work[qty_col], errors="coerce").fillna(0)
    work[inv_col] = pd.to_numeric(work[inv_col], errors="coerce").fillna(0)

    if date_col:
        work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
        valid_dates = work[date_col].dropna()
        total_days = max((valid_dates.max() - valid_dates.min()).days + 1, 1) if not valid_dates.empty else 1
    else:
        total_days = int(work[product_col].value_counts().max() or 1)

    results = []
    for product, group in work.groupby(product_col):
        total_qty = group[qty_col].sum()
        avg_daily_sales = total_qty / total_days if total_days else 0

        if date_col and group[date_col].notna().any():
            current_stock = group.sort_values(date_col).iloc[-1][inv_col]
        else:
            current_stock = group[inv_col].iloc[-1]

        if avg_daily_sales > 0:
            days_until_stockout = round(current_stock / avg_daily_sales, 1)
        else:
            days_until_stockout = None

        if days_until_stockout is None:
            risk = "Healthy"
        elif days_until_stockout < CRITICAL_DAYS:
            risk = "Critical"
        elif days_until_stockout < LOW_DAYS:
            risk = "Low"
        else:
            risk = "Healthy"

        target_cover = REORDER_COVER_DAYS + SAFETY_STOCK_DAYS
        recommended_reorder = max(0, round(avg_daily_sales * target_cover - current_stock))

        results.append({
            "product": product,
            "current_stock": round(float(current_stock), 1),
            "avg_daily_sales": round(float(avg_daily_sales), 2),
            "days_until_stockout": days_until_stockout if days_until_stockout is not None else "N/A",
            "risk": risk,
            "recommended_reorder": int(recommended_reorder),
        })

    results.sort(key=lambda r: r["days_until_stockout"] if isinstance(r["days_until_stockout"], (int, float)) else 9999)
    return results


def inventory_agent_node(state):
    df = state.get("_df")
    if df is None or len(df) == 0:
        text = "No dataset is loaded, so inventory levels cannot be calculated."
        return {"analysis": text, "sql_result": [], "sql": "", "sql_error": ""}

    product_col = _find_column(df, ["product"])
    qty_col = _find_column(df, ["quantity", "qty", "units_sold"])
    inv_col = _find_column(df, ["inventory", "stock", "current_stock"])

    missing = [name for name, col in
               [("product", product_col), ("quantity", qty_col), ("inventory", inv_col)] if col is None]
    if missing:
        text = (
            "Inventory analysis needs product, quantity, and inventory columns, "
            f"but this dataset is missing: {', '.join(missing)}."
        )
        return {"analysis": text, "sql_result": [], "sql": "", "sql_error": ""}

    results = compute_inventory_table(df)

    critical = [r for r in results if r["risk"] == "Critical"]
    low = [r for r in results if r["risk"] == "Low"]

    summary_lines = [f"Inventory checked for {len(results)} product(s)."]
    if critical:
        summary_lines.append(
            f"Critical stock risk (may run out within {CRITICAL_DAYS} days): "
            + ", ".join(r["product"] for r in critical) + "."
        )
    if low:
        summary_lines.append(
            f"Low stock risk (within {LOW_DAYS} days): "
            + ", ".join(r["product"] for r in low) + "."
        )
    if not critical and not low:
        summary_lines.append("No products are currently at critical or low stock risk.")
    summary_lines.append(
        f"Formula: days_until_stockout = current_inventory / average_daily_sales. "
        f"Recommended reorder covers {REORDER_COVER_DAYS} days of expected sales "
        f"plus a {SAFETY_STOCK_DAYS}-day safety buffer, minus current stock."
    )

    return {
        "analysis": " ".join(summary_lines),
        "sql_result": results,
        "sql": "",
        "sql_error": "",
    }