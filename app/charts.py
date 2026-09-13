"""
charts.py
Day 3: Auto-generated Plotly charts for quick visual exploration of the dataset.
"""

from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def plot_numeric_distribution(df: pd.DataFrame, column: str) -> go.Figure:
    """Histogram with a box-plot margin for a numeric column."""
    fig = px.histogram(
        df,
        x=column,
        nbins=40,
        marginal="box",
        title=f"Distribution of {column}",
    )
    fig.update_layout(bargap=0.05)
    return fig


def plot_categorical_counts(df: pd.DataFrame, column: str, top_n: int = 15) -> go.Figure:
    """Bar chart of the most frequent values in a categorical column."""
    counts = df[column].value_counts().head(top_n).reset_index()
    counts.columns = [column, "count"]
    fig = px.bar(
        counts,
        x=column,
        y="count",
        title=f"Top {top_n} values in {column}",
    )
    fig.update_layout(xaxis_tickangle=-45)
    return fig


def plot_correlation_heatmap(df: pd.DataFrame) -> Optional[go.Figure]:
    """
    Correlation heatmap across all numeric columns.
    Returns None if there are fewer than 2 numeric columns (nothing to correlate).
    """
    numeric_df = df.select_dtypes(include="number")
    if numeric_df.shape[1] < 2:
        return None

    corr = numeric_df.corr(numeric_only=True)
    fig = px.imshow(
        corr,
        text_auto=".2f",
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
        title="Correlation Heatmap (numeric columns)",
    )
    return fig


def plot_scatter(
    df: pd.DataFrame,
    x_column: str,
    y_column: str,
    color_column: Optional[str] = None,
) -> go.Figure:
    """Scatter plot between two numeric columns, optionally colored by a category."""
    fig = px.scatter(
        df,
        x=x_column,
        y=y_column,
        color=color_column,
        opacity=0.7,
        title=f"{y_column} vs {x_column}",
    )
    return fig

def _clean_layout(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(
        title=title,
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#10131a"),
    )
    return fig


def plot_metric_over_time(df: pd.DataFrame, x: str, y: str, title: str) -> go.Figure:
    fig = px.line(df, x=x, y=y, markers=True, title=title)
    return _clean_layout(fig, title)


def plot_top_products_bar(df: pd.DataFrame, metric: str, title: str) -> go.Figure:
    fig = px.bar(df, x="product", y=metric, title=title)
    fig.update_layout(xaxis_tickangle=-30)
    return _clean_layout(fig, title)


def plot_category_bar(df: pd.DataFrame, metric: str, title: str) -> go.Figure:
    fig = px.bar(df, x="category", y=metric, title=title)
    fig.update_layout(xaxis_tickangle=-20)
    return _clean_layout(fig, title)