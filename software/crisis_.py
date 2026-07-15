import streamlit as st
import smtplib
import os
import base64
import json
import math, struct
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None

try:
    from data_manager_ import get_crisis_state, set_crisis_state, append_crisis_log
except Exception:
    get_crisis_state = set_crisis_state = append_crisis_log = None

TRUSTED_CONTACT_DELAY = 30
HELPLINE_DELAY = 60

SENDER_EMAIL = os.getenv("SENTINEL_EMAIL", "")
SENDER_PASSWORD = os.getenv("SENTINEL_EMAIL_PASSWORD", "")
RECEIVER_EMAIL = os.getenv("SENTINEL_RECEIVER", "")


def _safe(func, default=None, *args, **kwargs):
    try:
        if func is not None:
            return func(*args, **kwargs)
    except Exception as e:
        import sys; print(f"[_safe] {func.__name__ if func else 'None'}: {e}", file=sys.stderr)
    return default if default is not None else {}


def _get_ack_link():
    env_link = os.getenv("SENTINEL_ACK_LINK", "")
    if env_link:
        return env_link
    try:
        port = st.config.get_option("server.port")
        return f"http://localhost:{port}/?trustee=1"
    except Exception:
        return "http://localhost:8501/?trustee=1"


def _get_base_link():
    link = _get_ack_link()
    idx = link.find("/", 8)
    return link[:idx] if idx != -1 else link


def _get_patient_display(username: str) -> str:
    try:
        from patient_profiles_ import get_patient_name
        return get_patient_name(username)
    except Exception:
        return username


def send_email(subject: str, body: str):
    _sender = os.getenv("SENTINEL_EMAIL", "")
    _pw = os.getenv("SENTINEL_EMAIL_PASSWORD", "")
    _receiver = os.getenv("SENTINEL_RECEIVER", "")
    if not _sender or not _pw or not _receiver:
        return False
    msg = MIMEMultipart()
    msg["From"] = _sender
    msg["To"] = _receiver
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=5)
        server.starttls()
        server.login(_sender, _pw)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Email failed: {e}")
        return False


def play_alert():
    try:
        sample_rate = 8000
        duration = 1.5
        num_samples = int(sample_rate * duration)
        data_size = num_samples * 2
        samples = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            sweep = 440 + 220 * math.sin(2 * math.pi * 3 * t)
            pulse = 0.4 + 0.3 * math.sin(2 * math.pi * 2 * t)
            sample = int(pulse * 32767 * math.sin(2 * math.pi * sweep * t))
            samples.extend(struct.pack('<h', sample))
        data = bytes(samples)
        wav = bytearray()
        wav.extend(b'RIFF')
        wav.extend(struct.pack('<I', 36 + data_size))
        wav.extend(b'WAVE')
        wav.extend(b'fmt ')
        wav.extend(struct.pack('<I', 16))
        wav.extend(struct.pack('<H', 1))
        wav.extend(struct.pack('<H', 1))
        wav.extend(struct.pack('<I', sample_rate))
        wav.extend(struct.pack('<I', sample_rate * 2))
        wav.extend(struct.pack('<H', 2))
        wav.extend(struct.pack('<H', 16))
        wav.extend(b'data')
        wav.extend(struct.pack('<I', data_size))
        wav.extend(data)
        audio_b64 = base64.b64encode(bytes(wav)).decode()
        st.markdown(
            f'<audio autoplay loop><source src="data:audio/wav;base64,{audio_b64}"></audio>',
            unsafe_allow_html=True,
        )
    except Exception:
        pass


