"""Shared CSS constants to reduce inline style duplication."""

CARD = "background:#1a2238;border:1px solid #1e3a5a;border-radius:10px;padding:14px;margin:8px 0;"
CARD_SM = "background:#1a2238;border:1px solid #1e2940;border-radius:8px;padding:12px;margin:2px 0;"
CARD_DARK = "background:#161d30;border:1px solid #1e2940;border-radius:10px;padding:12px;margin-top:8px;"
CARD_STAGE = "background:#0d1117;border:1px solid #2a3050;border-radius:8px;padding:6px 10px;margin-bottom:6px;display:flex;align-items:center;gap:8px;font-size:13px;"
CARD_STAGE_LG = "background:#161d30;border:1px solid #1e2940;border-radius:8px;padding:6px 10px;margin-bottom:6px;display:flex;align-items:center;gap:8px;font-size:0.8125rem;"

TEXT_PRIMARY = "#c0d0e0"
TEXT_SECONDARY = "#7a8aaa"
TEXT_ACCENT = "#60a5fa"
TEXT_ACCENT2 = "#6bcbff"
TEXT_MUTED = "#5a6a8a"
TEXT_WHITE = "#f0f4ff"

WARN_RED = "#ef4444"
WARN_GREEN = "#22c55e"
WARN_YELLOW = "#f59e0b"
WARN_ORANGE = "#ff6b6b"

BG_DARK = "#1a2238"
BG_DARK2 = "#161d30"
BG_TRANSPARENT = "rgba(0,0,0,0)"
BORDER_DEFAULT = "1px solid #1e2940"
BORDER_ACCENT = "1px solid #1e3a5a"
BORDER_WARN = "1px solid rgba(239,68,68,0.4)"
BORDER_OK = "1px solid rgba(34,197,94,0.3)"

FONT_XS = "0.6875rem"
FONT_SM = "0.75rem"
FONT_BASE = "0.8125rem"
FONT_MD = "0.9375rem"
FONT_LG = "1rem"
FONT_XL = "1.25rem"

BADGE_RED = "background:#ff444422;color:#ff4444;border:1px solid #ff4444;border-radius:4px;padding:1px 6px;font-size:0.65rem;"
BADGE_PSYCH = f"background:#f59e0b20;color:{WARN_YELLOW};font-size:0.6875rem;font-weight:600;padding:2px 8px;border-radius:4px;"
BADGE_THEME = f"background:#1e3a5a;color:#9aa8c0;font-size:0.6875rem;padding:2px 8px;border-radius:4px;"
BADGE_THERAPY = "background:#0a2a1a;color:#6bcbff;font-size:0.6875rem;padding:2px 8px;border-radius:4px;"

AI_BOX = f"background:{BG_DARK};border:{BORDER_ACCENT};border-radius:10px;padding:14px;margin:8px 0;"
AI_HEADER = f"color:{TEXT_ACCENT};font-size:{FONT_XS};font-weight:600;margin-bottom:6px;"
AI_BODY = f"color:{TEXT_PRIMARY};font-size:{FONT_BASE};line-height:1.6;"
AI_GRID = f"background:{BG_DARK};border:{BORDER_ACCENT};border-radius:10px;padding:12px;margin:4px 0;"

BORDER_DANGER = lambda c: f"border:1px solid {c};border-radius:10px;padding:14px;margin-bottom:10px;background:#161d30;"

ACCENT_LABELS = {
    "status": {"Accepted": "#22c55e", "Declined": "#ef4444", "Waitlisted": "#f59e0b", "Pending": "#60a5fa"},
    "stage": {"acknowledged": "#22c55e", "helpline_escalated": "#ef4444", "trustee_notified": "#f59e0b", "trustee_coming": "#4ade80", "trustee_clicked": "#6ee7a7", "triggered": "#ef4444"},
}

RISK_COLORS = {"high": "#ef4444", "medium": "#f59e0b", "low": "#22c55e"}
RISK_ICONS = {"high": "\U0001f534", "medium": "\U0001f7e1", "low": "\U0001f7e2"}

STATUS_ICONS = {"pending": "\u23f3", "completed": "\u2705", "not_yet": "\u274c"}
GRADE_ICONS = {"green": "\U0001f7e2", "yellow": "\U0001f7e1", "red": "\U0001f534"}
GRADE_LABELS = {"green": "\U0001f7e2 Correctly done", "yellow": "\U0001f7e1 Partially done", "red": "\U0001f534 Needs improvement"}
GRADE_COLORS = {"green": "#44ff44", "yellow": "#ffd93d", "red": "#ff4444"}

