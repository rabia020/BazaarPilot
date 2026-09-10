from .llm import ask_llm

def insight_node(state):
    prompt = f'''Answer the user's question using ONLY these verified results.
Question: {state["question"]}
Route: {state.get("route")}
SQL: {state.get("sql","")}
SQL result: {state.get("sql_result",[])}
Analyst result: {state.get("analysis","")}
Anomaly result: {state.get("anomaly_result",[])}
Never invent numbers. Keep the answer concise and professional.'''
    try:
        text = ask_llm("You summarize verified analytics results.", prompt)
    except Exception:
        if state.get("route") == "anomaly":
            text = state.get("analysis", "No anomaly result was produced.")
        elif state.get("sql_result"):
            text = f"The SQL analysis returned {len(state['sql_result'])} result row(s)."
        else:
            text = state.get("analysis", "No additional insight was produced.")
    return {"insights": text, "final_answer": text}