def trigger_crisis(patient_username: str, source: str = "patient"):
    now = datetime.now().isoformat()
    state = {
        "active": True,
        "patient": patient_username,
        "triggered_at": now,
        "triggered_by": source,
        "acknowledged": False,
        "acknowledged_by": "",
        "acknowledged_at": "",
        "helpline_escalated": False,
        "trusted_contact_notified": False,
        "trustee_acknowledged": False,
        "trustee_clicked": False,
        "tc_ack_emailed": False,
        "helpline_ack_emailed": False,
    }
    _safe(set_crisis_state, None, state)
    _safe(append_crisis_log, None, {"event": "triggered", "patient": patient_username, "timestamp": now, "source": source, "triggered_by": source})
    try:
        from data_manager_ import log_activity
        log_activity(source if source == "psychologist_self" else patient_username, "crisis", patient_username, f"triggered by {source}")
    except Exception:
        pass
    st.session_state.crisis_active = True
    st.session_state.crisis_acknowledged = False
    st.session_state.trusted_notified = False
    st.session_state.helpline_called = False


def cancel_crisis(patient_username: str):
    state = _safe(get_crisis_state, {})
    if not state.get("active"):
        return
    if state.get("patient") != patient_username:
        return
    now = datetime.now().isoformat()
    _safe(append_crisis_log, None, {"event": "cancelled", "patient": patient_username, "timestamp": now, "details": "cancelled by patient", "source": "patient"})
    _safe(set_crisis_state, None, {"active": False, "patient": "", "triggered_at": "", "triggered_by": "", "acknowledged": False, "acknowledged_by": "", "acknowledged_at": "", "helpline_escalated": False, "trusted_contact_notified": False, "trustee_acknowledged": False, "trustee_clicked": False, "tc_ack_emailed": False, "helpline_ack_emailed": False})
    try:
        from data_manager_ import log_activity
        log_activity(patient_username, "crisis_cancelled", patient_username, "cancelled by patient")
    except Exception:
        pass
    st.session_state.crisis_active = False
    st.session_state.crisis_acknowledged = False
    st.session_state.trusted_notified = False
    st.session_state.helpline_called = False


def resolve_crisis(psychologist_username: str):
    state = _safe(get_crisis_state, {})
    if not state.get("active"):
        return
    now = datetime.now().isoformat()
    _safe(append_crisis_log, None, {"event": "resolved", "patient": state["patient"], "timestamp": now, "details": f"by {psychologist_username}", "source": state.get("triggered_by", "patient")})
    _safe(set_crisis_state, None, {"active": False, "patient": "", "triggered_at": "", "triggered_by": "", "acknowledged": False, "acknowledged_by": "", "acknowledged_at": "", "helpline_escalated": False, "trusted_contact_notified": False, "trustee_acknowledged": False, "trustee_clicked": False, "tc_ack_emailed": False, "helpline_ack_emailed": False})
    try:
        from data_manager_ import log_activity
        log_activity(psychologist_username, "crisis_resolved", state.get("patient", ""), f"resolved by {psychologist_username}")
    except Exception:
        pass
    st.session_state.crisis_active = False
    st.session_state.crisis_acknowledged = False
    st.session_state.trusted_notified = False
    st.session_state.helpline_called = False


