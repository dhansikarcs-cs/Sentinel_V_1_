import streamlit as st

try:
    from crisis_ import get_crisis_state, get_crisis_status, trigger_crisis, cancel_crisis
except Exception:
    get_crisis_state = get_crisis_status = trigger_crisis = cancel_crisis = None

try:
    from patient_shared_ import safe
except Exception:
    safe = None


def _pt_emergency_buttons(username: str):
    _cs = safe(get_crisis_state, {})
    _active = _cs.get("active", False)
    c1, c2 = st.columns(2)
    with c1:
        if not _active:
            if st.button("\U0001f525 Crisis? I need help now", type="primary", use_container_width=True):
                safe(trigger_crisis, None, username, "patient")
    with c2:
        if _active:
            if st.button("\u2705 Stop Crisis", use_container_width=True):
                safe(cancel_crisis, None, username)


def render_patient_emergency(username: str):
    st.markdown("### \U0001f6a8 Emergency")
    crisis_active = st.session_state.get("crisis_active", False)
    if crisis_active:
        _cs = safe(get_crisis_state, {})
        _c = safe(get_crisis_status, {"active": False, "stage": "", "elapsed": 0})
        _triggered_by = _cs.get("triggered_by", "patient")
        _elapsed = _c.get("elapsed", 0)
        _stage = _c.get("stage", "triggered")
        _terminal = _stage in ("acknowledged", "trustee_coming", "trustee_clicked", "helpline_escalated")
        _stages = [
            ("triggered", "\U0001f6a8 Triggered", 0),
            ("trustee_notified", "\U0001f464 Trusted Contact", 30),
            ("helpline_escalated", "\U0001f3e5 Helpline", 60),
        ]
        _bars = ""
        for _k, _l, _s in _stages:
            _a = _k == _stage or (_terminal and _stage == "trustee_coming" and _k == "trustee_notified")
            _p = _elapsed >= _s
            if not _a:
                _a = _terminal and _stage in ("helpline_escalated", "acknowledged") and _k == "helpline_escalated"
            _fc = "#ef4444" if _a else ("#22c55e" if _p else "#3a4a5a")
            _bg = "rgba(239,68,68,0.15)" if _a else ("rgba(34,197,94,0.12)" if _p else "rgba(26,34,56,0.6)")
            _bd = "1px solid rgba(239,68,68,0.4)" if _a else ("1px solid rgba(34,197,94,0.3)" if _p else "1px solid #1e2940")
            _bars += (
                f"<div style='flex:1;text-align:center;padding:8px;margin:0 4px;border-radius:8px;"
                f"background:{_bg};border:{_bd};color:{_fc};font-size:0.8125rem;font-weight:600;'>"
                f"{_l}<br><span style='font-size:0.6875rem;font-weight:400;'>{_s}s</span></div>"
            )
        _t = "60+" if _elapsed >= 60 else str(_elapsed)
        if _triggered_by == "psychologist":
            st.error("\U0001f534 **Crisis triggered by your psychologist** \u2014 Elevated vitals detected + journal analysis indicated high risk.")
        elif _stage == "acknowledged":
            st.success("\u2705 **Crisis acknowledged.** Support team is with you.")
        elif _stage == "helpline_escalated":
            st.error("\U0001f6a8 **Crisis escalated to helpline.** Professional help is being dispatched.")
        elif _stage in ("trustee_coming", "trustee_clicked"):
            st.info("\U0001f464 **Trusted contact has been notified.**")
        else:
            st.error("\U0001f534 **You are in crisis and need of help.**")
        st.markdown(
            f"<div style='background:#161d30;border:1px solid #1e2940;border-radius:10px;padding:12px;margin-top:8px;'>"
            f"<div style='display:flex;align-items:center;gap:12px;margin-bottom:8px;'>"
            f"<span style='color:#fca5a5;font-size:1.125rem;'>\u23f1\ufe0f</span>"
            f"<span style='color:#f0f4ff;font-size:1.25rem;font-weight:700;'>{_t}s</span>"
            f"<span style='color:#7a8aaa;font-size:0.8125rem;'>elapsed</span></div>"
            f"<div style='display:flex;'>{_bars}</div></div>",
            unsafe_allow_html=True,
        )
        if _triggered_by == "patient":
            _pt_emergency_buttons(username)
        else:
            st.caption("\u26a0\ufe0f This crisis was triggered by your psychologist. Only they can stop it.")
    else:
        _pt_emergency_buttons(username)
