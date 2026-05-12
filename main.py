from dotenv import load_dotenv
import streamlit as st
import random
from datetime import datetime

load_dotenv()

st.set_page_config(
    page_title="Sentinel — Mental Health Platform",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

from patient_profiles import authenticate, get_patient_name, get_psychologist_name
from patient_portal import render_patient_portal
from psychologist import render_psychologist_portal
from data_manager import get_crisis_state, set_crisis_state, load_bookings


QUOTES = [
    "The wound is the place where the Light enters you. — Rumi",
    "Out of suffering have emerged the strongest souls. — Kahlil Gibran",
    "Healing takes time, and asking for help is a courageous step.",
    "Rest is not idleness. It is preparation for meaningful work.",
    "The greatest glory in living lies not in never falling, but in rising every time we fall. — Mandela",
    "What mental health needs is more sunlight, more candor, more unashamed conversation. — Glenn Close",
    "You are not your illness. You have an individual story to tell. — Viktor Frankl",
    "There is hope, even when your brain tells you there isn't. — John Green",
    "Self-care is not selfish. You cannot serve from an empty vessel.",
    "The only journey is the journey within. — Rainer Maria Rilke",
]


# ── Custom CSS ─────────────────────────────────────────────
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0a0e1a 0%, #111827 50%, #0a1628 100%);
    }
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        border: none;
        color: white;
    }
    .stTextInput > div > div > input, .stTextArea textarea {
        background: #1a1f2e;
        border: 1px solid #2a3050;
        color: #e0e8ff;
        border-radius: 8px;
    }
    .stSelectbox > div > div, .stNumberInput > div > div, .stDateInput > div > div, .stTimeInput > div > div {
        background: #1a1f2e !important;
        border: 1px solid #2a3050 !important;
        border-radius: 8px !important;
        color: #e0e8ff !important;
    }
    .stSelectbox > div > div > div, .stNumberInput input, .stDateInput input, .stTimeInput input {
        color: #e0e8ff !important;
    }
    .stSelectbox svg, .stDateInput svg, .stTimeInput svg {
        fill: #99aabb !important;
    }
    h1, h2, h3 {
        color: #f0f4ff !important;
        font-weight: 600;
    }
    .stMarkdown, p, li, .st-c0, .st-da {
        color: #d0d8e8 !important;
    }
    .st-bw, .st-bv, .st-cx, .st-cy {
        color: #d0d8e8 !important;
    }
    .stMetric label, .stMetric div {
        color: #b0b8c8 !important;
    }
    div[data-testid="stExpander"] {
        background: #111827;
        border: 1px solid #2a3050;
        border-radius: 10px;
    }
    div[data-testid="stExpander"] > div[role="button"] p {
        font-size: 14px;
    }
    div[data-testid="stExpander"] div[role="button"] p {
        color: #e0e8ff !important;
    }
    div[data-testid="stExpander"] div[role="button"]:hover {
        background: #1a1f2e;
        border-radius: 10px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background: #111827;
        padding: 6px;
        border-radius: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px;
        padding: 6px 16px;
        color: #889;
        background: transparent;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #c0d0e0 !important;
        background: #1a1f2e;
    }
    .stTabs [aria-selected="true"] {
        background: #1e293b !important;
        color: #e0e8ff !important;
    }
    .stAlert {
        background: #1a1f2e;
        border: 1px solid #2a3050;
        color: #d0d8e8;
    }
    .st-bw, .st-bv {
        background-color: #1a1f2e;
    }
    label, .stTextInput label, .stTextArea label, .stSelectbox label, .stNumberInput label, .stDateInput label, .stTimeInput label {
        color: #c0c8d8 !important;
    }
    .st-cx, .st-cy {
        color: #d0d8e8;
    }
    div[data-testid="stDataFrame"] {
        background: #111827;
        border: 1px solid #2a3050;
        border-radius: 8px;
    }
    div[data-testid="stDataFrame"] th {
        background: #1a1f2e !important;
        color: #c0d0e0 !important;
        font-weight: 600;
    }
    div[data-testid="stDataFrame"] td {
        background: #111827 !important;
        color: #d0d8e8 !important;
    }
    div[data-testid="stDataFrame"] tr:nth-child(even) td {
        background: #151b2a !important;
    }
    .stToggle label {
        color: #c0c8d8 !important;
    }
    .stCaption, caption {
        color: #99aabb !important;
    }
    section[data-testid="stSidebar"] {
        background: #0d1117 !important;
        border-right: 1px solid #1e293b !important;
    }
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] li,
    section[data-testid="stSidebar"] span:not([class*="metric"]) {
        color: #e0e8ff !important;
    }
    section[data-testid="stSidebar"] h3 {
        color: #f0f4ff !important;
        font-size: 18px !important;
    }
    section[data-testid="stSidebar"] .stMetric {
        background: #151b2a !important;
        padding: 8px !important;
        border-radius: 8px !important;
        border: 1px solid #2a3050 !important;
    }
    section[data-testid="stSidebar"] .stMetric label,
    section[data-testid="stSidebar"] .stMetric div {
        color: #c0d0e0 !important;
    }
    section[data-testid="stSidebar"] .stCaption {
        color: #99aabb !important;
    }
    section[data-testid="stSidebar"] .st-bb {
        background-color: transparent !important;
    }
    section[data-testid="stSidebar"] [data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-size: 22px !important;
        font-weight: 700;
    }
    section[data-testid="stSidebar"] [data-testid="stMetricLabel"] {
        color: #99aabb !important;
        font-size: 13px !important;
    }
    section[data-testid="stSidebar"] hr {
        border-color: #2a3050 !important;
    }
    section[data-testid="stSidebar"] .stAlert {
        background: #151b2a !important;
        border: 1px solid #2a3050 !important;
        color: #e0e8ff !important;
    }
    section[data-testid="stSidebar"] .stButton > button {
        background: #1a1f2e !important;
        border: 1px solid #2a3050 !important;
        color: #e0e8ff !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: #2563eb !important;
        border-color: #2563eb !important;
        color: white !important;
    }
    footer { display: none; }
    #MainMenu { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── PWA Support ──────────────────────────────────────────────