def acknowledge_crisis(psychologist_username: str):
    state = _safe(get_crisis_state, {})
    if not state.get("active"):
        return
    now = datetime.now().isoformat()
    state["acknowledged"] = True
    state["acknowledged_by"] = psychologist_username
    state["acknowledged_at"] = now
    _safe(set_crisis_state, None, state)
    _safe(append_crisis_log, None, {"event": "acknowledged", "patient": state["patient"], "timestamp": now, "details": f"by {psychologist_username}"})
    st.session_state.crisis_acknowledged = True

    patient = state["patient"]
    was_notified = state.get("trusted_contact_notified", False)
    helpline_was = state.get("helpline_escalated", False)
    display = _get_patient_display(patient)

    if helpline_was and not state.get("helpline_ack_emailed"):
        state["helpline_ack_emailed"] = True
        _safe(set_crisis_state, None, state)
        send_email(
            f"⚠️ {display}'s crisis — Psychologist acknowledged (after helpline)",
            f"The helpline was contacted for {display}, but Dr. {psychologist_username.replace('dr.', '')} has now acknowledged.\n\n"
            f"Triggered: {state['triggered_at']}\nAcknowledged: {now}\n\nDashboard: {_get_base_link()}\nSentinel"
        )
    elif was_notified and not helpline_was and not state.get("tc_ack_emailed"):
        state["tc_ack_emailed"] = True
        _safe(set_crisis_state, None, state)
        send_email(
            f"✅ {display}'s crisis — Psychologist intervened",
            f"Dr. {psychologist_username.replace('dr.', '')} acknowledged the crisis for {display}.\n"
            f"The trusted contact was notified but professional help is now in place.\n\n"
            f"Triggered: {state['triggered_at']}\nAcknowledged: {now}\n\n"
            f"Dashboard: {_get_base_link()}\nSentinel"
        )

    try:
        from agent_ import crisis_debrief as _agent_debrief
        _debrief = _agent_debrief()
        if _debrief and _debrief.get("debrief"):
            _safe(append_crisis_log, None, {"event": "debrief", "patient": patient, "timestamp": now, "details": _debrief["debrief"]})
    except Exception:
        pass


def acknowledge_trustee():
    state = _safe(get_crisis_state, {})
    if not state.get("active") or state.get("acknowledged"):
        return
    if state.get("trustee_acknowledged"):
        return
    display = _get_patient_display(state["patient"])
    state["trustee_acknowledged"] = True
    _safe(set_crisis_state, None, state)
    send_email(
        f"👤 {display}'s trusted contact is on the way",
        f"The trusted contact for {display} confirmed they are on the way.\n"
        f"Psychologist acknowledgement still needed.\n\n"
        f"Dashboard: {_get_base_link()}\n\nSentinel"
    )


def trustee_link_clicked():
    state = _safe(get_crisis_state, {})
    if not state.get("active") or state.get("acknowledged"):
        return
    if state.get("trustee_clicked"):
        return
    display = _get_patient_display(state["patient"])
    state["trustee_clicked"] = True
    _safe(set_crisis_state, None, state)
    send_email(
        f"👤 {display}'s trusted contact has been notified",
        f"The trusted contact for {display} viewed the alert page.\n"
        f"They have not yet confirmed they are on the way.\n\n"
        f"Dashboard: {_get_base_link()}\n\nSentinel"
    )


def get_crisis_status() -> dict:
    state = _safe(get_crisis_state, {})
    if not state.get("active"):
        return {"active": False, "stage": "none"}

    triggered = datetime.fromisoformat(state["triggered_at"])
    now = datetime.now()
    psych_ack = state.get("acknowledged", False)
    trustee_ack = state.get("trustee_acknowledged", False)
    trustee_clicked = state.get("trustee_clicked", False)
    elapsed = (now - triggered).total_seconds()

    if psych_ack:
        ack_at = datetime.fromisoformat(state["acknowledged_at"])
        elapsed = int((ack_at - triggered).total_seconds())
        stage = "acknowledged"
        message = f"Crisis acknowledged by {state.get('acknowledged_by', 'clinician')}. Intervention in progress."
    elif trustee_ack:
        stage = "trustee_coming"
        message = "Trusted contact is on the way. Psychologist acknowledgement still required."
    elif trustee_clicked:
        stage = "trustee_clicked"
        message = "Trusted contact has been notified. Awaiting confirmation."
    elif elapsed >= HELPLINE_DELAY:
        stage = "helpline_escalated"
        message = "CRISIS ESCALATED: Helpline contacted. Immediate intervention required."
    elif elapsed >= TRUSTED_CONTACT_DELAY:
        stage = "trustee_notified"
        message = "Trusted contact notified via email. Awaiting response."
    else:
        stage = "triggered"
        message = "Emergency siren active. Waiting for acknowledgement."

    return {
        "active": True, "stage": stage, "message": message, "elapsed": int(elapsed),
        "patient": state.get("patient", ""), "acknowledged": psych_ack,
        "trusted_notified": state.get("trusted_contact_notified", False),
        "helpline_escalated": state.get("helpline_escalated", False),
        "trustee_coming": trustee_ack, "trustee_clicked": trustee_clicked,
    }


