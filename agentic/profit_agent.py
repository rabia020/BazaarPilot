import pandas as pd
from .sql_agent import sql_agent_node

WHY_KEYWORDS_LATIN = [
    "why", "decrease", "decreased", "increase", "increased", "change", "changed",
    "compare", "comparison", "kam ho", "kam hui", "kyun", "kyu", "badal", "kis wajah",
]

# Urdu-script equivalents: کیوں (why), کم (less/decrease), کمی (decrease/reduction),
# بڑھ/اضافہ (increase), تبدیل/فرق (change), موازنہ (compare)
WHY_KEYWORDS_URDU = [
    "کیوں", "کیا وجہ", "کم", "کمی", "بڑھ", "اضافہ", "تبدیل", "فرق", "موازنہ",
]


def _find_column(df, candidates):
    lower_map = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand in lower_map:
            return lower_map[cand]
    return None


def _is_why_question(question: str) -> bool:
    if any(k in question for k in WHY_KEYWORDS_URDU):
        return True
    q = question.lower()
    return any(k in q for k in WHY_KEYWORDS_LATIN)


def profit_agent_node(state):
    question = state.get("question", "")

    # Ranking/total questions ("which product is most profitable") keep using
    # the existing SQL agent — unchanged behavior from Phase 5/6.
    if not _is_why_question(question):
        return sql_agent_node(state)

    df = state.get("_df")
    if df is None or len(df) == 0:
        return {"analysis": "No dataset is loaded.", "sql_result": [], "sql": "", "sql_error": ""}

    date_col = _find_column(df, ["date"])
    profit_col = _find_column(df, ["profit"])
    category_col = _find_column(df, ["category"])
    product_col = _find_column(df, ["product"])

    if not date_col or not profit_col:
        text = "Profit trend analysis needs date and profit columns, which are missing from this dataset."
        return {"analysis": text, "sql_result": [], "sql": "", "sql_error": ""}

    work = df.copy()
    work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
    work = work.dropna(subset=[date_col])
    work[profit_col] = pd.to_numeric(work[profit_col], errors="coerce").fillna(0)

    if work.empty:
        return {"analysis": "No valid dated rows found for profit trend analysis.", "sql_result": [], "sql": "", "sql_error": ""}

    work = work.sort_values(date_col)
    midpoint = work[date_col].min() + (work[date_col].max() - work[date_col].min()) / 2
    period1 = work[work[date_col] <= midpoint]
    period2 = work[work[date_col] > midpoint]

    p1_total = float(period1[profit_col].sum())
    p2_total = float(period2[profit_col].sum())
    change = p2_total - p1_total
    pct_change = (change / p1_total * 100) if p1_total else None

    breakdown_col = category_col or product_col
    results = []
    if breakdown_col:
        g1 = period1.groupby(breakdown_col)[profit_col].sum()
        g2 = period2.groupby(breakdown_col)[profit_col].sum()
        for key in set(g1.index) | set(g2.index):
            v1 = float(g1.get(key, 0))
            v2 = float(g2.get(key, 0))
            results.append({
                breakdown_col: key,
                "period1_profit": round(v1, 2),
                "period2_profit": round(v2, 2),
                "change": round(v2 - v1, 2),
            })
        results.sort(key=lambda r: r["change"])

    p1_start = period1[date_col].min().date() if not period1.empty else "N/A"
    p1_end = period1[date_col].max().date() if not period1.empty else "N/A"
    p2_start = period2[date_col].min().date() if not period2.empty else "N/A"
    p2_end = period2[date_col].max().date() if not period2.empty else "N/A"

    summary = [
        f"Period 1 ({p1_start} to {p1_end}) profit: {p1_total:.2f}.",
        f"Period 2 ({p2_start} to {p2_end}) profit: {p2_total:.2f}.",
    ]
    if pct_change is not None:
        direction = "increased" if change > 0 else "decreased" if change < 0 else "stayed flat"
        summary.append(f"Overall profit {direction} by {abs(pct_change):.1f}% ({change:+.2f}).")
    else:
        summary.append(f"Overall profit changed by {change:+.2f} (period 1 total was zero, percent change unavailable).")

    if results:
        biggest_drop = results[0]
        biggest_gain = results[-1]
        if biggest_drop["change"] < 0:
            summary.append(
                f"Largest negative contributor: {breakdown_col} '{biggest_drop[breakdown_col]}' "
                f"(change {biggest_drop['change']:+.2f})."
            )
        if biggest_gain["change"] > 0 and biggest_gain != biggest_drop:
            summary.append(
                f"Largest positive contributor: {breakdown_col} '{biggest_gain[breakdown_col]}' "
                f"(change {biggest_gain['change']:+.2f}), partially offsetting the decline."
            )

    return {
        "analysis": " ".join(summary),
        "sql_result": results,
        "sql": "",
        "sql_error": "",
    }