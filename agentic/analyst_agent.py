from .llm import ask_llm

def analyst_node(state):
    schema = "\n".join(f"- {c}: {state['column_types'].get(c,'unknown')}" for c in state["columns"])
    prompt = f'''Answer this general analytics question using only the dataset schema.
Do not invent numerical results.
Schema:
{schema}
Question:
{state["question"]}'''
    try:
        text = ask_llm("You are a concise professional data analyst.", prompt)
    except Exception:
        text = f"The dataset contains {len(state['columns'])} columns: {', '.join(state['columns'])}."
    return {"analysis": text}
