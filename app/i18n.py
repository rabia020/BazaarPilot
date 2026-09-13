import re
import streamlit as st


TRANSLATIONS = {
    "en": {
        "app_title": "BazaarPilot",
        "app_subtitle": "AI BUSINESS CO-PILOT",

        "load_sample": "Load sample sales dataset",
        "upload_label": "Upload a CSV or Excel file",
        "source_file": "SOURCE FILE",
        "replace_file": "↑ Replace file",

        "pipeline_upload": "Upload",
        "pipeline_profile": "Profile",
        "pipeline_ask": "Ask questions",
        "pipeline_visualize": "Visualize",
        "pipeline_anomalies": "Detect anomalies",
        "pipeline_report": "Report",

        "tab_overview": "Overview",
        "tab_quality": "Data quality",
        "tab_ai": "AI analysis",
        "tab_charts": "Charts",
        "tab_anomalies": "Anomalies",
        "tab_insights": "Insights",
        "tab_inventory": "Inventory",
        "tab_approvals": "Approvals",

        "dataset_overview": "Dataset overview",
        "export_report": "Export report",

        "revenue": "REVENUE",
        "profit": "PROFIT",
        "quantity_sold": "QUANTITY SOLD",
        "products": "PRODUCTS",
        "rows": "ROWS",

        "business_alerts": "Business alerts",
        "no_alerts": "✅ No critical alerts — inventory and sales trends look healthy.",

        "data_quality_heading": "Data quality",
        "ai_insight_heading": "AI insight",
        "generate_summary": "Generate Executive Summary",

        "ask_question_heading": "Ask a business question",
        "ask_caption": "Numbers come from DuckDB. The AI only explains the query result.",

        "btn_top10": "Top 10 revenue",
        "btn_profitable": "Most profitable",
        "btn_category": "Best category",
        "btn_reorder": "Reorder check",
        "btn_roman_urdu": "Roman Urdu profit",

        "chat_placeholder": "Ask in English or Roman Urdu",

        "generated_sql": "Generated SQL",
        "agent_label": "Agent",

        "inventory_heading": "Inventory & stockout risk",
        "inventory_caption": "days_until_stockout = current_inventory / average_daily_sales",
        "generate_reorders": "Generate Reorder Recommendations",

        "pending_actions": "Pending actions",
        "approvals_caption": (
            "AI-proposed actions require human approval before being recorded. "
            
        ),

        "approve": "✅ Approve",
        "reject": "❌ Reject",

        "activity_log": "Activity log",

        "no_pending": (
            "No pending actions. Go to the **Inventory** tab and click "
            "**Generate Reorder Recommendations**, or ask the AI Analyst "
            "\"Which products should I reorder?\"."
        ),

        "no_log": "No actions approved or rejected yet.",

        "language_label": "Language",

        "risk_critical": "Critical",
        "risk_low": "Low",
        "risk_healthy": "Healthy",

        "alert_critical": "Critical stock",
        "alert_low": "Low stock",
        "alert_increase": "Sales increase",
        "alert_decline": "Sales decline",
        "alert_anomaly": "Anomaly detected in numeric columns",

        "cost_caption": (
            "Cost {cost} · Missing values {missing} · Duplicate rows {dupes}"
        ),

        "q_top10": "What are my top 10 products by revenue?",
        "q_profitable": "Which products generate the most profit?",
        "q_category": "Which category performs best?",
        "q_reorder": "Which products should I reorder?",
        "q_roman_urdu": (
            "Meri shop mein sab se zyada profit kis product se aa raha hai?"
        ),

        "days_left_risk": "{days} days until stockout (risk: {risk}).",
        "action_reorder": "Reorder",
        "suggested_qty_label": "Suggested quantity: {qty} units",
    },

    "ur": {
        "app_title": "بازار پائلٹ",
        "app_subtitle": "اے آئی بزنس کو-پائلٹ",

        "load_sample": "نمونہ سیلز ڈیٹا لوڈ کریں",
        "upload_label": "CSV یا Excel فائل اپ لوڈ کریں",
        "source_file": "ماخذ فائل",
        "replace_file": "↑ فائل تبدیل کریں",

        "pipeline_upload": "اپ لوڈ",
        "pipeline_profile": "پروفائل",
        "pipeline_ask": "سوالات پوچھیں",
        "pipeline_visualize": "بصری منظر",
        "pipeline_anomalies": "بےقاعدگی معلوم کریں",
        "pipeline_report": "رپورٹ",

        "tab_overview": "جائزہ",
        "tab_quality": "ڈیٹا کوالٹی",
        "tab_ai": "اے آئی تجزیہ",
        "tab_charts": "چارٹس",
        "tab_anomalies": "بےقاعدگیاں",
        "tab_insights": "بصیرت",
        "tab_inventory": "انوینٹری",
        "tab_approvals": "منظوریاں",

        "dataset_overview": "ڈیٹاسیٹ کا جائزہ",
        "export_report": "رپورٹ برآمد کریں",

        "revenue": "آمدنی",
        "profit": "منافع",
        "quantity_sold": "فروخت شدہ مقدار",
        "products": "پروڈکٹس",
        "rows": "قطاریں",

        "business_alerts": "کاروباری الرٹس",
        "no_alerts": (
            "✅ کوئی سنگین الرٹ نہیں — انوینٹری اور سیلز رجحانات ٹھیک ہیں۔"
        ),

        "data_quality_heading": "ڈیٹا کوالٹی",
        "ai_insight_heading": "اے آئی بصیرت",
        "generate_summary": "ایگزیکٹو سمری بنائیں",

        "ask_question_heading": "کاروباری سوال پوچھیں",
        "ask_caption": (
            "اعداد و شمار DuckDB سے آتے ہیں۔ اے آئی صرف نتیجے کی وضاحت کرتا ہے۔"
        ),

        "btn_top10": "ٹاپ 10 آمدنی",
        "btn_profitable": "سب سے زیادہ منافع بخش",
        "btn_category": "بہترین کیٹگری",
        "btn_reorder": "دوبارہ آرڈر چیک",
        "btn_roman_urdu": "رومن اردو منافع",

        "chat_placeholder": "اپنا سوال پوچھیں",

        "generated_sql": "تیار کردہ SQL",
        "agent_label": "ایجنٹ",

        "inventory_heading": "انوینٹری اور اسٹاک ختم ہونے کا خطرہ",
        "inventory_caption": (
            "دن باقی = موجودہ انوینٹری / اوسط یومیہ فروخت"
        ),
        "generate_reorders": "دوبارہ آرڈر کی سفارشات بنائیں",

        "pending_actions": "زیر التوا اقدامات",
        "approvals_caption": (
            "اے آئی کی تجویز کردہ کارروائیوں کو ریکارڈ ہونے سے پہلے "
            "انسانی منظوری درکار ہے — "
            
        ),

        "approve": "✅ منظور کریں",
        "reject": "❌ مسترد کریں",

        "activity_log": "سرگرمی لاگ",

        "no_pending": (
            "کوئی زیر التوا کارروائی نہیں۔ **انوینٹری** ٹیب میں جا کر "
            "**دوبارہ آرڈر کی سفارشات بنائیں** پر کلک کریں، یا اے آئی "
            "اینالسٹ سے پوچھیں \"مجھے کون سا مال دوبارہ آرڈر کرنا چاہیے؟\"۔"
        ),

        "no_log": "ابھی تک کوئی کارروائی منظور یا مسترد نہیں ہوئی۔",

        "language_label": "زبان",

        "risk_critical": "سنگین",
        "risk_low": "کم",
        "risk_healthy": "بہتر",

        "alert_critical": "سنگین اسٹاک",
        "alert_low": "کم اسٹاک",
        "alert_increase": "فروخت میں اضافہ",
        "alert_decline": "فروخت میں کمی",
        "alert_anomaly": "اعداد میں بےقاعدگی معلوم ہوئی",

        "cost_caption": (
            "لاگت {cost} · غائب اقدار {missing} · تکراری قطاریں {dupes}"
        ),

        "q_top10": "ٹاپ 10 پروڈکٹس آمدنی کے لحاظ سے کون سے ہیں؟",
        "q_profitable": "کون سے پروڈکٹس سب سے زیادہ منافع بخش ہیں؟",
        "q_category": "کون سی کیٹگری بہترین کارکردگی دکھا رہی ہے؟",
        "q_reorder": "مجھے کون سا مال دوبارہ آرڈر کرنا چاہیے؟",
        "q_roman_urdu": (
            "میری شاپ میں سب سے زیادہ منافع کس پروڈکٹ سے آ رہا ہے؟"
        ),

        "days_left_risk": (
            "اسٹاک ختم ہونے میں {days} دن باقی ہیں (خطرہ: {risk})۔"
        ),

        "action_reorder": "دوبارہ آرڈر",
        "suggested_qty_label": "تجویز کردہ مقدار: {qty} یونٹس",
    },
}


