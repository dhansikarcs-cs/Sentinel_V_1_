"""Shared CSS constants to reduce inline style duplication."""

CARD = "background:#1e2336;border:1px solid #2d2d44;border-radius:10px;padding:14px;margin:8px 0;"
CARD_SM = "background:#1e2336;border:1px solid #2d2d44;border-radius:8px;padding:12px;margin:2px 0;"
CARD_DARK = "background:#1a1e30;border:1px solid #2d2d44;border-radius:10px;padding:12px;margin-top:8px;"
CARD_STAGE = "background:#151824;border:1px solid #2d2d44;border-radius:8px;padding:6px 10px;margin-bottom:6px;display:flex;align-items:center;gap:8px;font-size:13px;"
CARD_STAGE_LG = "background:#1a1e30;border:1px solid #2d2d44;border-radius:8px;padding:6px 10px;margin-bottom:6px;display:flex;align-items:center;gap:8px;font-size:0.8125rem;"

TEXT_PRIMARY = "#d8d4dc"
TEXT_SECONDARY = "#9a92a2"
TEXT_ACCENT = "#c49ea4"
TEXT_ACCENT2 = "#d8b4ba"
TEXT_MUTED = "#6a6474"
TEXT_WHITE = "#e8e4ec"

WARN_RED = "#ef4444"
WARN_GREEN = "#22c55e"
WARN_YELLOW = "#f59e0b"
WARN_ORANGE = "#ff6b6b"

BG_DARK = "#1e2336"
BG_DARK2 = "#1a1e30"
BG_TRANSPARENT = "rgba(0,0,0,0)"
BORDER_DEFAULT = "1px solid #2d2d44"
BORDER_ACCENT = "1px solid #3d3d5a"
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
BADGE_THEME = f"background:#2d2d44;color:#b4aab8;font-size:0.6875rem;padding:2px 8px;border-radius:4px;"
BADGE_THERAPY = "background:#1a1e30;color:#c49ea4;font-size:0.6875rem;padding:2px 8px;border-radius:4px;"

AI_BOX = f"background:{BG_DARK};border:{BORDER_ACCENT};border-radius:10px;padding:14px;margin:8px 0;"
AI_HEADER = f"color:{TEXT_ACCENT};font-size:{FONT_XS};font-weight:600;margin-bottom:6px;"
AI_BODY = f"color:{TEXT_PRIMARY};font-size:{FONT_BASE};line-height:1.6;"
AI_GRID = f"background:{BG_DARK};border:{BORDER_ACCENT};border-radius:10px;padding:12px;margin:4px 0;"

BORDER_DANGER = lambda c: f"border:1px solid {c};border-radius:10px;padding:14px;margin-bottom:10px;background:#1a1e30;"

