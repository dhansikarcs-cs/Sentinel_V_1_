import streamlit as st
import smtplib
import os
import base64
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from data_manager import get_crisis_state, set_crisis_state

TRUSTED_CONTACT_DELAY = 30
HELPLINE_DELAY = 60

SENDER_EMAIL = os.getenv("SENTINEL_EMAIL", "")
SENDER_PASSWORD = os.getenv("SENTINEL_EMAIL_PASSWORD", "")
RECEIVER_EMAIL = os.getenv("SENTINEL_RECEIVER", "")
ACK_LINK = os.getenv("SENTINEL_ACK_LINK", "http://localhost:8501/trustee")


def send_email(subject: str, body: str):
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        st.warning("Email not configured — set SENTINEL_EMAIL and SENTINEL_EMAIL_PASSWORD in .env")
        return False
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Email failed: {e}")
        return False


def _play_alert():
    import math, struct
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


def trigger_crisis(patient_username: str):
    state = {
        "active": True,
        "patient": patient_username,
        "triggered_at": datetime.now().isoformat(),
        "acknowledged": False,
        "acknowledged_by": "",
        "helpline_escalated": False,
        "trusted_contact_notified": False,
        "trustee_acknowledged": False,
        "trustee_clicked": False,
    }
    set_crisis_state(state)
    st.session_state.crisis_active = True
    st.session_state.crisis_acknowledged = False
    st.session_state.trusted_notified = False
    st.session_state.helpline_called = False


def acknowledge_crisis(psychologist_username: str):
    state = get_crisis_state()
    if state.get("active"):
        state["acknowledged"] = True
        state["acknowledged_by"] = psychologist_username
        state["acknowledged_at"] = datetime.now().isoformat()
        set_crisis_state(state)
        st.session_state.crisis_acknowledged = True


def acknowledge_trustee():
    state = get_crisis_state()
    if state.get("active") and not state.get("acknowledged"):
        state["trustee_acknowledged"] = True
        set_crisis_state(state)


def trustee_link_clicked():
    state = get_crisis_state()
    if state.get("active") and not state.get("acknowledged"):
        state["trustee_clicked"] = True
        set_crisis_state(state)


def get_crisis_status() -> dict:
    state = get_crisis_state()
    if not state.get("active"):
        return {"active": False, "stage": "none"}

    triggered = datetime.fromisoformat(state["triggered_at"])
    now = datetime.now()
    elapsed = (now - triggered).total_seconds()

    psych_ack = state.get("acknowledged", False)
    trustee_ack = state.get("trustee_acknowledged", False)
    trustee_clicked = state.get("trustee_clicked", False)

    if psych_ack:
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
        "active": True,
        "stage": stage,
        "message": message,
        "elapsed": int(elapsed),
        "patient": state.get("patient", ""),
        "acknowledged": psych_ack,
        "trusted_notified": state.get("trusted_contact_notified", False),
        "helpline_escalated": state.get("helpline_escalated", False),
        "trustee_coming": trustee_ack,
        "trustee_clicked": trustee_clicked,
    }


def handle_escalation():
    state = get_crisis_state()
    if not state.get("active"):
        return
    if state.get("acknowledged") or state.get("trustee_acknowledged"):
        return
    if state.get("helpline_escalated"):
        return

    triggered = datetime.fromisoformat(state["triggered_at"])
    elapsed = (datetime.now() - triggered).total_seconds()

    if elapsed >= TRUSTED_CONTACT_DELAY and not state.get("trusted_contact_notified"):
        state["trusted_contact_notified"] = True
        set_crisis_state(state)
        subject = f"CRISIS ALERT — {state['patient']} — Trusted Contact Notification"
        body = (
            f"A crisis was triggered by {state['patient']} at {state['triggered_at']}.\n"
            f"Please acknowledge this alert immediately.\n\n"
            f"Acknowledge here: {ACK_LINK}"
        )
        send_email(subject, body)
    if elapsed >= HELPLINE_DELAY and not state.get("helpline_escalated"):
        state["helpline_escalated"] = True
        set_crisis_state(state)
        subject = f"CRISIS ESCALATION — {state['patient']} — Helpline Contacted"
        body = (
            f"A crisis was triggered by {state['patient']} at {state['triggered_at']}.\n"
            f"No acknowledgement was received within {HELPLINE_DELAY}s.\n\n"
            f"The helpline has been contacted.\n\n"
            f"To acknowledge: {ACK_LINK}"
        )
        send_email(subject, body)


def render_crisis_alarm():
    status = get_crisis_status()
    if not status["active"]:
        raw = get_crisis_state()
        if raw.get("active"):
            status = get_crisis_status()
        else:
            return

    st_autorefresh(interval=5000, key="crisis_alarm_poll")
    _play_alert()
    handle_escalation()

    stage = status["stage"]
    patient = status["patient"]

    if stage == "acknowledged":
        st.success(f"**Crisis Acknowledged** — {status['message']}")
        return

    if stage == "helpline_escalated":
        st.error(f"🚨 **CRISIS ESCALATION — HELPLINE CONTACTED** 🚨")
        st.markdown(
            "<div style='background:#7a0000;padding:15px;border-radius:8px;"
            "border:2px solid #ff4444;text-align:center;color:white;font-weight:bold;'>"
            "⚠️ IMMEDIATE INTERVENTION REQUIRED ⚠️</div>",
            unsafe_allow_html=True,
        )
    elif stage == "trustee_coming":
        st.info(f"🟢 **Trusted Contact En Route — {patient}**")
        st.markdown(
            "<div style='background:#1a4a1a;padding:12px;border-radius:8px;"
            "border:2px solid #44ff44;color:#88ff88;text-align:center;font-weight:bold;'>"
            "👤 TRUSTED CONTACT ON THE WAY — Psychologist acknowledgement still needed</div>",
            unsafe_allow_html=True,
        )
    elif stage == "trustee_clicked":
        st.info(f"👤 **Trusted Contact Notified — {patient}**")
        st.markdown(
            "<div style='background:#2a4a2a;padding:12px;border-radius:8px;"
            "border:1px solid #44cc44;color:#88ff88;text-align:center;font-weight:bold;'>"
            "👤 TRUSTED CONTACT NOTIFIED — Awaiting confirmation of arrival</div>",
            unsafe_allow_html=True,
        )
    elif stage == "trustee_notified":
        st.warning(f"⚠️ **Crisis Alert — {patient}**")
        st.markdown(
            f"<div style='background:#5a3a00;padding:12px;border-radius:8px;"
            f"border:1px solid #ffaa00;color:white;'>"
            f"Trusted contact emailed. Awaiting response.</div>",
            unsafe_allow_html=True,
        )
    else:
        st.error(f"🚨 **Emergency Siren — {patient}**")
        st.markdown(
            "<div style='background:#4a0000;padding:10px;border-radius:8px;"
            "border:1px solid #ff6666;color:#ff9999;text-align:center;'>"
            "🔴 SIREN ACTIVE — Patient triggered emergency</div>",
            unsafe_allow_html=True,
        )

    if not status["acknowledged"]:
        cols = st.columns([3, 1])
        with cols[1]:
            if st.button("✓ Acknowledge Crisis", type="primary", use_container_width=True):
                acknowledge_crisis(st.session_state.get("username", "clinician"))
                st.rerun()
