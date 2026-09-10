"""
anomaly.py
Day 3: Basic anomaly detection on numeric columns using IQR and Z-score methods.

Both are simple statistical methods (no ML training needed):
- IQR: flags values far outside the middle 50% of the data. Robust to extreme outliers.
- Z-score: flags values far from the mean in units of standard deviation. Sensitive to
  extreme outliers skewing the mean/std themselves, but simple and widely understood.
"""

import numpy as np
import pandas as pd


def detect_anomalies_iqr(df: pd.DataFrame, column: str, multiplier: float = 1.5) -> pd.DataFrame:
    """
    Flags rows as anomalies using the IQR (interquartile range) method.
    A value is an outlier if it falls below Q1 - multiplier*IQR or above Q3 + multiplier*IQR.
    """
    series = df[column].dropna()
    if series.empty:
        return df.iloc[0:0].copy()

    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - multiplier * iqr
    upper_bound = q3 + multiplier * iqr

    mask = (df[column] < lower_bound) | (df[column] > upper_bound)
    result = df[mask].copy()
    result["anomaly_reason"] = np.where(
        df.loc[mask, column] < lower_bound,
        f"{column} below {lower_bound:.2f}",
        f"{column} above {upper_bound:.2f}",
    )
    return result


def detect_anomalies_zscore(df: pd.DataFrame, column: str, threshold: float = 3.0) -> pd.DataFrame:
    """
    Flags rows as anomalies using the Z-score method.
    A value is an outlier if its absolute z-score exceeds the threshold (default 3 std devs).
    """
    series = df[column]
    mean = series.mean()
    std = series.std()

    if std == 0 or pd.isna(std):
        return df.iloc[0:0].copy()  # no variance in the column, nothing to flag

    z_scores = (series - mean) / std
    mask = z_scores.abs() > threshold

    result = df[mask].copy()
    result["z_score"] = z_scores[mask].round(2)
    return result


def get_anomaly_summary(df: pd.DataFrame, method: str = "iqr", **kwargs) -> pd.DataFrame:
    """
    Runs anomaly detection across every numeric column and returns a summary table:
    column, anomaly_count, anomaly_%. Sorted by anomaly_count descending.

    kwargs are passed through to the underlying detector
    (e.g. multiplier=1.5 for iqr, threshold=3.0 for zscore).
    """
    numeric_columns = df.select_dtypes(include="number").columns
    rows = []

    for column in numeric_columns:
        if method == "zscore":
            anomalies = detect_anomalies_zscore(df, column, **kwargs)
        else:
            anomalies = detect_anomalies_iqr(df, column, **kwargs)

        rows.append(
            {
                "column": column,
                "anomaly_count": len(anomalies),
                "anomaly_%": round((len(anomalies) / len(df)) * 100, 2) if len(df) else 0,
            }
        )

    summary_df = pd.DataFrame(rows)
    if summary_df.empty:
        return summary_df
    return summary_df.sort_values("anomaly_count", ascending=False).reset_index(drop=True)