st.markdown("""
<script>
  (function(){
    var l = document.createElement('link');
    l.rel = 'manifest'; l.href = '/manifest.json';
    document.head.appendChild(l);
    var m = document.createElement('meta');
    m.name = 'theme-color'; m.content = '#111827';
    document.head.appendChild(m);
    if('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js');
    }
  })();
</script>
""", unsafe_allow_html=True)


# ── Session Initialization ────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = ""

if "crisis_active" not in st.session_state:
    st.session_state.crisis_active = False
if "crisis_acknowledged" not in st.session_state:
    st.session_state.crisis_acknowledged = False
if "trusted_notified" not in st.session_state:
    st.session_state.trusted_notified = False
if "helpline_called" not in st.session_state:
    st.session_state.helpline_called = False
if "ai_cache" not in st.session_state:
    st.session_state.ai_cache = {}
if "login_time" not in st.session_state:
    st.session_state.login_time = datetime.now()
if "quote_index" not in st.session_state:
    st.session_state.quote_index = random.randint(0, len(QUOTES) - 1)
if "simulate_heavy" not in st.session_state:
    st.session_state.simulate_heavy = False
if "psych_room_intense" not in st.session_state:
    st.session_state.psych_room_intense = False
if "patient_room_intense" not in st.session_state:
    st.session_state.patient_room_intense = False
# Sync crisis state from disk on each load
crisis_state = get_crisis_state()
if crisis_state.get("active"):
    st.session_state.crisis_active = True
    st.session_state.crisis_acknowledged = crisis_state.get("acknowledged", False)
    st.session_state.trusted_notified = crisis_state.get("trusted_contact_notified", False)
    st.session_state.helpline_called = crisis_state.get("helpline_escalated", False)
else:
    st.session_state.crisis_active = False


