import re

import duckdb

from .llm import ask_llm

FORBIDDEN = {
    "insert", "update", "delete", "drop", "alter", "create", "replace",
    "truncate", "attach", "detach", "copy", "install", "load", "call",
    "export", "import", "pragma", "grant", "revoke", "vacuum",
}


def clean_sql(raw: str) -> str:
    sql = raw.strip()
    sql = re.sub(r"^```sql\s*", "", sql, flags=re.I)
    sql = re.sub(r"^```\s*", "", sql)
    sql = re.sub(r"\s*```$", "", sql)
    return sql.split(";")[0].strip()


def validate_sql(sql: str):
    low = sql.lower()
    if not low.startswith(("select", "with")):
        raise ValueError("Only SELECT/WITH queries are allowed.")
    for word in FORBIDDEN:
        if re.search(rf"\b{re.escape(word)}\b", low):
            raise ValueError(f"Forbidden SQL operation: {word}")


def sql_agent_node(state):
    schema = "\n".join(f"- {c}: {state['column_types'].get(c,'unknown')}" for c in state["columns"])
    prompt = f'''Generate ONE read-only DuckDB SQL query for the question.
Use ONLY table uploaded_data and the supplied columns.
Return ONLY SQL. Use SELECT or WITH only.
Schema:
{schema}
Question:
{state["question"]}'''

    # Step 1: generate + validate the SQL.
    try:
        sql = clean_sql(ask_llm("You generate safe DuckDB SQL.", prompt))
        validate_sql(sql)
    except Exception as exc:
        return {
            "sql": "",
            "sql_result": [],
            "sql_error": str(exc),
            "error": f"SQL agent error: {exc}",
        }

    # Step 2: execute the validated query against the uploaded dataset.
    # This runs inside the node so the rest of the graph (visualization,
    # insight_agent) sees the real result in the same pass — no need to
    # re-execute or re-summarize outside the graph afterward.
    try:
        df = state["_df"]
        con = duckdb.connect(":memory:")
        con.register("uploaded_data", df)
        result_df = con.execute(sql).df()
        con.close()
        return {
            "sql": sql,
            "sql_result": result_df.to_dict(orient="records"),
            "sql_error": "",
        }
    except Exception as exc:
        return {
            "sql": sql,
            "sql_result": [],
            "sql_error": str(exc),
            "error": f"SQL execution error: {exc}",
        }