def t(key: str) -> str:
    """
    Return the translation for the current UI language.
    Falls back to English if the key is missing.
    """
    lang = st.session_state.get("ui_lang", "en")

    return TRANSLATIONS.get(
        lang,
        TRANSLATIONS["en"]
    ).get(
        key,
        TRANSLATIONS["en"].get(key, key)
    )


def inject_rtl_if_needed():
    """
    Apply RTL styling when Urdu is selected.
    """
    if st.session_state.get("ui_lang") == "ur":
        st.markdown(
            """
            <style>
            .block-container,
            .stMarkdown,
            .stTextInput,
            .stButton,
            .stTabs {
                direction: rtl;
                text-align: right;
            }

            .stTabs [data-baseweb="tab-list"] {
                direction: rtl;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------
# Category translations
# ---------------------------------------------------------

CATEGORY_TRANSLATIONS_UR = {
    "electronics": "الیکٹرانکس",
    "grocery": "گروسری",
    "dairy": "ڈیری",
    "household": "گھریلو اشیاء",
    "beverages": "مشروبات",
}


def translate_category(name: str) -> str:
    """
    Translate a category name when Urdu UI is active.
    """
    if st.session_state.get("ui_lang") != "ur":
        return name

    return CATEGORY_TRANSLATIONS_UR.get(
        str(name).strip().lower(),
        name
    )


# ---------------------------------------------------------
# Product translations
# ---------------------------------------------------------

PRODUCT_TRANSLATIONS_UR = {
    "milk": "دودھ",
    "mineral water": "منرل واٹر",
    "green tea": "گرین ٹی",
    "cooking oil": "کوکنگ آئل",
    "instant noodles": "انسٹنٹ نوڈلز",
    "rice": "چاول",
    "energy drink": "انرجی ڈرنک",
    "dish soap": "ڈش صابن",
    "premium headphones": "پریمیم ہیڈ فونز",
    "smartphone case": "اسمارٹ فون کیس",
    "basmati gift box": "باسمتی گفٹ باکس",
}


def translate_products_in_text(text: str) -> str:
    """
    Replace known English product names inside a larger text.

    This function does NOT depend on Streamlit session state,
    so it is safe to use from ai_insights.py and insight_agent.py.
    """
    if not text:
        return text

    names = sorted(
        PRODUCT_TRANSLATIONS_UR.keys(),
        key=len,
        reverse=True,
    )

    pattern = re.compile(
        r"\b(" + "|".join(re.escape(name) for name in names) + r")\b",
        flags=re.IGNORECASE,
    )

    return pattern.sub(
        lambda match: PRODUCT_TRANSLATIONS_UR.get(
            match.group(0).lower(),
            match.group(0),
        ),
        text,
    )


def translate_product(name: str) -> str:
    """
    Translate one product name.
    Uses the current UI language.
    """
    if st.session_state.get("ui_lang") != "ur":
        return name

    return PRODUCT_TRANSLATIONS_UR.get(
        str(name).strip().lower(),
        name,
    )


# ---------------------------------------------------------
# Route translations
# ---------------------------------------------------------

ROUTE_TRANSLATIONS_UR = {
    "analytics": "تجزیات",
    "profit": "منافع",
    "inventory": "انوینٹری",
    "recommendation": "سفارش",
    "error": "خرابی",
    "unknown": "نامعلوم",
}


def translate_route(route: str) -> str:
    """
    Translate agent route labels for the Urdu UI.
    """
    if st.session_state.get("ui_lang") != "ur":
        return route

    return ROUTE_TRANSLATIONS_UR.get(
        str(route).lower(),
        route,
    )


# ---------------------------------------------------------
# Risk translations
# ---------------------------------------------------------

RISK_TRANSLATIONS_UR = {
    "Critical": "سنگین",
    "Low": "کم",
    "Healthy": "بہتر",
}


def translate_risk(risk: str) -> str:
    """
    Translate inventory risk labels for the Urdu UI.
    """
    if st.session_state.get("ui_lang") != "ur":
        return risk

    return RISK_TRANSLATIONS_UR.get(
        str(risk).strip(),
        risk,
    )