from dotenv import load_dotenv
import streamlit as st
import os, random
from datetime import datetime

load_dotenv()
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import sys
try:
    print(f"[main] CWD: {os.getcwd()}, GROQ_API_KEY set: {bool(os.getenv('GROQ_API_KEY'))}", file=sys.stderr)
except OSError:
    try:
        print("[main] CWD unavailable, GROQ_API_KEY set:", bool(os.getenv('GROQ_API_KEY')))
    except OSError:
        pass

st.set_page_config(
    page_title="Sentinel — Mental Health Platform",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

try:
    from patient_profiles_ import get_patient_name, get_psychologist_name
except Exception:
    get_patient_name = get_psychologist_name = None

try:
    from patient_portal_ import render_patient_portal
except Exception:
    render_patient_portal = None

try:
    from psychologist_ import render_psychologist_portal
except Exception:
    render_psychologist_portal = None

try:
    from data_manager_ import get_crisis_state, set_crisis_state, load_bookings, load_crisis_log
except Exception:
    get_crisis_state = set_crisis_state = load_bookings = None


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
from styles_ import MAIN_CSS
st.markdown(MAIN_CSS, unsafe_allow_html=True)

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


# ── Trustee Portal ────────────────────────────────────────
if st.query_params.get("trustee") == "1":
    from trustee_ import render_trustee_portal
    render_trustee_portal()

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
def _safe(func, default=None, *args, **kwargs):
    try:
        if func is not None:
            return func(*args, **kwargs)
    except Exception as e:
        import sys; print(f"[_safe] {func.__name__ if func else 'None'}: {e}", file=sys.stderr)
    return default if default is not None else {}

crisis_state = _safe(get_crisis_state, {})
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
        if st.button(f"👤 {st.session_state.username}", key="sidebar_profile_btn", use_container_width=True, help="View and edit your profile"):
            st.session_state.show_profile = True
        st.markdown("---")

        if st.session_state.role == "Patient":
            st.markdown(f'<div style="font-size:0.8125rem;color:#6a6474;font-style:italic;padding:6px 0 6px 12px;border-left:2px solid #c49ea4;line-height:1.5;">"{QUOTES[st.session_state.quote_index]}"</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="font-size:0.8125rem;color:#6a6474;font-style:italic;padding:6px 0 6px 12px;border-left:2px solid #c49ea4;line-height:1.5;">"{QUOTES[st.session_state.quote_index]}"</div>', unsafe_allow_html=True)

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
                bookings_data = _safe(load_bookings, [])
                crisis_state = _safe(get_crisis_state, {})
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
            try:
                if crisis_state.get("active") and not crisis_state.get("acknowledged"):
                    _cp = crisis_state["patient"]
                    if crisis_state.get("triggered_by") == "psychologist_self":
                        _name = _safe(get_psychologist_name, _cp.replace("psych:", ""), _cp.replace("psych:", ""))
                        _reason = "🧑‍⚕️ Psychologist self-reported crisis"
                    else:
                        _name = _safe(get_patient_name, _cp, _cp)
                        _reason = "Active crisis — not acknowledged"
                    high_risk.append({
                        "name": _name,
                        "reason": _reason,
                        "severity": "critical",
                    })
            except Exception:
                pass

            try:
                from data_manager_ import load_bookings
                all_bookings = load_bookings()
                missed = {}
                for b in all_bookings:
                    if b.get("status") == "No-show":
                        missed[b["patient"]] = missed.get(b["patient"], 0) + 1
                for pname, count in list(missed.items())[:3]:
                    high_risk.append({"name": _safe(get_patient_name, pname, pname), "reason": f"{count} missed session(s)", "severity": "flagged"})
            except Exception:
                pass

            if high_risk:
                for p in high_risk:
                    icon = "🔴" if p["severity"] == "critical" else "🟡"
                    st.markdown(
                        f"<div style='display:flex;align-items:center;gap:10px;padding:8px 10px;"
                        f"background:{'rgba(239,68,68,0.1)' if p['severity'] == 'critical' else 'rgba(234,179,8,0.08)'};"
                        f"border:1px solid {'rgba(239,68,68,0.2)' if p['severity'] == 'critical' else 'rgba(234,179,8,0.15)'};"
                        f"border-radius:8px;margin:6px 0;font-size:0.8125rem;'>"
                        f"<span>{icon}</span>"
                        f"<div><strong>{p['name']}</strong><br><span style='color:#6a6474;font-size:0.75rem;'>{p['reason']}</span></div>"
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
        st.markdown("#### 📋 Recent Activity")
        try:
            from activity_feed_ import render_activity_feed
            if st.session_state.role == "Patient":
                render_activity_feed(st.session_state.username, 8)
            else:
                render_activity_feed(limit=8)
        except Exception:
            st.caption("Activity feed unavailable.")

        if st.session_state.get("role") == "Psychologist" and not st.session_state.get("_psych_onboarding", True):
            st.markdown("---")
            st.markdown("#### 🤖 AI Insights")
            import time as _time
            _now = _time.time()
            _ai_cache_ts = st.session_state.get("_ai_cache_ts", 0)
            if _now - _ai_cache_ts > 120:
                st.session_state["_ai_cache_ts"] = _now
                try:
                    from agent_ import pre_session_brief, cross_patient_patterns, compliance_radar, silent_period_watch, relapse_indicators
                    from patient_profiles_ import get_assigned_patients, get_patient_name
                    from psych_shared_ import safe as _ai_safe
                    _all_p = _ai_safe(get_assigned_patients, [], st.session_state.get("username", ""))
                    _briefs = []
                    _warnings = []
                    if _all_p:
                        for _ap in _all_p[:5]:
                            _b = _ai_safe(pre_session_brief, {"suggestion": ""}, _ap)
                            _pn = _ai_safe(get_patient_name, _ap, _ap)
                            _briefs.append({"patient": _pn, "text": _b.get("suggestion", "")})
                            _si = _ai_safe(silent_period_watch, {"flag": False, "message": ""}, _ap)
                            if _si and _si.get("flag"):
                                _warnings.append(f"Silent: {_pn}")
                            _ri = _ai_safe(relapse_indicators, {"flag": False, "message": ""}, _ap)
                            if _ri and _ri.get("flag"):
                                _warnings.append(f"Relapse: {_pn}")
                        _cp = _ai_safe(cross_patient_patterns, {"suggestion": ""})
                    else:
                        _cp = {"suggestion": ""}
                    st.session_state["_ai_cache_briefs"] = _briefs
                    st.session_state["_ai_cache_warnings"] = _warnings
                    st.session_state["_ai_cache_patterns"] = _cp.get("suggestion", "")
                except Exception:
                    st.session_state["_ai_cache_briefs"] = []
                    st.session_state["_ai_cache_warnings"] = []
                    st.session_state["_ai_cache_patterns"] = ""
            _cached_briefs = st.session_state.get("_ai_cache_briefs", [])
            _cached_warnings = st.session_state.get("_ai_cache_warnings", [])
            _cached_patterns = st.session_state.get("_ai_cache_patterns", "")
            if _cached_briefs:
                _itabs = st.tabs(["Briefs", "Patterns", "Monitors"])
                with _itabs[0]:
                    for _cb in _cached_briefs:
                        if _cb["text"]:
                            st.markdown(f"**{_cb['patient']}**  \n{_cb['text']}")
                            st.divider()
                with _itabs[1]:
                    if _cached_patterns:
                        st.markdown(_cached_patterns)
                    else:
                        st.caption("No patterns yet.")
                with _itabs[2]:
                    for _w in _cached_warnings:
                        st.warning(_w)
                    if not _cached_warnings:
                        st.caption("No flags.")

        st.markdown("---")
        if st.button("🆘 Trigger Crisis Alert (Self)", key="psych_self_crisis", use_container_width=True):
                _u = st.session_state.get("username", "unknown_psych")
                _n = st.session_state.get("psychologist_name", _u)
                _ts = datetime.now().isoformat()
                try:
                    from data_manager_ import append_crisis_log, set_crisis_state
                    append_crisis_log({"event": "psych_self_report", "patient": f"psych:{_u}", "timestamp": _ts, "source": "psychologist_self", "details": {"name": _n}})
                    set_crisis_state({"active": True, "patient": f"psych:{_u}", "triggered_at": _ts, "triggered_by": "psychologist_self", "acknowledged": False, "acknowledged_by": "", "acknowledged_at": "", "helpline_escalated": False, "trusted_contact_notified": False, "trustee_acknowledged": False, "trustee_clicked": False, "tc_ack_emailed": False, "helpline_ack_emailed": False})
                except Exception:
                    pass
                st.rerun()

        st.markdown("---")
        st.markdown("#### 🆘 Crisis History")
        crisis_log = _safe(load_crisis_log, [])
        if crisis_log:
            _role = st.session_state.get("role", "")
            _user = st.session_state.get("username", "")
            if _role == "Patient":
                crisis_log = [e for e in crisis_log if e.get("patient") == _user]
            for entry in reversed(crisis_log[-5:]):
                ts = entry["timestamp"][:19].replace("T", " ")
                event = entry["event"]
                patient = entry["patient"]
                if event == "triggered":
                    icon = "🔴"
                    _src = entry.get("source", "patient")
                    label = f"Triggered by {patient} ({'🧪 Demo' if _src=='psychologist' else '🆘 Patient'})"
                elif event == "psych_self_report":
                    icon = "💛"
                    _d = entry.get("details", {})
                    _n = _d.get("name", patient)
                    label = f"🧑‍⚕️ {_n} requested help"
                elif event == "vitals_ai":
                    icon = "📊"
                    _v = entry.get("details", {})
                    label = f"HR {_v.get('base_hr','?')}→{_v.get('spike_hr','?')} BPM | AI: {_v.get('risk_score','?')}/10 ({patient})"
                elif event == "acknowledged":
                    icon = "🟢"
                    label = f"Acknowledged {entry.get('details', '')}"
                elif event == "helpline_escalated":
                    icon = "🚨"
                    label = f"Helpline escalated ({patient})"
                elif event == "trustee_notified":
                    icon = "📧"
                    label = f"TC notified ({patient})"
                elif event == "resolved":
                    icon = "⏹"
                    label = f"Resolved {entry.get('details', '')} ({entry.get('source', 'patient')})"
                else:
                    icon = "📌"
                    label = event
                st.markdown(
                    f"<div style='font-size:0.75rem;padding:4px 0;color:#c0d0e0;line-height:1.5;'>"
                    f"{icon} <strong>{label}</strong><br>"
                    f"<span style='color:#5a4a5a;font-size:0.6875rem;'>{ts}</span></div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No crisis events recorded.")

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
from auth_ui_ import render_login


# ── Routing ────────────────────────────────────────────────
if not st.session_state.authenticated:
    render_login()
else:
    role = st.session_state.role
    if role == "Patient":
        try:
            render_patient_portal()
        except Exception as e:
            st.error(f"Patient portal unavailable.")
    else:
        try:
            render_psychologist_portal()
        except Exception as e:
            st.error(f"Psychologist portal unavailable.")
