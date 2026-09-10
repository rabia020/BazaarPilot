"""
report_generator.py
Day 3 Morning: Assembles everything the app has produced — executive summary,
data quality, anomalies, recommendations, and the Q&A conversation history —
into a single downloadable Markdown report.
"""

from datetime import datetime

import pandas as pd


def build_markdown_report(
    dataset_name: str,
    profile_stats: dict,
    column_profile_df: pd.DataFrame,
    executive_summary: str,
    recommendations: str,
    anomaly_summary_df: pd.DataFrame,
    anomaly_explanation: str,
    chat_history: list,
) -> str:
    lines = []
    lines.append(f"# Analytics Report — {dataset_name}")
    lines.append(f"_Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}_")
    lines.append("")

    lines.append("## Executive Summary")
    lines.append(executive_summary or "_Not generated yet — visit the Overview tab._")
    lines.append("")

    lines.append("## Dataset Overview")
    lines.append(f"- Rows: {profile_stats['row_count']:,}")
    lines.append(f"- Columns: {profile_stats['column_count']:,}")
    lines.append(f"- Missing values: {profile_stats['missing_values']:,}")
    lines.append(f"- Duplicate rows: {profile_stats['duplicate_rows']:,}")
    lines.append("")

    lines.append("## Data Quality")
    lines.append(column_profile_df.to_markdown(index=False))
    lines.append("")

    lines.append("## Anomalies")
    if anomaly_summary_df is not None and not anomaly_summary_df.empty:
        lines.append(anomaly_summary_df.to_markdown(index=False))
    else:
        lines.append("No anomalies detected.")
    lines.append("")

    if anomaly_explanation:
        lines.append("### Anomaly Explanation")
        lines.append(anomaly_explanation)
        lines.append("")

    lines.append("## Recommendations")
    lines.append(recommendations or "_Not generated yet — visit the Insights tab._")
    lines.append("")

    if chat_history:
        lines.append("## Q&A History (AI Analysis)")
        for i, turn in enumerate(chat_history, 1):
            lines.append(f"**Q{i}: {turn['question']}**")
            lines.append(f"_Route: {turn.get('route', 'unknown')}_")
            if turn.get("sql"):
                lines.append(f"```sql\n{turn['sql']}\n```")
            lines.append(turn.get("answer", ""))
            lines.append("")

    return "\n".join(lines)