def handle_escalation():
    state = _safe(get_crisis_state, {})
    if not state.get("active"):
        return
    if state.get("acknowledged"):
        return

    triggered = datetime.fromisoformat(state["triggered_at"])
    elapsed = (datetime.now() - triggered).total_seconds()

    if elapsed >= TRUSTED_CONTACT_DELAY and not state.get("trusted_contact_notified"):
        state["trusted_contact_notified"] = True
        _safe(set_crisis_state, None, state)
        display = _get_patient_display(state["patient"])
        _safe(append_crisis_log, None, {"event": "trustee_notified", "patient": state["patient"], "timestamp": datetime.now().isoformat()})
        send_email(
            f"\U0001f4e7 {display}'s trusted contact notified (30s)",
            f"The trusted contact for {display} has been emailed.\n"
            f"Trustee page: {_get_ack_link()}\n\n"
            f"Triggered at: {state['triggered_at']}\n\nSentinel"
        )

    if state.get("trustee_acknowledged") or state.get("helpline_escalated"):
        return

    if elapsed >= HELPLINE_DELAY and not state.get("helpline_escalated"):
        state["helpline_escalated"] = True
        _safe(set_crisis_state, None, state)
        display = _get_patient_display(state["patient"])
        _safe(append_crisis_log, None, {"event": "helpline_escalated", "patient": state["patient"], "timestamp": datetime.now().isoformat()})
        send_email(
            f"🚨 {display}'s crisis — Helpline contacted (60s)",
            f"No acknowledgement was received within {HELPLINE_DELAY}s for {display}.\n"
            f"The helpline has been contacted. IMMEDIATE INTERVENTION REQUIRED.\n\n"
            f"Dashboard: {_get_base_link()}\nTriggered at: {state['triggered_at']}\n\nSentinel"
        )


def render_crisis_alarm():
    try:
        status = _safe(get_crisis_status, {"active": False})
        if not status["active"]:
            raw = _safe(get_crisis_state, {})
            if raw.get("active"):
                status = _safe(get_crisis_status, {"active": False})
            else:
                return

        if st_autorefresh:
            st_autorefresh(interval=5000, key="crisis_alarm_poll")
        play_alert()
        handle_escalation()

        stage = status["stage"]
        patient = status["patient"]

        if stage == "acknowledged":
            st.success(f"**Crisis Acknowledged** — {status['message']}")
            return

        _raw = _safe(get_crisis_state, {})
        if stage == "helpline_escalated":
            msg = "🚨 **CRISIS ESCALATION — HELPLINE CONTACTED** 🚨"
            if _raw.get("trustee_acknowledged"):
                msg += "\n\n👤 Trusted Contact is on the way"
            elif _raw.get("trustee_clicked"):
                msg += "\n\n👤 Trusted Contact has been notified"
            st.error(msg)
            st.markdown("<div style='background:#7a0000;padding:15px;border-radius:8px;border:2px solid #ff4444;text-align:center;color:white;font-weight:bold;'>⚠️ IMMEDIATE INTERVENTION REQUIRED ⚠️</div>", unsafe_allow_html=True)
        elif stage == "trustee_coming":
            st.info(f"🟢 **Trusted Contact En Route — {patient}**")
            st.markdown("<div style='background:#1a4a1a;padding:12px;border-radius:8px;border:2px solid #44ff44;color:#88ff88;text-align:center;font-weight:bold;'>👤 TRUSTED CONTACT ON THE WAY — Psychologist acknowledgement still needed</div>", unsafe_allow_html=True)
        elif stage == "trustee_clicked":
            st.info(f"👤 **Trusted Contact Notified — {patient}**")
            st.markdown("<div style='background:#2a4a2a;padding:12px;border-radius:8px;border:1px solid #44cc44;color:#88ff88;text-align:center;font-weight:bold;'>👤 TRUSTED CONTACT NOTIFIED — Awaiting confirmation of arrival</div>", unsafe_allow_html=True)
        elif stage == "trustee_notified":
            st.warning(f"⚠️ **Crisis Alert — {patient}**")
            st.markdown(f"<div style='background:#5a3a00;padding:12px;border-radius:8px;border:1px solid #ffaa00;color:white;'>Trusted contact emailed. Awaiting response.</div>", unsafe_allow_html=True)
        else:
            st.error(f"🚨 **Emergency Siren — {patient}**")
            st.markdown("<div style='background:#4a0000;padding:10px;border-radius:8px;border:1px solid #ff6666;color:#ff9999;text-align:center;'>🔴 SIREN ACTIVE — Patient triggered emergency</div>", unsafe_allow_html=True)

        if not status.get("acknowledged"):
            cols = st.columns([3, 1])
            with cols[1]:
                if st.button("✓ Acknowledge Crisis", type="primary", use_container_width=True):
                    acknowledge_crisis(st.session_state.get("username", "clinician"))
                    st.rerun()
    except Exception:
        st.error("Crisis alarm unavailable.")


