import io
import sys
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from profiler import profile_dataset, profile_columns, get_sample_rows
from charts import plot_numeric_distribution, plot_categorical_counts, plot_correlation_heatmap
from anomaly import detect_anomalies_iqr, detect_anomalies_zscore, get_anomaly_summary
from ai_insights import generate_executive_summary, generate_recommendations, explain_anomalies
from report_generator import build_markdown_report
import theme

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from agentic.graph import build_graph

load_dotenv()
st.set_page_config(page_title="Vectorfield — AI Analytics Engine", page_icon="📊", layout="wide")
theme.inject_css()

# ---------------------------------------------------------------------------
# Sidebar: brand block (top) + pipeline checklist + source file
# ---------------------------------------------------------------------------
with st.sidebar:
    theme.sidebar_brand("Vectorfield", "AI ANALYTICS ENGINE")
    uploaded_file = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx", "xls"], label_visibility="collapsed")

if uploaded_file is None:
    with st.sidebar:
        theme.pipeline_sidebar(
            [
                ("Upload", "pending"),
                ("Profile", "pending"),
                ("Ask questions", "pending"),
                ("Visualize", "pending"),
                ("Detect anomalies", "pending"),
                ("Report", "pending"),
            ]
        )
    st.info("Upload a CSV or Excel dataset in the sidebar to start.")
    st.stop()

file_name = uploaded_file.name
file_bytes = uploaded_file.getvalue()
size_kb = len(file_bytes) / 1024
file_type = "CSV dataset" if file_name.lower().endswith(".csv") else "Excel dataset"

try:
    if file_name.lower().endswith(".csv"):
        df = pd.read_csv(io.BytesIO(file_bytes))
    else:
        df = pd.read_excel(io.BytesIO(file_bytes))
except Exception as exc:
    st.error(f"Could not read the file: {exc}")
    st.stop()

if df.empty:
    st.warning("The uploaded dataset is empty.")
    st.stop()

con = duckdb.connect(database=":memory:")
con.register("uploaded_data", df)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if st.session_state.get("_current_file") != file_name:
    st.session_state._current_file = file_name
    st.session_state.chat_history = []
    st.session_state.executive_summary = ""
    st.session_state.recommendations = ""
    st.session_state.anomaly_explanation = ""

stats = profile_dataset(con, df)
column_profile_df = profile_columns(con, df)
numeric_cols_all = df.select_dtypes(include="number").columns.tolist()

# Data quality scores (all derived from real computed stats — nothing fabricated)
total_cells = stats["row_count"] * stats["column_count"]
completeness_pct = 100 * (1 - stats["missing_values"] / total_cells) if total_cells else 100.0
consistency_pct = 100 * (1 - stats["duplicate_rows"] / stats["row_count"]) if stats["row_count"] else 100.0
default_anomaly_summary = get_anomaly_summary(df, method="iqr", multiplier=1.5)
if not default_anomaly_summary.empty:
    clean_cols = (default_anomaly_summary["anomaly_count"] == 0).sum()
    validity_pct = 100 * clean_cols / len(default_anomaly_summary)
else:
    validity_pct = 100.0

with st.sidebar:
    theme.pipeline_sidebar(
        [
            ("Upload", "done"),
            ("Profile", "done"),
            ("Ask questions", "done" if st.session_state.chat_history else "ready"),
            ("Visualize", "ready"),
            ("Detect anomalies", "done" if st.session_state.anomaly_explanation else "ready"),
            ("Report", "ready"),
        ]
    )
    theme.sidebar_section_label("SOURCE FILE")
    theme.file_card(file_name, size_kb, file_type)
    with st.expander("↑ Replace file"):
        st.file_uploader("Replace file", type=["csv", "xlsx", "xls"], key="replace_uploader", label_visibility="collapsed")
    insights_ready = sum(
        bool(x) for x in [st.session_state.executive_summary, st.session_state.recommendations, st.session_state.anomaly_explanation]
    )
    theme.success_banner(
        f"Analysis complete — {insights_ready} insight(s) ready" if insights_ready else "Upload complete — generate insights in the tabs"
    )

# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------
title_col, export_col = st.columns([4, 1])
with title_col:
    st.markdown("## Dataset overview")
    st.caption(f"{file_name} · {stats['row_count']:,} records · {stats['column_count']} fields")
