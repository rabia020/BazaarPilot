import pandas as pd
from .inventory_agent import compute_inventory_table, _find_column

RECENT_WINDOW_DAYS = 7
TREND_DROP_THRESHOLD_PCT = -30


def _profit_margins(df):
    product_col = _find_column(df, ["product"])
    revenue_col = _find_column(df, ["revenue"])
    profit_col = _find_column(df, ["profit"])
    if not product_col or not revenue_col or not profit_col:
        return {}
    work = df[[product_col, revenue_col, profit_col]].copy()
    work[revenue_col] = pd.to_numeric(work[revenue_col], errors="coerce").fillna(0)
    work[profit_col] = pd.to_numeric(work[profit_col], errors="coerce").fillna(0)
    grouped = work.groupby(product_col).sum(numeric_only=True)
    margins = {}
    for product, row in grouped.iterrows():
        rev = row[revenue_col]
        margins[product] = (row[profit_col] / rev) if rev else 0.0
    return margins


def _sales_trend(df):
    """Recent vs baseline avg daily quantity per product (same method as anomaly_agent)."""
    product_col = _find_column(df, ["product"])
    date_col = _find_column(df, ["date"])
    qty_col = _find_column(df, ["quantity", "qty", "units_sold"])
    if not (product_col and date_col and qty_col):
        return {}
    work = df[[product_col, date_col, qty_col]].copy()
    work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
    work[qty_col] = pd.to_numeric(work[qty_col], errors="coerce").fillna(0)
    work = work.dropna(subset=[date_col])
    if work.empty:
        return {}
    daily = work.groupby([product_col, date_col])[qty_col].sum().reset_index()
    max_date = daily[date_col].max()
    cutoff = max_date - pd.Timedelta(days=RECENT_WINDOW_DAYS)
    trends = {}
    for product, group in daily.groupby(product_col):
        recent = group[group[date_col] > cutoff][qty_col]
        baseline = group[group[date_col] <= cutoff][qty_col]
        if len(recent) == 0 or len(baseline) < 3:
            continue
        baseline_avg = float(baseline.mean())
        recent_avg = float(recent.mean())
        if baseline_avg == 0:
            continue
        trends[product] = round((recent_avg - baseline_avg) / baseline_avg * 100, 1)
    return trends


def _category_trend(df):
    category_col = _find_column(df, ["category"])
    date_col = _find_column(df, ["date"])
    profit_col = _find_column(df, ["profit"])
    if not (category_col and date_col and profit_col):
        return []
    work = df[[category_col, date_col, profit_col]].copy()
    work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
    work[profit_col] = pd.to_numeric(work[profit_col], errors="coerce").fillna(0)
    work = work.dropna(subset=[date_col])
    if work.empty:
        return []
    midpoint = work[date_col].min() + (work[date_col].max() - work[date_col].min()) / 2
    p1 = work[work[date_col] <= midpoint].groupby(category_col)[profit_col].sum()
    p2 = work[work[date_col] > midpoint].groupby(category_col)[profit_col].sum()
    declines = []
    for cat in set(p1.index) | set(p2.index):
        v1, v2 = float(p1.get(cat, 0)), float(p2.get(cat, 0))
        if v1 <= 0:
            continue
        pct = (v2 - v1) / v1 * 100
        if pct <= TREND_DROP_THRESHOLD_PCT:
            declines.append({"category": cat, "pct_change": round(pct, 1)})
    declines.sort(key=lambda r: r["pct_change"])
    return declines


def recommendation_agent_node(state):
    df = state.get("_df")
    if df is None or len(df) == 0:
        text = "No dataset is loaded, so recommendations cannot be generated."
        return {"analysis": text, "sql_result": [], "sql": "", "sql_error": ""}

    inventory_rows = compute_inventory_table(df)
    margins = _profit_margins(df)
    trends = _sales_trend(df)
    declining_categories = _category_trend(df)

    inv_by_product = {r["product"]: r for r in inventory_rows}
    margin_values = [v for v in margins.values() if v]
    median_margin = sorted(margin_values)[len(margin_values) // 2] if margin_values else 0

    recommendations = []

    for row in inventory_rows:
        if row["risk"] in ("Critical", "Low"):
            recommendations.append({
                "action": "Reorder",
                "target": row["product"],
                "reason": f"{row['days_until_stockout']} days until stockout (risk: {row['risk']}).",
                "suggested_quantity": row["recommended_reorder"],
                "priority": 1 if row["risk"] == "Critical" else 2,
            })

    for product, pct in trends.items():
        if pct <= -30:
            recommendations.append({
                "action": "Investigate",
                "target": product,
                "reason": f"Recent sales dropped {abs(pct)}% vs baseline.",
                "suggested_quantity": None,
                "priority": 2,
            })

    for product, margin in margins.items():
        row = inv_by_product.get(product)
        trend = trends.get(product, 0)
        if row and margin >= median_margin and trend >= 20 and row["risk"] != "Critical":
            recommendations.append({
                "action": "Increase inventory",
                "target": product,
                "reason": f"Sales trending up {trend}% with {margin*100:.1f}% profit margin.",
                "suggested_quantity": None,
                "priority": 3,
            })

    for dec in declining_categories:
        recommendations.append({
            "action": "Review category",
            "target": dec["category"],
            "reason": f"Category profit declined {abs(dec['pct_change'])}% between the two halves of the dataset.",
            "suggested_quantity": None,
            "priority": 3,
        })

    recommendations.sort(key=lambda r: r["priority"])

    if recommendations:
        lines = [f"Generated {len(recommendations)} recommendation(s):"]
        for r in recommendations[:6]:
            qty_note = f" (~{r['suggested_quantity']} units)" if r["suggested_quantity"] else ""
            lines.append(f"{r['action']} {r['target']}{qty_note} — {r['reason']}")
        text = " ".join(lines)
    else:
        text = "No specific actions are recommended right now — inventory, sales, and profit trends all look healthy."

    return {
        "sql_result": recommendations,
        "sql": "",
        "sql_error": "",
        "analysis": text,
    }