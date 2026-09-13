import re
import pandas as pd

RECENT_WINDOW_DAYS = 7
CHANGE_THRESHOLD_PCT = 30  # minimum % deviation from baseline to flag as anomaly

WINDOW_KEYWORDS = {
    "today": 1,
    "yesterday": 2,
    "this week": 7,
    "last week": 7,
    "is hafte": 7,
    "pichle hafte": 7,
    "this month": 30,
    "last month": 30,
    "is mahine": 30,
    "pichle mahine": 30,
    "اس ہفتے": 7,
    "پچھلے ہفتے": 7,
    "اس مہینے": 30,
    "پچھلے مہینے": 30,
}


def _find_column(df, candidates):
    lower_map = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand in lower_map:
            return lower_map[cand]
    return None


def _severity(pct_change: float) -> str:
    pct = abs(pct_change)
    if pct >= 70:
        return "Severe"
    if pct >= 50:
        return "Moderate"
    return "Mild"


def _resolve_window(question: str) -> int:
    """Return a recent-window size in days if the question names a period, else the default."""
    q = question.lower()
    for phrase, days in WINDOW_KEYWORDS.items():
        if phrase in q or phrase in question:
            return days
    return RECENT_WINDOW_DAYS


def _find_named_product(question: str, products) -> str | None:
    """If the question names one of the dataset's actual products, return it (case-insensitive)."""
    q = question.lower()
    for product in products:
        if str(product).lower() in q:
            return product
    return None


def _column_level_outliers(df: pd.DataFrame) -> list:
    """Fallback: simple IQR outlier scan across numeric columns."""
    results = []
    for column in df.select_dtypes(include="number").columns:
        s = df[column].dropna()
        if len(s) < 4:
            continue
        q1, q3 = s.quantile(.25), s.quantile(.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        count = int(((df[column] < lower) | (df[column] > upper)).fillna(False).sum())
        if count:
            results.append({
                "column": str(column),
                "outlier_count": count,
                "lower_bound": round(float(lower), 2),
                "upper_bound": round(float(upper), 2),
            })
    return results


def anomaly_agent_node(state):
    df = state.get("_df")
    question = state.get("question", "") or ""

    if df is None or len(df) == 0:
        text = "No dataset is loaded, so anomaly detection cannot run."
        return {"analysis": text, "anomaly_result": [], "sql_result": [], "sql": "", "sql_error": ""}

    product_col = _find_column(df, ["product"])
    date_col = _find_column(df, ["date"])
    qty_col = _find_column(df, ["quantity", "qty", "units_sold"])
    revenue_col = _find_column(df, ["revenue"])
    metric_col = qty_col or revenue_col
    metric_label = "quantity" if qty_col else "revenue"

    window_days = _resolve_window(question)
    named_product = None

    results = []

    if product_col and metric_col and date_col:
        named_product = _find_named_product(question, df[product_col].dropna().unique())

        work = df[[product_col, date_col, metric_col]].copy()
        work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
        work[metric_col] = pd.to_numeric(work[metric_col], errors="coerce").fillna(0)
        work = work.dropna(subset=[date_col])

        if named_product:
            work = work[work[product_col] == named_product]

        if not work.empty:
            daily = work.groupby([product_col, date_col])[metric_col].sum().reset_index()
            max_date = daily[date_col].max()
            recent_cutoff = max_date - pd.Timedelta(days=window_days)

            for product, group in daily.groupby(product_col):
                recent = group[group[date_col] > recent_cutoff][metric_col]
                baseline = group[group[date_col] <= recent_cutoff][metric_col]

                if len(recent) == 0 or len(baseline) < 3:
                    continue

                recent_avg = float(recent.mean())
                baseline_avg = float(baseline.mean())
                baseline_std = float(baseline.std() or 0)

                if baseline_avg == 0:
                    continue

                pct_change = (recent_avg - baseline_avg) / baseline_avg * 100

                # When a specific product was named, show its status even if
                # the deviation is below the flag threshold — the user asked directly.
                if named_product or abs(pct_change) >= CHANGE_THRESHOLD_PCT:
                    normal_low = round(max(baseline_avg - baseline_std, 0), 1)
                    normal_high = round(baseline_avg + baseline_std, 1)
                    results.append({
                        "product": product,
                        "metric": metric_label,
                        "window_days": window_days,
                        "recent_avg": round(recent_avg, 1),
                        "normal_range": f"{normal_low} - {normal_high}",
                        "pct_change": round(pct_change, 1),
                        "severity": _severity(pct_change) if abs(pct_change) >= CHANGE_THRESHOLD_PCT else "Normal",
                    })

            results.sort(key=lambda r: abs(r["pct_change"]), reverse=True)

    if results:
        if named_product:
            r = results[0]
            if r["severity"] == "Normal":
                text = (
                    f"{r['product']}'s recent {window_days}-day average {metric_label} is {r['recent_avg']}, "
                    f"within its normal range ({r['normal_range']}) — no anomaly detected."
                )
            else:
                direction = "above" if r["pct_change"] > 0 else "below"
                text = (
                    f"{r['product']}'s recent {window_days}-day average {metric_label} is {r['recent_avg']}, "
                    f"{abs(r['pct_change'])}% {direction} its normal range ({r['normal_range']}) — {r['severity']} severity."
                )
        else:
            lines = [f"Detected {len(results)} product(s) with unusual {metric_label} over the last {window_days} day(s):"]
            for r in results[:5]:
                direction = "above" if r["pct_change"] > 0 else "below"
                lines.append(
                    f"{r['product']} was {abs(r['pct_change'])}% {direction} its recent average "
                    f"({r['severity']} severity)."
                )
            text = " ".join(lines)
    else:
        column_outliers = _column_level_outliers(df)
        if column_outliers:
            results = column_outliers
            text = (
                "No unusual per-product sales trends were found, but IQR-based numeric outliers "
                "were detected in: " + ", ".join(x["column"] for x in results) + "."
            )
        else:
            text = "No unusual sales patterns or numeric outliers were detected in the current dataset."

    return {
        "anomaly_result": results,
        "sql_result": results,
        "sql": "",
        "sql_error": "",
        "analysis": text,
    }