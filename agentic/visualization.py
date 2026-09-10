def visualization_node(state):
    result = state.get("sql_result") or state.get("anomaly_result") or []
    if len(result) >= 2:
        return {"chart_type": "bar", "chart_data": result}
    return {"chart_type": "table", "chart_data": result}
