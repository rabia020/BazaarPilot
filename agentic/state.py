from typing import Any, TypedDict

class AgentState(TypedDict, total=False):
    _df: Any  # the raw uploaded pandas DataFrame; must be declared here or
              # LangGraph drops it, since it only tracks fields in this schema
    question: str
    ui_lang: str
    dataset_name: str
    columns: list[str]
    column_types: dict[str, str]
    route: str
    route_reason: str
    sql: str
    sql_result: list[dict[str, Any]]
    sql_error: str
    analysis: str
    anomaly_result: list[dict[str, Any]]
    chart_type: str
    chart_data: list[dict[str, Any]]
    insights: str
    final_answer: str
    error: str