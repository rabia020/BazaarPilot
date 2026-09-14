import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

load_dotenv()


def _secret(name: str) -> str | None:
    try:
        import streamlit as st
        value = st.secrets.get(name)
        if value:
            return str(value)
    except Exception:
        pass
    return os.getenv(name)


def get_llm():
    key = _secret("GROQ_API_KEY")
    if not key:
        return None
    return ChatGroq(
        model=_secret("GROQ_MODEL") or "openai/gpt-oss-20b",
        temperature=0,
        api_key=key,
    )


def ask_llm(system_prompt: str, user_prompt: str) -> str:
    llm = get_llm()
    if llm is None:
        raise RuntimeError(
            "GROQ_API_KEY is not configured. Add it to .env locally or to Streamlit secrets."
        )
    response = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
    )
    return response.content
