from langgraph.graph import START, END, StateGraph
from .state import AgentState
from .supervisor import supervisor_node
from .sql_agent import sql_agent_node
from .anomaly_agent import anomaly_agent_node
from .analyst_agent import analyst_node
from .inventory_agent import inventory_agent_node
from .recommendation_agent import recommendation_agent_node
from .visualization import visualization_node
from .insight_agent import insight_node
from .profit_agent import profit_agent_node

ROUTE_MAP = {
    "analytics": "sql_agent",
    "profit": "profit_agent",
    "anomaly": "anomaly_agent",
    "inventory": "inventory_agent",
    "recommendation": "recommendation_agent",
    "general": "analyst_agent",
}

def route_after_supervisor(state):
    return ROUTE_MAP.get(state.get("route"), "analyst_agent")

def build_graph():
    g = StateGraph(AgentState)
    g.add_node("supervisor", supervisor_node)
    g.add_node("sql_agent", sql_agent_node)
    g.add_node("anomaly_agent", anomaly_agent_node)
    g.add_node("analyst_agent", analyst_node)
    g.add_node("inventory_agent", inventory_agent_node)
    g.add_node("recommendation_agent", recommendation_agent_node)
    g.add_node("visualization", visualization_node)
    g.add_node("insight_agent", insight_node)
    g.add_node("profit_agent", profit_agent_node)

    g.add_edge(START, "supervisor")
    g.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "sql_agent": "sql_agent",
            "anomaly_agent": "anomaly_agent",
            "analyst_agent": "analyst_agent",
            "inventory_agent": "inventory_agent",
            "recommendation_agent": "recommendation_agent",
            "profit_agent": "profit_agent",
        },
    )
    g.add_edge("sql_agent", "visualization")
    g.add_edge("anomaly_agent", "visualization")
    g.add_edge("analyst_agent", "visualization")
    g.add_edge("inventory_agent", "visualization")
    g.add_edge("recommendation_agent", "visualization")
    g.add_edge("profit_agent", "visualization")
    g.add_edge("visualization", "insight_agent")
    g.add_edge("insight_agent", END)
    return g.compile()