MAIN_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; }

    .stApp {
        background: linear-gradient(160deg, #0f1525 0%, #131b2e 40%, #0e1628 100%);
    }

    ::selection { background: #3b82f6; color: white; }
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0f1525; }
    ::-webkit-scrollbar-thumb { background: #2a3a5a; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #3a4a6a; }

    h1, h2, h3 {
        color: #eef2f8 !important;
        font-weight: 600;
        letter-spacing: -0.01em;
    }
    h1 { font-size: 1.75rem !important; }
    h2 { font-size: 1.4rem !important; }
    h3 { font-size: 1.15rem !important; }

    .stMarkdown, p, li, .st-c0, .st-da {
        color: #d0d8e8 !important;
        line-height: 1.6;
    }
    .st-bw, .st-bv, .st-cx, .st-cy {
        color: #d0d8e8 !important;
    }

    button, .stButton > button, section[data-testid="stSidebar"] button {
        background: #1e2940 !important;
        color: #d0d8e8 !important;
        border-radius: 8px;
        font-weight: 500;
        font-size: 0.875rem;
        transition: all 0.2s ease;
        border: 1px solid #2a3a5a !important;
    }
    button:hover, .stButton > button:hover, section[data-testid="stSidebar"] button:hover {
        background: #2a3a5a !important;
        color: #eef2f8 !important;
        border-color: #3b82f6 !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 16px rgba(59,130,246,0.15);
    }
    button:active, .stButton > button:active {
        transform: translateY(0);
    }
    button[kind="primary"], .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
        border: none !important;
        color: white !important;
    }
    button[kind="primary"]:hover, .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #60a5fa, #3b82f6) !important;
    }

    .stTextInput > div > div > input, .stTextArea textarea {
        background: #1a2238 !important;
        border: 1px solid #2a3a5a !important;
        color: #eef2f8 !important;
        caret-color: #60a5fa !important;
        border-radius: 8px;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .stTextInput > div > div > input:focus, .stTextArea textarea:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59,130,246,0.1) !important;
    }
    .stTextInput input::placeholder, .stTextArea textarea::placeholder {
        color: #5a6a8a !important;
        opacity: 1 !important;
    }
    .stTextInput input, .stTextArea textarea {
        -webkit-text-fill-color: #eef2f8 !important;
    }
    .stTextInput > div > div > input:autofill,
    .stTextInput > div > div > input:-webkit-autofill {
        -webkit-text-fill-color: #eef2f8 !important;
        -webkit-box-shadow: 0 0 0 30px #1a2238 inset !important;
    }
    input[type="password"] { color: #eef2f8 !important; }

    .stNumberInput, .stDateInput, .stTimeInput, .stSelectbox {
        background: transparent !important;
    }
    .stNumberInput > div > div, .stDateInput > div > div, .stTimeInput > div > div, .stSelectbox > div > div {
        background: #1a2238 !important;
        border: 1px solid #2a3a5a !important;
        border-radius: 8px !important;
        color: #e0e8f5 !important;
        transition: border-color 0.2s ease !important;
    }
    .stNumberInput > div > div:hover, .stDateInput > div > div:hover, .stTimeInput > div > div:hover, .stSelectbox > div > div:hover {
        border-color: #3b82f6 !important;
    }
    .stNumberInput input, .stDateInput input, .stTimeInput input, .stSelectbox input,
    .stNumberInput input[type="number"], input[type="number"] {
        background: #1a2238 !important;
        color: #eef2f8 !important;
        caret-color: #60a5fa !important;
    }
    .stNumberInput button, .stDateInput button, .stTimeInput button {
        background: #1e2940 !important;
        color: #7a8aaa !important;
        border: none !important;
        cursor: pointer !important;
    }
    .stNumberInput button:hover, .stDateInput button:hover, .stTimeInput button:hover {
        background: #2a3a5a !important;
        color: #eef2f8 !important;
    }

    div[data-baseweb="select"] > div, div[data-baseweb="select"] input {
        background: #1a2238 !important;
        border: 1px solid #2a3a5a !important;
        color: #eef2f8 !important;
        caret-color: #60a5fa !important;
    }
    div[data-baseweb="select"] > div:hover {
        border-color: #3b82f6 !important;
    }
    ul[role="listbox"], div[role="listbox"] {
        background: #1a2238 !important;
        border: 1px solid #2a3a5a !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 16px rgba(0,0,0,0.4) !important;
    }
    li[role="option"] {
        background: #1a2238 !important;
        color: #c0d0e0 !important;
        border: none !important;
    }
    li[role="option"]:hover {
        background: #1e2940 !important;
        color: #eef2f8 !important;
    }
    li[role="option"][aria-selected="true"] {
        background: #1e3a5a !important;
        color: #60a5fa !important;
    }
    .stSelectbox > div > div > div {
        color: #e0e8f5 !important;
        background: transparent !important;
    }
    .stSelectbox svg, .stDateInput svg, .stTimeInput svg {
        fill: #7a8aaa !important;
    }

    label, .stTextInput label, .stTextArea label, .stSelectbox label, .stNumberInput label, .stDateInput label, .stTimeInput label {
        color: #b0bcd0 !important;
        font-weight: 500;
        font-size: 0.8125rem;
    }

    .stMetric {
        background: rgba(26,34,56,0.5);
        border-radius: 10px;
        padding: 12px !important;
        border: 1px solid #1e2940;
    }
    .stMetric label, .stMetric div {
        color: #b0bcd0 !important;
    }
    [data-testid="stMetricValue"] {
        color: #f0f4ff !important;
        font-size: 1.5rem !important;
        font-weight: 700;
    }
    [data-testid="stMetricLabel"] {
        color: #7a8aaa !important;
        font-size: 0.75rem !important;
    }

    div[data-testid="stExpander"] {
        background: #161d30;
        border: 1px solid #1e2940;
        border-radius: 10px;
        transition: border-color 0.2s ease;
    }
    div[data-testid="stExpander"]:hover {
        border-color: #2a3a5a;
    }
    div[data-testid="stExpander"] > div[role="button"] p {
        font-size: 0.875rem;
    }
    div[data-testid="stExpander"] div[role="button"] p {
        color: #d0d8e8 !important;
    }
    div[data-testid="stExpander"] div[role="button"]:hover {
        background: #1a2238;
        border-radius: 10px;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: #161d30;
        padding: 4px;
        border-radius: 10px;
        border: 1px solid #1e2940;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 7px;
        padding: 6px 16px;
        color: #7a8aaa;
        background: transparent;
        font-size: 0.8125rem;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #d0d8e8 !important;
        background: #1a2238;
    }
    .stTabs [aria-selected="true"] {
        background: #1e2940 !important;
        color: #eef2f8 !important;
    }

    .stAlert {
        background: #1a2238;
        border: 1px solid #2a3a5a;
        color: #d0d8e8;
        border-radius: 10px;
    }
    .stAlert [data-testid="stAlertIcon"] svg { fill: currentColor; }

    .st-bw, .st-bv {
        background-color: #1a2238;
    }

    div[data-testid="stDataFrame"] {
        background: #161d30;
        border: 1px solid #1e2940;
        border-radius: 10px;
    }
    div[data-testid="stDataFrame"] th {
        background: #1a2238 !important;
        color: #c0d0e0 !important;
        font-weight: 600;
        font-size: 0.8125rem;
    }
    div[data-testid="stDataFrame"] td {
        background: #161d30 !important;
        color: #d0d8e8 !important;
        font-size: 0.8125rem;
    }
    div[data-testid="stDataFrame"] tr:nth-child(even) td {
        background: #131b2e !important;
    }

    .stToggle label {
        color: #b0bcd0 !important;
    }
    .stCheckbox label { color: #b0bcd0 !important; }

    .psych-box {
        background: linear-gradient(135deg, rgba(59,130,246,0.08), rgba(37,99,235,0.04));
        border: 1px solid rgba(59,130,246,0.2);
        border-radius: 10px;
        padding: 14px 16px 6px;
        margin: 4px 0 8px;
    }
    .psych-box-title {
        color: #60a5fa;
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 4px;
    }
    .psych-box-desc {
        color: #7a8aaa;
        font-size: 0.75rem;
        margin-bottom: 8px;
    }

    .stCaption, caption {
        color: #7a8aaa !important;
        font-size: 0.75rem;
    }

    section[data-testid="stSidebar"] {
        background: #0f1525 !important;
        border-right: 1px solid #1e2940 !important;
    }
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] li,
    section[data-testid="stSidebar"] span:not([class*="metric"]) {
        color: #d0d8e8 !important;
    }
    section[data-testid="stSidebar"] h3 {
        color: #eef2f8 !important;
        font-size: 1.1rem !important;
    }
    section[data-testid="stSidebar"] .stMetric {
        background: rgba(26,34,56,0.6) !important;
        padding: 8px !important;
        border-radius: 8px !important;
        border: 1px solid #1e2940 !important;
    }
    section[data-testid="stSidebar"] .stMetric label,
    section[data-testid="stSidebar"] .stMetric div {
        color: #b0bcd0 !important;
    }
    section[data-testid="stSidebar"] .stCaption {
        color: #7a8aaa !important;
    }
    section[data-testid="stSidebar"] .st-bb {
        background-color: transparent !important;
    }
    section[data-testid="stSidebar"] [data-testid="stMetricValue"] {
        color: #f0f4ff !important;
        font-size: 1.25rem !important;
        font-weight: 700;
    }
    section[data-testid="stSidebar"] [data-testid="stMetricLabel"] {
        color: #7a8aaa !important;
        font-size: 0.75rem !important;
    }
    section[data-testid="stSidebar"] hr {
        border-color: #1e2940 !important;
    }
    section[data-testid="stSidebar"] .stAlert {
        background: #1a2238 !important;
        border: 1px solid #1e2940 !important;
        color: #d0d8e8 !important;
    }
    section[data-testid="stSidebar"] .stButton > button {
        background: #1a2238 !important;
        border: 1px solid #1e2940 !important;
        color: #d0d8e8 !important;
        transition: all 0.2s ease !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: #3b82f6 !important;
        border-color: #3b82f6 !important;
        color: white !important;
        transform: translateY(-1px);
    }

    hr { border-color: #1e2940 !important; }

    .stSpinner > div { border-color: #3b82f6 !important; }

    div[role="alert"] {
        border-radius: 10px;
    }

    footer { display: none; }
    #MainMenu { visibility: hidden; }
</style>
"""
