import re
from .llm import ask_llm

def heuristic_route(question: str) -> str:
    q = question.lower()
    if any(x in q for x in ["anomaly","anomalies","outlier","outliers","unusual","abnormal","spike","drop"]):
        return "anomaly"
    if any(x in q for x in ["top","bottom","highest","lowest","sum","average","avg","count","total","revenue","sales","group by","compare","maximum","minimum"]):
        return "sql"
    return "analyst"

def supervisor_node(state):
    question = state["question"]
    prompt = f'''Choose exactly one route for this data question:
sql = aggregation, ranking, filtering, totals, averages, comparisons
anomaly = anomalies, outliers, unusual values, spikes, drops
analyst = general dataset analysis or explanation
Return ONLY: sql, anomaly, or analyst.

Question: {question}'''
    try:
        raw = ask_llm("You are a strict analytics router.", prompt).strip().lower()
        m = re.search(r"\b(sql|anomaly|analyst)\b", raw)
        route = m.group(1) if m else heuristic_route(question)
        reason = f"Supervisor selected the {route} route."
    except Exception:
        route = heuristic_route(question)
        reason = f"Supervisor fallback selected the {route} route."
    return {"route": route, "route_reason": reason}