with export_col:
    report_text_preview = build_markdown_report(
        dataset_name=file_name,
        profile_stats=stats,
        column_profile_df=column_profile_df,
        executive_summary=st.session_state.executive_summary,
        recommendations=st.session_state.recommendations,
        anomaly_summary_df=default_anomaly_summary,
        anomaly_explanation=st.session_state.anomaly_explanation,
        chat_history=st.session_state.chat_history,
    )
    st.download_button(
        "Export report",
        data=report_text_preview,
        file_name=f"analytics_report_{file_name.rsplit('.', 1)[0]}.md",
        mime="text/markdown",
        use_container_width=True,
    )

tab_overview, tab_quality, tab_ai, tab_charts, tab_anomalies, tab_insights = st.tabs(
    ["Overview", "Data quality", "AI analysis", "Charts", "Anomalies", "Insights"]
)

# --- Overview -----------------------------------------------------------------
with tab_overview:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        theme.metric_card("ROWS", f"{stats['row_count']:,}", "Complete scan")
    with c2:
        theme.metric_card("COLUMNS", f"{stats['column_count']}", f"{len(numeric_cols_all)} numeric")
    with c3:
        missing_pct = 100 * stats["missing_values"] / total_cells if total_cells else 0
        theme.metric_card("MISSING VALUES", f"{stats['missing_values']:,}", f"{missing_pct:.1f}% of cells")
    with c4:
        dup_note = "No conflicts" if stats["duplicate_rows"] == 0 else "Review duplicates"
        theme.metric_card("DUPLICATES", f"{stats['duplicate_rows']:,}", dup_note)

    st.write("")
    st.markdown("#### Dataset distribution")
    if numeric_cols_all:
        default_col = numeric_cols_all[0]
        st.plotly_chart(plot_numeric_distribution(df, default_col), use_container_width=True, key="overview_dist_chart")
    else:
        st.info("No numeric columns available to chart here — see the Charts tab for categorical breakdowns.")

    left, right = st.columns([1, 1])
    with left:
        st.markdown("#### Data quality")
        theme.progress_row("Completeness", completeness_pct)
        theme.progress_row("Consistency", consistency_pct)
        theme.progress_row("Validity", validity_pct)
        st.caption("Validity = share of numeric columns with zero flagged anomalies (IQR method).")

    with right:
        st.markdown("#### AI insight")
        if st.button("Generate Executive Summary", use_container_width=True):
            with st.spinner("Summarizing..."):
                try:
                    st.session_state.executive_summary = generate_executive_summary(stats, column_profile_df)
                except Exception as exc:
                    st.error(f"Could not generate summary: {exc}")
        if st.session_state.executive_summary:
            theme.ai_insight_box(st.session_state.executive_summary)
        else:
            st.caption("Generate a summary to see it here.")

    with st.expander("Data preview"):
        st.dataframe(get_sample_rows(con), use_container_width=True, hide_index=True)

# --- Data Quality ---------------------------------------------------------------
with tab_quality:
    st.markdown("#### Column profile")
    st.dataframe(column_profile_df, use_container_width=True, hide_index=True)

    st.markdown("#### Summary statistics")
    numeric_df = df.select_dtypes(include="number")
    if numeric_df.empty:
        st.info("No numeric columns detected.")
    else:
        summary = numeric_df.describe().T.reset_index().rename(columns={"index": "column"})
        st.dataframe(summary, use_container_width=True, hide_index=True)

# --- AI Analysis --------------------------------------------------------------
with tab_ai:
    st.markdown("#### Ask a question about your data")

    for turn in st.session_state.chat_history:
        with st.chat_message("user"):
            st.write(turn["question"])
        with st.chat_message("assistant"):
            st.caption(f"Route: `{turn.get('route', 'unknown')}`")
            if turn.get("sql"):
                st.code(turn["sql"], language="sql")
            st.write(turn.get("answer", ""))

    question = st.chat_input("e.g. What are the top 5 products by revenue?")
    if question:
        state = {
            "question": question,
            "dataset_name": file_name,
            "columns": [str(c) for c in df.columns],
            "column_types": {str(c): str(t) for c, t in df.dtypes.items()},
            "_df": df,
        }
        with st.spinner("Running agentic workflow..."):
            try:
                result = build_graph().invoke(state)
                answer = result.get("final_answer") or result.get("insights") or ""
                st.session_state.chat_history.append(
                    {"question": question, "route": result.get("route", "unknown"), "sql": result.get("sql", ""), "answer": answer}
                )
            except Exception as exc:
                st.session_state.chat_history.append(
                    {"question": question, "route": "error", "sql": "", "answer": f"Error: {exc}"}
                )
        st.rerun()

