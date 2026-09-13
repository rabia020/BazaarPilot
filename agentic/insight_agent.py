import re
from .llm import ask_llm
from app.i18n import translate_products_in_text

MAX_ROWS = 25

# Only words that are distinctly Roman Urdu grammar/function words —
# deliberately excludes English/loanwords like "profit" or "shop" that
# would cause false positives on plain English sentences.
ROMAN_URDU_WORDS = {
    "hai", "hain", "kya", "mein", "ka", "ki", "ke", "aur", "se", "sab", "zyada",
    "kaunsa", "konsa", "meri", "mera", "dukan", "chahiye", "kis", "hoon",
    "raha", "rahi", "rahe", "kyun", "kyu", "dobara", "maal", "batao", "mujhe",
    "kitna", "kitni", "konse", "wala", "wali", "kam", "hua", "hui", "kaise",
    "kaisay", "karen", "karne", "karo",
}

# Common English words that can appear in Roman-Urdu-style sentences too
# (loanwords) — never enough on their own to decide the language.
ENGLISH_AMBIGUOUS_WORDS = {"profit", "shop", "sales", "revenue", "stock", "category", "product"}


def _detect_script(question: str, ui_lang: str = "en") -> str:
    # UI language wins when set to Urdu — the app should never answer in
    # English while the whole interface is displayed in Urdu.
    if ui_lang == "ur":
        return "urdu_script"
    if any("\u0600" <= ch <= "\u06FF" for ch in question):
        return "urdu_script"
    words = set(re.findall(r"[a-zA-Z]+", question.lower()))
    strong_matches = words & ROMAN_URDU_WORDS
    if strong_matches:
        return "roman_urdu"
    return "english"


MARKERS = ["###ANSWER###", "###RECOMMENDATION###", "###URDU_ANSWER###", "###URDU_RECOMMENDATION###"]


def _parse_sections(raw: str) -> dict:
    pattern = "(" + "|".join(re.escape(m) for m in MARKERS) + ")"
    parts = re.split(pattern, raw)
    sections, current = {}, None
    for part in parts:
        stripped = part.strip()
        if stripped in MARKERS:
            current = stripped
        elif current:
            sections[current] = sections.get(current, "") + part
    return {k: v.strip() for k, v in sections.items() if v.strip()}


def _render_answer(raw: str, script: str) -> str:
    sections = _parse_sections(raw)
    if not sections:
        return raw.strip()

    blocks = []
    if "###ANSWER###" in sections:
        blocks.append(sections["###ANSWER###"])
    if "###RECOMMENDATION###" in sections:
        blocks.append(f"**Recommendation:** {sections['###RECOMMENDATION###']}")

    urdu_parts = []
    if "###URDU_ANSWER###" in sections:
        urdu_parts.append(
            translate_products_in_text(
                sections["###URDU_ANSWER###"]
            )
        )

    if "###URDU_RECOMMENDATION###" in sections:
        urdu_parts.append(
            f"<strong>تجویز:</strong> "
            f"{translate_products_in_text(
                sections['###URDU_RECOMMENDATION###']
            )}"
        )

    if urdu_parts:
        urdu_html = (
            '<div dir="rtl" lang="ur" style="text-align:right; line-height:2; '
            "margin-top:0.75rem; font-family:'Noto Nastaliq Urdu','Jameel Noori Nastaleeq',serif;\">"
            + "<br><br>".join(urdu_parts)
            + "</div>"
        )
        blocks.append(urdu_html)

    return "\n\n".join(blocks)


def insight_node(state):
    question = state.get("question", "")
    route = state.get("route", "")
    sql = state.get("sql", "") or ""
    sql_error = state.get("sql_error", "") or ""
    error = state.get("error", "") or ""
    rows = state.get("sql_result") or []

    if route in ("inventory", "recommendation") and not rows and not sql_error and not error:
        text = state.get("analysis", "") or "No result available yet."
        return {"insights": text, "final_answer": text}

    preview = rows[:MAX_ROWS]
    analysis = state.get("analysis", "") or ""
    anomaly = state.get("anomaly_result") or []

    if sql_error or (error and not rows):
        text = (
            "I could not complete this analysis from the live dataset.\n\n"
            f"Details: {sql_error or error}\n\n"
            "No numbers were invented. Try rephrasing the question."
        )
        return {"insights": text, "final_answer": text}

    ui_lang = state.get("ui_lang", "en")
    script = _detect_script(question, ui_lang)

    if script == "english":
        format_instructions = f'''Reply in English only. Use exactly this format, with each marker on its own line:
{MARKERS[0]}
(the answer, using numbers copied from the data)
{MARKERS[1]}
(one short recommendation based on this data)'''

    elif script == "roman_urdu":
        format_instructions = f'''The question is in Roman Urdu. Reply using exactly this format, with each marker on its own line:
{MARKERS[0]}
(the answer in Roman Urdu)
{MARKERS[1]}
(one short recommendation in Roman Urdu)
{MARKERS[2]}
(the SAME answer, fully in proper Urdu script اردو, same numbers)
{MARKERS[3]}
(the SAME recommendation, fully in proper Urdu script اردو)'''

    else:  # urdu_script
        format_instructions = f'''The question is written in Urdu script. Reply ONLY in proper Urdu script (اردو رسم الخط).
Do NOT use Roman/Latin letters anywhere in your reply, except for numbers and product names that only exist in Latin script in the data.
Use exactly this format, with each marker on its own line:
{MARKERS[2]}
(the answer, fully in Urdu script)
{MARKERS[3]}
(one short recommendation, fully in Urdu script)'''

    prompt = f'''You are a business analyst for a small shop.

Answer the user's question using ONLY the verified data below.
Never invent or round in a way that changes a figure. Copy numbers from the data exactly.
If a number is not in the data, say it is not in the result.
If the result is empty, say so.

{format_instructions}

Do not add any text outside the marker sections. Do not repeat the marker names inside the content.

Question: {question}
Route: {route}
SQL: {sql}
Verified SQL rows ({len(rows)} total, showing {len(preview)}): {preview}
Analyst notes: {analysis}
Anomaly notes: {anomaly}
'''
    try:
        raw = ask_llm(
            "You only narrate verified analytics. You never invent metrics. "
            "You follow the requested marker format and language exactly.",
            prompt,
        )
        text = _render_answer(raw, script)
    except Exception as exc:
        if rows:
            text = (
                f"Query succeeded with {len(rows)} row(s). "
                f"AI explanation is unavailable ({exc}). "
                "Use the table in the app for the exact numbers."
            )
        else:
            text = analysis or f"No verified result was produced. ({exc})"
    return {"insights": text, "final_answer": text}