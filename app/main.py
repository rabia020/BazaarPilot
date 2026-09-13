import io
import sys
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from profiler import profile_dataset, profile_columns, get_sample_rows
from file_loader import load_table_from_bytes, load_table_from_path, prepare_dataset
from charts import (
    plot_numeric_distribution,
    plot_categorical_counts,
    plot_correlation_heatmap,
    plot_metric_over_time,
    plot_top_products_bar,
    plot_category_bar,
)
from business_metrics import (
    compute_business_profile,
    revenue_over_time,
    profit_over_time,
    top_products,
    category_performance,
    money,
)
from anomaly import detect_anomalies_iqr, detect_anomalies_zscore, get_anomaly_summary
from ai_insights import generate_executive_summary, generate_recommendations, explain_anomalies
from report_generator import build_markdown_report
import theme

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from agentic.graph import build_graph
from agentic.inventory_agent import compute_inventory_table
from agentic.anomaly_agent import anomaly_agent_node
from duckdb_manager import connect_sales

load_dotenv()
st.set_page_config(page_title="BazaarPilot — AI Business Co-Pilot", page_icon="🛒", layout="wide")
theme.inject_css()

# ---------------------------------------------------------------------------
# Sidebar: brand block (top) + pipeline checklist + source file
# ---------------------------------------------------------------------------
SAMPLE_PATH = ROOT / "data" / "sample_sales.csv"

if "use_sample" not in st.session_state:
    st.session_state.use_sample = False

with st.sidebar:
    theme.sidebar_brand("BazaarPilot", "AI BUSINESS CO-PILOT")
    if st.button("Load sample sales dataset", use_container_width=True):
        st.session_state.use_sample = True
    uploaded_file = st.file_uploader(
        "Upload a CSV or Excel file",
        type=["csv", "xlsx", "xls"],
        label_visibility="collapsed",
    )

raw_df = None
file_name = None
load_error = None

if uploaded_file is not None:
    st.session_state.use_sample = False
    file_name = uploaded_file.name
    raw_df, load_error = load_table_from_bytes(file_name, uploaded_file.getvalue())
elif st.session_state.use_sample:
    raw_df, load_error = load_table_from_path(SAMPLE_PATH)
    file_name = SAMPLE_PATH.name

if file_name is None:
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
    st.info("Upload a CSV or Excel file, or click **Load sample sales dataset** in the sidebar.")
    st.stop()

if load_error:
    st.error(load_error)
    st.stop()

df, validation, prep_notes = prepare_dataset(raw_df)
size_kb = 0.0
if uploaded_file is not None:
    size_kb = len(uploaded_file.getvalue()) / 1024
elif SAMPLE_PATH.exists():
    size_kb = SAMPLE_PATH.stat().st_size / 1024
file_type = "CSV dataset" if str(file_name).lower().endswith(".csv") else "Excel dataset"

if not validation["ok"]:
    st.error("This file could not be used as a business dataset.")
    for err in validation["errors"]:
        st.error(err)
    if validation.get("column_names"):
        st.write("Columns found:", validation["column_names"])
    st.stop()

for warning in validation["warnings"]:
    st.warning(warning)
if prep_notes:
    with st.expander("How this file was prepared"):
        for note in prep_notes:
            st.write(f"- {note}")

with st.expander("Dataset validation", expanded=False):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", f"{validation['row_count']:,}")
    c2.metric("Columns", f"{validation['column_count']}")
    c3.metric("Missing values", f"{validation['missing_values']:,}")
    c4.metric("Duplicate rows", f"{validation['duplicate_rows']:,}")
    st.write("Column names:", ", ".join(validation["column_names"]))
    dtype_df = pd.DataFrame(
        {"column": list(validation["dtypes"].keys()), "dtype": list(validation["dtypes"].values())}
    )
    st.dataframe(dtype_df, use_container_width=True, hide_index=True)
    missing_df = pd.DataFrame(
        {
            "column": list(validation["missing_by_column"].keys()),
            "missing": list(validation["missing_by_column"].values()),
        }
    )
    st.dataframe(missing_df, use_container_width=True, hide_index=True)
    st.success("Required business columns found: date, product, quantity, plus price/revenue.")

    st.caption("Query engine: DuckDB table `sales` (read-only).")


con = connect_sales(df)
# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if st.session_state.get("_current_file") != file_name:
    st.session_state._current_file = file_name
    st.session_state.chat_history = []
    st.session_state.executive_summary = ""
    st.session_state.recommendations = ""
    st.session_state.anomaly_explanation = ""
    st.session_state.pending_actions = []
    st.session_state.action_log = []

stats = profile_dataset(con, df)
column_profile_df = profile_columns(con, df)
numeric_cols_all = df.select_dtypes(include="number").columns.tolist()
biz = compute_business_profile(df)
rev_ts = revenue_over_time(df)
profit_ts = profit_over_time(df)
top_rev = top_products(df, "revenue", 10)
top_profit = top_products(df, "profit", 10)
cat_perf = category_performance(df)

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

