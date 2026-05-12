import streamlit as st
import json, os
from datetime import datetime

CRISIS_FILE = "data/crisis_state.json"

st.set_page_config(page_title="Trusted Contact — Sentinel", page_icon="👤")
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #0a0e1a 0%, #111827 50%, #0a1628 100%); }
    h1, p, div { color: #d0d8e8 !important; }
    .stButton > button { border-radius: 8px; font-weight: 500; }
    .stButton > button[kind="primary"] { background: linear-gradient(135deg, #2563eb, #1d4ed8); border: none; color: white; }
</style>
""", unsafe_allow_html=True)

def _read_crisis():
    if not os.path.exists(CRISIS_FILE):
        return None
    with open(CRISIS_FILE) as f:
        return json.load(f)

def _write_crisis(state):
    tmp = CRISIS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, CRISIS_FILE)

st.markdown("<h1 style='text-align:center;font-size:36px;'>👤 Trusted Contact Alert</h1>", unsafe_allow_html=True)

state = _read_crisis()
if not state or not state.get("active"):
    st.info("No active crisis at this time.")
    st.markdown("---")
st.caption("Sentinel — Crisis Response System")
    st.stop()

if state.get("acknowledged"):
    st.success("✅ This crisis has already been resolved. No further action needed.")
    st.stop()

patient = state.get("patient", "your loved one")
elapsed = int((datetime.now() - datetime.fromisoformat(state["triggered_at"])).total_seconds())

st.markdown(
    f"<p style='text-align:center;color:#d0d8e8;font-size:18px;'>"
    f"{patient} triggered a crisis alert <strong>{elapsed}s ago</strong>.</p>",
    unsafe_allow_html=True,
)

if state.get("trustee_acknowledged"):
    st.success("✅ **You have already responded.** Thank you — please proceed to check on them.")
    st.stop()

if "accepted" not in st.session_state:
    st.session_state.accepted = False

if not st.session_state.accepted:
    if state.get("trustee_clicked"):
        st.info("👤 **You have already been notified.**")
    else:
        st.info("👤 **You have been notified as a trusted contact.**")

    st.markdown(
        "<div style='background:#0d1117;border:1px solid #2a3050;border-radius:10px;"
        "padding:20px;text-align:center;'>"
        "<p style='color:#889;font-size:14px;'>This person needs your support. "
        "Please confirm you are on the way.</p></div>",
        unsafe_allow_html=True,
    )

    # Mark as clicked on first visit
    if not state.get("trustee_clicked") and not state.get("trustee_acknowledged"):
        state["trustee_clicked"] = True
        _write_crisis(state)

    if st.button("✅ Yes, I'm on my way!", type="primary", use_container_width=True):
        state["trustee_acknowledged"] = True
        _write_crisis(state)
        st.session_state.accepted = True
        st.rerun()
else:
    st.success("🚀 **Thank you!** Your status has been updated.")
    st.markdown(
        "<div style='background:#1a4a1a;border:1px solid #44ff44;border-radius:10px;"
        "padding:16px;text-align:center;color:#88ff88;font-weight:bold;'>"
        "👤 You are marked as 'On the Way'. The patient and psychologist have been notified.</div>",
        unsafe_allow_html=True,
    )

st.markdown("---")
st.caption("Sentinel — Crisis Response System")