ACCENT_LABELS = {
    "status": {"Accepted": "#22c55e", "Declined": "#ef4444", "Waitlisted": "#f59e0b", "Pending": "#c49ea4"},
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
        background: linear-gradient(160deg, #161926 0%, #1a1e2e 40%, #151824 100%);
    }
    .main > div { padding: 1.5rem 2rem; }

    ::selection { background: #c49ea4; color: #151824; }
    ::-webkit-scrollbar { width: 5px; }
    ::-webkit-scrollbar-track { background: #161926; }
    ::-webkit-scrollbar-thumb { background: #2d2d44; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #3d3d5a; }

    h1, h2, h3 {
        color: #e8e4ec !important;
        font-weight: 600;
        letter-spacing: -0.01em;
    }
    h1 { font-size: 1.75rem !important; margin-bottom: 0.5rem !important; }
    h2 { font-size: 1.4rem !important; margin-bottom: 0.4rem !important; }
    h3 { font-size: 1.15rem !important; margin-bottom: 0.35rem !important; }

    .stMarkdown, p, li, .st-c0, .st-da {
        color: #d8d4dc !important;
        line-height: 1.7;
    }

    .element-container { margin-bottom: 0.4rem; }
    .stMarkdown { margin-bottom: 0.25rem; }
    hr { margin: 1.25rem 0 !important; border-color: #2d2d44 !important; opacity: 0.4; }

    .st-bw, .st-bv, .st-cx, .st-cy { color: #d8d4dc !important; }

    button, .stButton > button {
        background: #1e2336 !important;
        color: #d8d4dc !important;
        border-radius: 8px;
        font-weight: 500;
        font-size: 0.875rem;
        transition: all 0.2s ease;
        border: 1px solid #3d3d5a !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.15);
    }
    button:hover, .stButton > button:hover {
        background: #232840 !important;
        color: #e8e4ec !important;
        border-color: #c49ea4 !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 16px rgba(196,158,164,0.12);
    }
    button:active { transform: translateY(0); }
    button[kind="primary"], .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #c49ea4, #b08a92) !important;
        border: none !important;
        color: #151824 !important;
        box-shadow: 0 2px 8px rgba(196,158,164,0.2);
    }
    button[kind="primary"]:hover {
        background: linear-gradient(135deg, #d8b4ba, #c49ea4) !important;
        box-shadow: 0 4px 16px rgba(196,158,164,0.3);
    }

    .stTextInput > div > div > input, .stTextArea textarea {
        background: #1e2336 !important;
        border: 1px solid #2d2d44 !important;
        color: #e8e4ec !important;
        caret-color: #c49ea4 !important;
        border-radius: 8px;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .stTextInput > div > div > input:focus, .stTextArea textarea:focus {
        border-color: #c49ea4 !important;
        box-shadow: 0 0 0 3px rgba(196,158,164,0.1) !important;
    }
    .stTextInput input::placeholder, .stTextArea textarea::placeholder {
        color: #6a6474 !important;
        opacity: 1 !important;
    }
    .stTextInput input, .stTextArea textarea {
        -webkit-text-fill-color: #e8e4ec !important;
    }
    .stTextInput > div > div > input:autofill,
    .stTextInput > div > div > input:-webkit-autofill {
        -webkit-text-fill-color: #e8e4ec !important;
        -webkit-box-shadow: 0 0 0 30px #1e2336 inset !important;
    }
    input[type="password"] { color: #e8e4ec !important; }

    .stNumberInput, .stDateInput, .stTimeInput, .stSelectbox {
        background: transparent !important;
    }
    .stNumberInput > div > div, .stDateInput > div > div, .stTimeInput > div > div, .stSelectbox > div > div {
        background: #1e2336 !important;
        border: 1px solid #2d2d44 !important;
        border-radius: 8px !important;
        color: #d8d4dc !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    }
    .stNumberInput > div > div:hover, .stDateInput > div > div:hover, .stTimeInput > div > div:hover, .stSelectbox > div > div:hover {
        border-color: #c49ea4 !important;
    }
    .stNumberInput > div > div:focus-within, .stDateInput > div > div:focus-within, .stTimeInput > div > div:focus-within, .stSelectbox > div > div:focus-within {
        border-color: #c49ea4 !important;
        box-shadow: 0 0 0 3px rgba(196,158,164,0.08) !important;
    }
    .stNumberInput input, .stDateInput input, .stTimeInput input, .stSelectbox input,
    .stNumberInput input[type="number"], input[type="number"] {
        background: #1e2336 !important;
        color: #e8e4ec !important;
        caret-color: #c49ea4 !important;
    }
    .stNumberInput button, .stDateInput button, .stTimeInput button {
        background: transparent !important;
        color: #9a92a2 !important;
        border: none !important;
        cursor: pointer !important;
        transition: color 0.15s;
    }
    .stNumberInput button:hover, .stDateInput button:hover, .stTimeInput button:hover {
        color: #e8e4ec !important;
    }

    div[data-baseweb="select"] > div, div[data-baseweb="select"] input {
        background: #1e2336 !important;
        border: 1px solid #2d2d44 !important;
        color: #e8e4ec !important;
        caret-color: #c49ea4 !important;
    }
    div[data-baseweb="select"] > div:hover { border-color: #c49ea4 !important; }
    ul[role="listbox"], div[role="listbox"] {
        background: #1e2336 !important;
        border: 1px solid #3d3d5a !important;
        border-radius: 8px !important;
        box-shadow: 0 6px 24px rgba(0,0,0,0.4) !important;
    }
    li[role="option"] {
        background: #1e2336 !important;
        color: #d8d4dc !important;
        border: none !important;
    }
    li[role="option"]:hover {
        background: #232840 !important;
        color: #e8e4ec !important;
    }
    li[role="option"][aria-selected="true"] {
        background: #2d2d44 !important;
        color: #c49ea4 !important;
    }
    .stSelectbox > div > div > div {
        color: #d8d4dc !important;
        background: transparent !important;
    }
    .stSelectbox svg, .stDateInput svg, .stTimeInput svg { fill: #9a92a2 !important; }

    label, .stTextInput label, .stTextArea label, .stSelectbox label, .stNumberInput label, .stDateInput label, .stTimeInput label {
        color: #b4aab8 !important;
        font-weight: 500;
        font-size: 0.8125rem;
        margin-bottom: 0.2rem;
    }

    .stMetric {
        background: rgba(30,35,54,0.5);
        border-radius: 10px;
        padding: 12px !important;
        border: 1px solid #2d2d44;
        transition: border-color 0.2s;
    }
    .stMetric:hover { border-color: #3d3d5a; }
    .stMetric label, .stMetric div { color: #b4aab8 !important; }
    [data-testid="stMetricValue"] {
        color: #e8e4ec !important;
        font-size: 1.5rem !important;
        font-weight: 700;
    }
    [data-testid="stMetricLabel"] {
        color: #9a92a2 !important;
        font-size: 0.75rem !important;
    }

    div[data-testid="stExpander"] {
        background: #1a1e30;
        border: 1px solid #2d2d44;
        border-radius: 10px;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
        margin-bottom: 0.5rem;
    }
    div[data-testid="stExpander"]:hover { border-color: #3d3d5a; }
    div[data-testid="stExpander"] > div[role="button"] p { font-size: 0.875rem; }
    div[data-testid="stExpander"] div[role="button"] p { color: #d8d4dc !important; }
    div[data-testid="stExpander"] div[role="button"]:hover {
        background: #1e2336;
        border-radius: 10px;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: #1a1e30;
        padding: 5px;
        border-radius: 10px;
        border: 1px solid #2d2d44;
        margin-bottom: 1rem;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 7px;
        padding: 6px 16px;
        color: #9a92a2;
        background: transparent;
        font-size: 0.8125rem;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #d8d4dc !important;
        background: #1e2336;
    }
    .stTabs [aria-selected="true"] {
        background: #232840 !important;
        color: #e8e4ec !important;
    }

    .stAlert {
        background: #1e2336;
        border: 1px solid #2d2d44;
        color: #d8d4dc;
        border-radius: 10px;
        margin: 0.6rem 0;
    }
    .stAlert [data-testid="stAlertIcon"] svg { fill: currentColor; }

    .st-bw, .st-bv { background-color: #1e2336; }

    div[data-testid="stDataFrame"] {
        background: #1a1e30;
        border: 1px solid #2d2d44;
        border-radius: 10px;
        overflow: hidden;
    }
    div[data-testid="stDataFrame"] th {
        background: #1e2336 !important;
        color: #d8d4dc !important;
        font-weight: 600;
        font-size: 0.8125rem;
        padding: 10px 12px !important;
    }
    div[data-testid="stDataFrame"] td {
        background: #1a1e30 !important;
        color: #d8d4dc !important;
        font-size: 0.8125rem;
        padding: 8px 12px !important;
    }
    div[data-testid="stDataFrame"] tr:nth-child(even) td { background: #161926 !important; }

    .stToggle label { color: #b4aab8 !important; }
    .stCheckbox label { color: #b4aab8 !important; }

    .psych-box {
        background: linear-gradient(135deg, rgba(196,158,164,0.06), rgba(176,138,146,0.03));
        border: 1px solid rgba(196,158,164,0.15);
        border-radius: 10px;
        padding: 14px 16px 6px;
        margin: 4px 0 8px;
    }
    .psych-box-title {
        color: #d8b4ba;
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 4px;
    }
    .psych-box-desc {
        color: #9a92a2;
        font-size: 0.75rem;
        margin-bottom: 8px;
    }

    .stCaption, caption {
        color: #9a92a2 !important;
        font-size: 0.75rem;
    }

    section[data-testid="stSidebar"] {
        background: #151824 !important;
        border-right: 1px solid #2d2d44 !important;
    }
    section[data-testid="stSidebar"] > div { padding: 1rem 0.8rem; }
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] li,
    section[data-testid="stSidebar"] span:not([class*="metric"]) {
        color: #d8d4dc !important;
    }
    section[data-testid="stSidebar"] h3 {
        color: #e8e4ec !important;
        font-size: 1.05rem !important;
        margin: 0.75rem 0 0.4rem !important;
    }
    section[data-testid="stSidebar"] .stMetric {
        background: rgba(30,35,54,0.5) !important;
        padding: 6px 8px !important;
        border-radius: 8px !important;
        border: 1px solid #2d2d44 !important;
    }
    section[data-testid="stSidebar"] .stMetric label,
    section[data-testid="stSidebar"] .stMetric div {
        color: #b4aab8 !important;
        font-size: 0.6875rem !important;
    }
    section[data-testid="stSidebar"] [data-testid="stMetricValue"] {
        color: #e8e4ec !important;
        font-size: 1.15rem !important;
        font-weight: 700;
    }
    section[data-testid="stSidebar"] [data-testid="stMetricLabel"] {
        color: #9a92a2 !important;
        font-size: 0.6875rem !important;
    }
    section[data-testid="stSidebar"] .stCaption { color: #9a92a2 !important; }
    section[data-testid="stSidebar"] .st-bb { background-color: transparent !important; }
    section[data-testid="stSidebar"] hr {
        border-color: #2d2d44 !important;
        margin: 0.75rem 0 !important;
    }
    section[data-testid="stSidebar"] .stAlert {
        background: #1e2336 !important;
        border: 1px solid #2d2d44 !important;
        color: #d8d4dc !important;
        margin: 0.4rem 0;
    }
    section[data-testid="stSidebar"] .stButton > button {
        background: #1e2336 !important;
        border: 1px solid #2d2d44 !important;
        color: #d8d4dc !important;
        transition: all 0.2s ease !important;
        font-size: 0.8125rem;
        padding: 0.35rem 0.6rem;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: #c49ea4 !important;
        border-color: #c49ea4 !important;
        color: #151824 !important;
        transform: translateY(-1px);
    }

    .stSpinner > div { border-color: #c49ea4 !important; }

    div[role="alert"] { border-radius: 10px; }

    footer { display: none; }
    #MainMenu { visibility: hidden; }

    .journal-card {
        background: linear-gradient(135deg, #1e2336, #1a1e30);
        border: 1px solid #2d2d44;
        border-radius: 10px;
        padding: 16px;
        transition: border-color 0.2s, box-shadow 0.2s;
    }
    .journal-card:hover { border-color: #3d3d5a; box-shadow: 0 2px 12px rgba(196,158,164,0.06); }

    .step-done { background: #1a3a2a; border-color: #22c55e40; }
    .step-active { background: #232840; border-color: #c49ea460; }
    .step-pending { background: #1e2336; border-color: #2d2d44; }

    div[data-baseweb="segmented-control"] {
        background: #1a1e30 !important;
        border: 1px solid #2d2d44 !important;
        border-radius: 10px !important;
        padding: 3px !important;
        gap: 2px !important;
    }
    div[data-baseweb="segmented-control"] button {
        background: transparent !important;
        border: none !important;
        color: #9a92a2 !important;
        font-size: 0.8125rem !important;
        font-weight: 500 !important;
        border-radius: 7px !important;
        padding: 6px 14px !important;
        transition: all 0.2s ease !important;
        box-shadow: none !important;
    }
    div[data-baseweb="segmented-control"] button:hover {
        color: #d8d4dc !important;
        background: #1e2336 !important;
    }
    div[data-baseweb="segmented-control"] button[aria-checked="true"] {
        background: #232840 !important;
        color: #e8e4ec !important;
    }

    div[data-testid="column"], section[data-testid="stSidebar"] div[data-testid="column"] {
        gap: 0.5rem;
    }
    div[data-testid="stForm"] { border: none !important; padding: 0 !important; }
    div[role="radiogroup"] { gap: 0.25rem; }
    button[title^="Download"] {
        background: transparent !important;
        border: 1px solid #2d2d44 !important;
    }
</style>
"""
