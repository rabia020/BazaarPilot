import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))

from duckdb_manager import TABLE_NAME, execute_readonly, validate_sql, clean_sql
from .llm import ask_llm


def sql_agent_node(state):
    schema = "\n".join(
        f"- {c}: {state['column_types'].get(c, 'unknown')}" for c in state["columns"]
    )
    prompt = f'''Generate ONE read-only DuckDB SQL query for the question.
Use ONLY table {TABLE_NAME} and the supplied columns.
Return ONLY SQL. Use SELECT or WITH only. Never invent rows.
Schema:
{schema}
Question:
{state["question"]}'''

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

    try:
        result_df = execute_readonly(sql, state["_df"])
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