tab_overview, tab_quality, tab_ai, tab_charts, tab_anomalies, tab_insights, tab_inventory, tab_approvals = st.tabs(
    ["Overview", "Data quality", "AI analysis", "Charts", "Anomalies", "Insights", "Inventory", "Approvals"]
)

# --- Overview -----------------------------------------------------------------
with tab_overview:
    date_note = "Date range unavailable"
    if biz["date_min"] and biz["date_max"]:
        date_note = f"{biz['date_min']} → {biz['date_max']}"

    r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns(5)
    with r1c1:
        theme.metric_card("REVENUE", money(biz["total_revenue"]), date_note)
    with r1c2:
        theme.metric_card("PROFIT", money(biz["total_profit"]), date_note)
    with r1c3:
        theme.metric_card("QUANTITY SOLD", f"{biz['total_quantity']:,.0f}", "Units")
    with r1c4:
        theme.metric_card("PRODUCTS", f"{biz['product_count']}", f"{biz['category_count']} categories")
    with r1c5:
        theme.metric_card("ROWS", f"{biz['row_count']:,}", f"{biz['column_count']} columns")

        # --- Business Alerts strip ---------------------------------------------
    inventory_rows_overview = compute_inventory_table(df)
    critical_products = [r["product"] for r in inventory_rows_overview if r["risk"] == "Critical"]
    low_products = [r["product"] for r in inventory_rows_overview if r["risk"] == "Low"]

    anomaly_out = anomaly_agent_node({"_df": df})
    anomaly_rows_overview = anomaly_out.get("anomaly_result") or []
    drops = [r for r in anomaly_rows_overview if isinstance(r.get("pct_change"), (int, float)) and r["pct_change"] < 0]
    spikes = [r for r in anomaly_rows_overview if isinstance(r.get("pct_change"), (int, float)) and r["pct_change"] > 0]

    alerts = []
    if critical_products:
        alerts.append(f"🔴 Critical stock: {', '.join(critical_products[:3])}")
    if low_products:
        alerts.append(f"🟠 Low stock: {', '.join(low_products[:3])}")
    if spikes:
        alerts.append(f"📈 Sales increase: {', '.join(r['product'] for r in spikes[:2])}")
    if drops:
        alerts.append(f"📉 Sales decline: {', '.join(r['product'] for r in drops[:2])}")
    if len(anomaly_rows_overview) > len(drops) + len(spikes):
        alerts.append("⚠️ Anomaly detected in numeric columns")

    if alerts:
        st.markdown("#### Business alerts")
        for alert in alerts:
            st.warning(alert)
    else:
        st.success("✅ No critical alerts — inventory and sales trends look healthy.")

    st.write("")

    st.caption(
        f"Cost {money(biz['total_cost'])} · Missing values {biz['missing_values']:,} · "
        f"Duplicate rows {biz['duplicate_rows']:,}"
    )
    st.write("")

    c_left, c_right = st.columns(2)
    with c_left:
        if not rev_ts.empty:
            st.plotly_chart(
                plot_metric_over_time(rev_ts, "date", "revenue", "Revenue over time"),
                use_container_width=True,
                key="rev_time_chart",
            )
        else:
            st.info("Revenue over time needs date and revenue columns.")
    with c_right:
        if not profit_ts.empty:
            st.plotly_chart(
                plot_metric_over_time(profit_ts, "date", "profit", "Profit over time"),
                use_container_width=True,
                key="profit_time_chart",
            )
        else:
            st.info("Profit over time needs date and profit columns.")

    st.write("")
    p_left, p_right = st.columns(2)
    with p_left:
        if not top_rev.empty:
            st.plotly_chart(
                plot_top_products_bar(top_rev, "revenue", "Top products by revenue"),
                use_container_width=True,
                key="top_rev_chart",
            )
            st.dataframe(top_rev, use_container_width=True, hide_index=True)
        else:
            st.info("Top products need product and revenue columns.")
    with p_right:
        if not top_profit.empty:
            st.plotly_chart(
                plot_top_products_bar(top_profit, "profit", "Top products by profit"),
                use_container_width=True,
                key="top_profit_chart",
            )

    st.write("")
    cat_left, cat_right = st.columns(2)
    with cat_left:
        if not cat_perf.empty and "revenue" in cat_perf.columns:
            st.plotly_chart(
                plot_category_bar(cat_perf, "revenue", "Revenue by category"),
                use_container_width=True,
                key="cat_rev_chart",
            )
        else:
            st.info("Category revenue chart needs a category column.")
    with cat_right:
        if not cat_perf.empty and "profit" in cat_perf.columns:
            st.plotly_chart(
                plot_category_bar(cat_perf, "profit", "Profit by category"),
                use_container_width=True,
                key="cat_profit_chart",
            )

    st.write("")

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
    st.markdown("#### Ask a business question")
    st.caption("Numbers come from DuckDB. The AI only explains the query result.")

    question = None
    b1, b2, b3, b4, b5 = st.columns(5)
    if b1.button("Top 10 revenue"):
        question = "What are my top 10 products by revenue?"
    if b2.button("Most profitable"):
        question = "Which products generate the most profit?"
    if b3.button("Best category"):
        question = "Which category performs best?"
    if b4.button("Reorder check"):
        question = "Which products should I reorder?"
    if b5.button("Roman Urdu profit"):
        question = "Meri shop mein sab se zyada profit kis product se aa raha hai?"

    for turn in st.session_state.chat_history:
        with st.chat_message("user"):
            st.write(turn["question"])
        with st.chat_message("assistant"):
            st.caption(f"Agent: `{turn.get('route', 'unknown')}`")
            if turn.get("sql"):
                with st.expander("Generated SQL", expanded=True):
                    st.code(turn["sql"], language="sql")
            if turn.get("sql_error"):
                st.error(turn["sql_error"])
            rows = turn.get("sql_result") or []
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                st.markdown(turn.get("answer", ""), unsafe_allow_html=True)

    typed = st.chat_input("Ask in English or Roman Urdu")
    if typed:
        question = typed

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
                    {
                        "question": question,
                        "route": result.get("route", "unknown"),
                        "sql": result.get("sql", ""),
                        "sql_result": result.get("sql_result") or [],
                        "sql_error": result.get("sql_error") or result.get("error") or "",
                        "answer": answer,
                    }
                )
            except Exception as exc:
                st.session_state.chat_history.append(
                    {
                        "question": question,
                        "route": "error",
                        "sql": "",
                        "sql_result": [],
                        "sql_error": str(exc),
                        "answer": f"Error: {exc}",
                    }
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

# --- Inventory ---------------------------------------------------------------
with tab_inventory:
    st.markdown("#### Inventory & stockout risk")
    st.caption("days_until_stockout = current_inventory / average_daily_sales")
    inventory_rows = compute_inventory_table(df)
    if not inventory_rows:
        st.info("This dataset doesn't have the product/quantity/inventory columns needed for inventory analysis.")
    else:
        inv_df_display = pd.DataFrame(inventory_rows).copy()
        badge = {"Critical": "🔴 Critical", "Low": "🟠 Low", "Healthy": "🟢 Healthy"}
        inv_df_display["risk"] = inv_df_display["risk"].map(lambda r: badge.get(r, r))
        st.dataframe(inv_df_display, use_container_width=True, hide_index=True)

        if st.button("Generate Reorder Recommendations", use_container_width=True):
            at_risk = [r for r in inventory_rows if r["risk"] in ("Critical", "Low")]
            existing = {a["target"] for a in st.session_state.pending_actions}
            logged = {a["target"] for a in st.session_state.action_log}
            added = 0
            for r in at_risk:
                if r["product"] in existing or r["product"] in logged:
                    continue
                st.session_state.pending_actions.append({
                    "action": "Reorder",
                    "target": r["product"],
                    "reason": f"{r['days_until_stockout']} days until stockout (risk: {r['risk']}).",
                    "suggested_quantity": r["recommended_reorder"],
                })
                added += 1
            if added:
                st.success(f"{added} new reorder recommendation(s) added. See the Approvals tab.")
            else:
                st.info("No new at-risk products found (already pending or already actioned).")

# --- Approvals ---------------------------------------------------------------
with tab_approvals:
    st.markdown("#### Pending actions")
    st.caption(
        "AI-proposed actions require human approval before being recorded. "
        "This is a simulated action log — no real orders or inventory changes are made."
    )

    if not st.session_state.pending_actions:
        st.info(
            "No pending actions. Go to the **Inventory** tab and click "
            "**Generate Reorder Recommendations**, or ask the AI Analyst "
            "\"Which products should I reorder?\"."
        )
    else:
        for i, action in enumerate(list(st.session_state.pending_actions)):
            with st.container(border=True):
                st.markdown(f"**{action['action']}: {action['target']}**")
                if action.get("suggested_quantity"):
                    st.write(f"Suggested quantity: {action['suggested_quantity']} units")
                st.caption(action["reason"])
                c1, c2 = st.columns(2)
                if c1.button("✅ Approve", key=f"approve_{i}_{action['target']}"):
                    st.session_state.action_log.append({**action, "status": "Approved"})
                    st.session_state.pending_actions.remove(action)
                    st.rerun()
                if c2.button("❌ Reject", key=f"reject_{i}_{action['target']}"):
                    st.session_state.action_log.append({**action, "status": "Rejected"})
                    st.session_state.pending_actions.remove(action)
                    st.rerun()

    st.divider()
    st.markdown("#### Activity log")
    if st.session_state.action_log:
        st.dataframe(pd.DataFrame(st.session_state.action_log), use_container_width=True, hide_index=True)
    else:
        st.caption("No actions approved or rejected yet.")

con.close()