# ── Sidebar ────────────────────────────────────────────────
with st.sidebar:
    if st.session_state.authenticated:
        st.markdown(f"### 🧠 Sentinel")
        st.markdown(f"**{st.session_state.role}**")
        st.markdown(f"👤 {st.session_state.username}")
        st.markdown("---")

        if st.session_state.role == "Patient":
            st.markdown(f'<div style="font-size:13px;color:#889;font-style:italic;padding:4px 0;border-left:2px solid #2563eb;padding-left:10px;">"{QUOTES[st.session_state.quote_index]}"</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="font-size:13px;color:#889;font-style:italic;padding:4px 0;border-left:2px solid #2563eb;padding-left:10px;">"{QUOTES[st.session_state.quote_index]}"</div>', unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("#### 📋 Daily Ops")

            sim_col1, sim_col2 = st.columns([3, 1])
            with sim_col1:
                st.caption("Current shift overview")
            with sim_col2:
                if st.button("📊 Demo", key="sim_toggle", help="Toggle simulated load scenario"):
                    st.session_state.simulate_heavy = not st.session_state.simulate_heavy
                    st.rerun()

            if st.session_state.simulate_heavy:
                pending_count = 4
                active_crisis = 2
                session_mins = 120
            else:
                bookings_data = load_bookings()
                crisis_state = get_crisis_state()
                now = datetime.now()
                session_mins = int((now - st.session_state.login_time).total_seconds() / 60)
                pending_count = sum(1 for b in bookings_data if b["status"] == "Pending")
                active_crisis = 1 if crisis_state.get("active") and not crisis_state.get("acknowledged") else 0

            workload_score = pending_count + active_crisis * 3
            if session_mins > 120:
                workload_score += 2
            elif session_mins > 90:
                workload_score += 1

            cols_op = st.columns(3)
            cols_op[0].metric("Pending", pending_count, border=False)
            cols_op[1].metric("Crisis", active_crisis, border=False)
            cols_op[2].metric("Session", f"{session_mins}m", border=False)

            if workload_score >= 5:
                st.warning("⚠️ **High workload detected.** Consider a short break.")
            elif workload_score >= 3:
                st.info("📊 Moderate activity. Pace yourself.")
            else:
                st.success("✅ Light load. Good time for deep work.")

            st.markdown("---")
            st.markdown("#### 🔴 High Risk Patients")
            high_risk = []
            if crisis_state.get("active") and not crisis_state.get("acknowledged"):
                high_risk.append({
                    "name": get_patient_name(crisis_state["patient"]),
                    "reason": "Active crisis — not acknowledged",
                    "severity": "critical",
                })

            flagged = [
                ("Alice Chen", "Elevated stress trend (72h)"),
                ("Bob Martinez", "3 missed sessions"),
            ]
            seed_patients = hash(st.session_state.username + "risk") % 100
            if seed_patients < 60:
                for pname, reason in flagged:
                    high_risk.append({"name": pname, "reason": reason, "severity": "flagged"})

            if high_risk:
                for p in high_risk:
                    icon = "🔴" if p["severity"] == "critical" else "🟡"
                    st.markdown(
                        f"<div style='display:flex;align-items:center;gap:8px;padding:6px 8px;"
                        f"background:{'#3a0a0a' if p['severity'] == 'critical' else '#3a2a00'};"
                        f"border-radius:6px;margin:4px 0;font-size:13px;'>"
                        f"<span>{icon}</span>"
                        f"<div><strong>{p['name']}</strong><br><span style='color:#889;font-size:11px;'>{p['reason']}</span></div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("No high-risk patients at this time.")

        st.markdown("---")
        st.markdown("#### System Status")
        status_color = "🟢 Online" if not st.session_state.crisis_active else "🔴 Crisis Active"
        st.markdown(f"{status_color}")
        st.markdown(f"AI: {'Connected' if st.session_state.get('ai_cache') is not None else 'Ready'}")

        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    else:
        st.markdown("### 🧠 Sentinel")
        st.markdown("*AI-Assisted Mental Health Platform*")
        st.markdown("---")
        st.markdown("Dual Portal Ecosystem")


# ── Login Screen ───────────────────────────────────────────
def render_login():
    st.markdown(
        "<h1 style='text-align:center;font-size:42px;background:linear-gradient(135deg,#60a5fa,#a78bfa);"
        "-webkit-background-clip:text;-webkit-text-fill-color:transparent;'>"
        "🧠 Sentinel</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center;color:#889;font-size:16px;'>"
        "AI-Assisted Mental Health Ecosystem</p>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("#### Sign In")
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="e.g., alice, dr.sarah")
            password = st.text_input("Password", type="password", placeholder="pass123")

            if st.form_submit_button("Authenticate", type="primary", use_container_width=True):
                role = authenticate(username, password)
                if role:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.role = role
                    if role == "Patient":
                        st.session_state.patient_name = get_patient_name(username)
                    else:
                        st.session_state.psychologist_name = get_psychologist_name(username)
                    st.rerun()
                else:
                    st.error("Invalid credentials. Try: alice / pass123 or dr.sarah / doc123")

        st.markdown("---")
        st.markdown("##### Demo Credentials")
        cols = st.columns(2)
        with cols[0]:
            st.markdown("**Patients**")
            st.code("alice / pass123")
            st.code("bob / pass123")
            st.code("charlie / pass123")
        with cols[1]:
            st.markdown("**Psychologists**")
            st.code("dr.sarah / doc123")
            st.code("dr.james / doc123")


# ── Routing ────────────────────────────────────────────────
if not st.session_state.authenticated:
    render_login()
else:
    role = st.session_state.role
    if role == "Patient":
        render_patient_portal()
    else:
        render_psychologist_portal()
