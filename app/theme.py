"""
theme.py
"Vectorfield" visual theme: CSS + small HTML-rendering helpers so main.py
can build cards, progress bars, badges, and the AI insight callout without
repeating markup everywhere.
"""

import streamlit as st


def inject_css():
    st.markdown(
        """
        <style>
        :root {
            --vf-bg: #f6f7fb;
            --vf-card-bg: #ffffff;
            --vf-border: #e6e8ef;
            --vf-accent: #2f6fed;
            --vf-accent-soft: #eaf1ff;
            --vf-text: #10131a;
            --vf-text-secondary: #6b7280;
            --vf-label: #9aa4b2;
            --vf-green: #1fae5f;
        }

        .stApp { background-color: var(--vf-bg); }

        /* Sidebar brand block (top of sidebar) */
        .vf-sidebar-brand { display: flex; align-items: center; gap: 10px; margin-bottom: 18px; }
        .vf-logo {
            width: 34px; height: 34px; border-radius: 9px; background: var(--vf-accent);
            color: white; font-weight: 700; font-size: 16px;
            display: flex; align-items: center; justify-content: center; flex-shrink: 0;
        }
        .vf-brand-name { font-weight: 700; font-size: 15px; color: var(--vf-text); line-height: 1.2; }
        .vf-brand-sub {
            font-family: 'Courier New', monospace; font-size: 10px; letter-spacing: 1px;
            color: var(--vf-label); text-transform: uppercase;
        }

        /* Top-right status row in main content */
        .vf-status { font-size: 13px; color: var(--vf-text-secondary); text-align: right; }
        .vf-status-dot {
            display: inline-block; width: 7px; height: 7px; border-radius: 50%;
            background: var(--vf-accent); margin-right: 6px;
        }

        /* Cards */
        .vf-card {
            background: var(--vf-card-bg); border: 1px solid var(--vf-border);
            border-radius: 14px; padding: 16px 18px; height: 100%;
        }
        .vf-label {
            font-family: 'Courier New', monospace; font-size: 10px; letter-spacing: 1px;
            color: var(--vf-label); text-transform: uppercase; margin-bottom: 6px;
        }
        .vf-value { font-size: 28px; font-weight: 700; color: var(--vf-text); line-height: 1.15; }
        .vf-subtitle { font-size: 12px; color: var(--vf-text-secondary); margin-top: 3px; }

        /* Sidebar pipeline */
        .vf-pipeline-title {
            font-family: 'Courier New', monospace; font-size: 10px; letter-spacing: 1px;
            color: var(--vf-label); text-transform: uppercase; margin-bottom: 8px;
            display: flex; justify-content: space-between;
        }
        .vf-segment-row { display: flex; gap: 4px; margin-bottom: 14px; }
        .vf-segment { flex: 1; height: 4px; border-radius: 999px; background: #eef0f4; }
        .vf-segment-filled { background: var(--vf-accent); }
        .vf-step {
            display: flex; justify-content: space-between; align-items: center;
            padding: 6px 0; font-size: 13px; color: var(--vf-text);
        }
        .vf-step-badge { font-size: 11px; font-weight: 600; }
        .vf-badge-done { color: var(--vf-accent); }
        .vf-badge-ready { color: var(--vf-green); }
        .vf-badge-pending { color: var(--vf-label); }

        /* Progress bars (data quality) */
        .vf-progress-row { margin-bottom: 14px; }
        .vf-progress-label {
            display: flex; justify-content: space-between; font-size: 13px;
            color: var(--vf-text); margin-bottom: 6px;
        }
        .vf-progress-track {
            width: 100%; height: 7px; border-radius: 999px; background: #eef0f4;
            overflow: hidden;
        }
        .vf-progress-fill { height: 100%; border-radius: 999px; background: var(--vf-accent); }

        /* AI insight callout */
        .vf-insight-box {
            background: var(--vf-accent-soft); border: 1px solid #d6e4ff;
            border-radius: 14px; padding: 14px 16px;
        }
        .vf-insight-tag {
            font-family: 'Courier New', monospace; font-size: 10px; letter-spacing: 1px;
            color: var(--vf-accent); text-transform: uppercase; margin-bottom: 6px;
            font-weight: 700;
        }
        .vf-insight-text { font-size: 13px; color: var(--vf-text); line-height: 1.5; }

        /* Source file card */
        .vf-file-card {
            background: var(--vf-card-bg); border: 1px solid var(--vf-border);
            border-radius: 12px; padding: 10px 12px; display: flex; gap: 9px;
            align-items: center; margin-bottom: 8px;
        }
        .vf-file-icon {
            width: 30px; height: 30px; border-radius: 8px; background: var(--vf-accent-soft);
            display: flex; align-items: center; justify-content: center; font-size: 14px; flex-shrink: 0;
        }
        .vf-file-name { font-size: 12.5px; font-weight: 600; color: var(--vf-text); }
        .vf-file-meta { font-size: 11.5px; color: var(--vf-text-secondary); }

        /* Success / status banner */
        .vf-success-banner {
            background: var(--vf-accent-soft); border: 1px solid #d6e4ff;
            border-radius: 10px; padding: 10px 12px; font-size: 12.5px;
            color: var(--vf-accent); font-weight: 600; display: flex; align-items: center; gap: 6px;
        }

        /* Section labels in sidebar */
        .vf-sidebar-section-label {
            font-family: 'Courier New', monospace; font-size: 10px; letter-spacing: 1px;
            color: var(--vf-label); text-transform: uppercase; margin: 4px 0 8px 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def sidebar_brand(brand_name: str, subtitle: str):
    """Renders the logo + brand name at the very top of the sidebar."""
    st.markdown(
        f"""
        <div class="vf-sidebar-brand">
            <div class="vf-logo">{brand_name[0].upper()}</div>
            <div>
                <div class="vf-brand-name">{brand_name}</div>
                <div class="vf-brand-sub">{subtitle}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_row(status_text: str):
    """Small right-aligned status line for the top of the main content area."""
    st.markdown(
        f"""<div class="vf-status"><span class="vf-status-dot"></span>{status_text}</div>""",
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, subtitle: str):
    st.markdown(
        f"""
        <div class="vf-card">
            <div class="vf-label">{label}</div>
            <div class="vf-value">{value}</div>
            <div class="vf-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def progress_row(label: str, pct: float):
    pct = max(0.0, min(100.0, pct))
    st.markdown(
        f"""
        <div class="vf-progress-row">
            <div class="vf-progress-label"><span>{label}</span><span>{pct:.1f}%</span></div>
            <div class="vf-progress-track"><div class="vf-progress-fill" style="width:{pct}%;"></div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def ai_insight_box(text: str, tag: str = "AI INSIGHT"):
    st.markdown(
        f"""<div class="vf-insight-box"><div class="vf-insight-tag">{tag}</div>
        <div class="vf-insight-text">{text}</div></div>""",
        unsafe_allow_html=True,
    )


def pipeline_sidebar(steps: list[tuple[str, str]]):
    """steps: list of (label, status) where status in {'done','ready','pending'}"""
    done_count = sum(1 for _, s in steps if s in ("done", "ready"))
    st.markdown(
        f"""<div class="vf-pipeline-title"><span>ANALYSIS PIPELINE</span><span>{done_count} / {len(steps)}</span></div>""",
        unsafe_allow_html=True,
    )
    segments = "".join(
        f'<div class="vf-segment {"vf-segment-filled" if i < done_count else ""}"></div>'
        for i in range(len(steps))
    )
    st.markdown(f'<div class="vf-segment-row">{segments}</div>', unsafe_allow_html=True)

    rows = ""
    for i, (label, status) in enumerate(steps, 1):
        rows += f'<div class="vf-step"><span>{i:02d} {label}</span></div>'
    st.markdown(rows, unsafe_allow_html=True)


def file_card(file_name: str, size_kb: float, file_type: str):
    st.markdown(
        f"""
        <div class="vf-file-card">
            <div class="vf-file-icon">📄</div>
            <div>
                <div class="vf-file-name">{file_name}</div>
                <div class="vf-file-meta">{size_kb:.1f} KB · {file_type}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def success_banner(text: str):
    st.markdown(f"""<div class="vf-success-banner">✓ {text}</div>""", unsafe_allow_html=True)


def sidebar_section_label(text: str):
    st.markdown(f'<div class="vf-sidebar-section-label">{text}</div>', unsafe_allow_html=True)