# --- Charts ---------------------------------------------------------------------
with tab_charts:
    categorical_cols = df.select_dtypes(exclude="number").columns.tolist()
    chart_tab1, chart_tab2, chart_tab3 = st.tabs(["Distribution", "Category Counts", "Correlation"])

    with chart_tab1:
        if numeric_cols_all:
            col = st.selectbox("Numeric column", numeric_cols_all, key="dist_col")
            st.plotly_chart(plot_numeric_distribution(df, col), use_container_width=True, key="charts_dist_chart")
        else:
            st.info("No numeric columns available.")

    with chart_tab2:
        if categorical_cols:
            col = st.selectbox("Categorical column", categorical_cols, key="cat_col")
            st.plotly_chart(plot_categorical_counts(df, col), use_container_width=True, key="charts_cat_chart")
        else:
            st.info("No categorical columns available.")

    with chart_tab3:
        heatmap = plot_correlation_heatmap(df)
        if heatmap is not None:
            st.plotly_chart(heatmap, use_container_width=True, key="charts_corr_chart")
        else:
            st.info("Need at least 2 numeric columns for a correlation heatmap.")

# --- Anomalies --------------------------------------------------------------------
with tab_anomalies:
    method = st.radio("Detection method", ["IQR (interquartile range)", "Z-score"], horizontal=True)
    method_key = "iqr" if method.startswith("IQR") else "zscore"

    if method_key == "iqr":
        multiplier = st.slider("IQR multiplier (lower = stricter)", 1.0, 3.0, 1.5, 0.1)
        anomaly_summary = get_anomaly_summary(df, method="iqr", multiplier=multiplier)
    else:
        threshold = st.slider("Z-score threshold (lower = stricter)", 1.0, 4.0, 3.0, 0.1)
        anomaly_summary = get_anomaly_summary(df, method="zscore", threshold=threshold)

    st.markdown("#### Summary across numeric columns")
    if anomaly_summary.empty:
        st.info("No numeric columns available for anomaly detection.")
    else:
        st.dataframe(anomaly_summary, use_container_width=True, hide_index=True)

    if st.button("Explain anomalies in plain English"):
        with st.spinner("Explaining..."):
            try:
                st.session_state.anomaly_explanation = explain_anomalies(anomaly_summary, method)
            except Exception as exc:
                st.error(f"Could not generate explanation: {exc}")
    if st.session_state.anomaly_explanation:
        theme.ai_insight_box(st.session_state.anomaly_explanation, tag="ANOMALY EXPLANATION")

    if numeric_cols_all:
        selected_col = st.selectbox("Inspect flagged rows for column", numeric_cols_all, key="anomaly_col")
        flagged = (
            detect_anomalies_iqr(df, selected_col, multiplier=multiplier)
            if method_key == "iqr"
            else detect_anomalies_zscore(df, selected_col, threshold=threshold)
        )
        st.write(f"**{len(flagged)}** anomalous rows found in `{selected_col}`")
        st.dataframe(flagged, use_container_width=True)

# --- Insights ---------------------------------------------------------------------
with tab_insights:
    st.markdown("#### Recommendations")
    if st.button("Generate Recommendations"):
        with st.spinner("Thinking..."):
            try:
                st.session_state.recommendations = generate_recommendations(stats, anomaly_summary, st.session_state.chat_history)
            except Exception as exc:
                st.error(f"Could not generate recommendations: {exc}")
    if st.session_state.recommendations:
        st.markdown(st.session_state.recommendations)

    st.divider()
    st.markdown("#### Downloadable report")
    report_text = build_markdown_report(
        dataset_name=file_name,
        profile_stats=stats,
        column_profile_df=column_profile_df,
        executive_summary=st.session_state.executive_summary,
        recommendations=st.session_state.recommendations,
        anomaly_summary_df=anomaly_summary,
        anomaly_explanation=st.session_state.anomaly_explanation,
        chat_history=st.session_state.chat_history,
    )
    st.download_button("Download Report (Markdown)", data=report_text, file_name=f"analytics_report_{file_name.rsplit('.', 1)[0]}.md", mime="text/markdown")
    with st.expander("Preview report"):
        st.markdown(report_text)

con.close()