def crisis_elapsed_html(elapsed: int, large: bool = False,
                         icon_color: str = "#fca5a5",
                         text_color: str = "#f0f4ff",
                         label_color: str = "#7a8aaa") -> str:
    display = "60+" if elapsed >= 60 else str(elapsed)
    bg = "#0d1117" if large else "#161d30"
    bd = "#2a3050" if large else "#1e2940"
    fs = "13px" if large else "0.8125rem"
    style = (
        f"background:{bg};border:1px solid {bd};border-radius:8px;padding:6px 10px;"
        "margin-bottom:6px;display:flex;align-items:center;gap:8px;"
        f"font-size:{fs};"
    )
    return (
        f"<div style='{style}'>"
        f"<span style='color:{icon_color};'>\u23f1\ufe0f</span>"
        f"<span style='color:{text_color};font-weight:700;'>{display}s</span>"
        f"<span style='color:{label_color};'>elapsed</span>"
        f"</div>"
    )


def crisis_stage_bar(stages: list, current: str, elapsed: int, terminal: bool = False) -> str:
    bars = ""
    for key, label, sec in stages:
        active = key == current or (terminal and current in ("helpline_escalated", "acknowledged") and key == "helpline")
        passed = elapsed >= sec
        fc = "#ef4444" if active else ("#22c55e" if passed else "#3a4a5a")
        bg = "rgba(239,68,68,0.15)" if active else ("rgba(34,197,94,0.12)" if passed else "rgba(26,34,56,0.6)")
        bd = "1px solid rgba(239,68,68,0.4)" if active else ("1px solid rgba(34,197,94,0.3)" if passed else "1px solid #1e2940")
        bars += (
            f"<div style='flex:1;text-align:center;padding:8px;margin:0 4px;border-radius:8px;"
            f"background:{bg};border:{bd};color:{fc};font-size:0.8125rem;font-weight:600;'>"
            f"{label}<br><span style='font-size:0.6875rem;font-weight:400;'>{sec}s</span></div>"
        )
    return bars


_STAGES = [("triggered", "\U0001f6a8 Triggered", 0),
           ("trustee", "\U0001f464 Trusted Contact", 30),
           ("helpline", "\U0001f3e5 Helpline", 60)]


def crisis_stage(stage: str, elapsed: int, terminal: bool = False) -> str:
    return crisis_stage_bar(_STAGES, stage, elapsed, terminal)
