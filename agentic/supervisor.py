import re
from .llm import ask_llm

VALID_ROUTES = {"analytics", "inventory", "profit", "anomaly", "recommendation", "general"}

def heuristic_route(question: str) -> str:
    q = question.lower()
    if any(x in q for x in ["anomaly", "anomalies", "outlier", "outliers", "unusual", "abnormal", "spike", "drop", "unusual sales"]):
        return "anomaly"
    if any(x in q for x in ["reorder", "restock", "stockout", "stock out", "low stock", "run out", "runout", "inventory", "maal dobara order"]):
        return "inventory"
    if any(x in q for x in ["should i", "recommend", "recommendation", "what should", "suggest", "advice"]):
        return "recommendation"
    if any(x in q for x in ["profit", "margin", "why did", "decrease", "decline", "increase", "kis product se aa raha"]):
        return "profit"
    if any(x in q for x in ["top", "bottom", "highest", "lowest", "sum", "average", "avg", "count", "total",
                             "revenue", "sales", "group by", "compare", "maximum", "minimum"]):
        return "analytics"
    return "general"

def supervisor_node(state):
    question = state["question"]
    prompt = f'''Choose exactly one route for this small-business data question.
The question may be in English or Roman Urdu.

analytics = rankings, totals, averages, top/bottom products, revenue, sales volume comparisons
inventory = stock levels, stockout risk, reorder quantities, "which products should I reorder"
profit = profit amounts, profit margin, why profit went up/down, profitability by product/category
anomaly = unusual values, outliers, spikes, drops, "is anything unusual"
recommendation = general business advice, "what should I do", suggestions not tied to inventory reorder
general = anything else, or a question about the dataset itself

Return ONLY one word: analytics, inventory, profit, anomaly, recommendation, or general.

Question: {question}'''
    try:
        raw = ask_llm("You are a strict business-question router. Reply with one word only.", prompt).strip().lower()
        m = re.search(r"\b(analytics|inventory|profit|anomaly|recommendation|general)\b", raw)
        route = m.group(1) if m else heuristic_route(question)
        if route not in VALID_ROUTES:
            route = heuristic_route(question)
        reason = f"Supervisor selected the {route} route."
    except Exception:
        route = heuristic_route(question)
        reason = f"Supervisor fallback selected the {route} route."
    return {"route": route, "route_reason": reason}