import os
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

def get_llm():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        return None
    return ChatGroq(
        model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        temperature=0,
        api_key=key,
    )

def ask_llm(system_prompt: str, user_prompt: str) -> str:
    llm = get_llm()
    if llm is None:
        raise RuntimeError("GROQ_API_KEY is not configured. Add it to .env.")
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ])
    return response.content
