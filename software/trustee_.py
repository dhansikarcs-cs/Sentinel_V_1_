import streamlit as st
from datetime import datetime


_ADDRESSES = {
    "test_patient_1": "42 Lakeview Drive, Apt 7B, Portland, OR 97201",
    "test_patient_2": "815 Maple Street, House #3, Portland, OR 97202",
    "test_patient_3": "1200 Pine Avenue, Unit 12, Portland, OR 97203",
}


def render_trustee_portal():
    from patient_profiles_ import get_patient_name
    from data_manager_ import get_crisis_state

    st.markdown("<h1 style='text-align:center;font-size:36px;'>\U0001f464 Trusted Contact Portal</h1>", unsafe_allow_html=True)
    _state = _safe(get_crisis_state, None)
    if not _state or not _state.get("active"):
        st.info("No active crisis at this time.")
        st.stop()
    if _state.get("acknowledged"):
        st.success("\u2705 This crisis has been resolved. No further action needed.")
        st.stop()
    if _state.get("trustee_acknowledged"):
        st.success("\u2705 **You have already responded.** Please proceed to check on them.")
        st.stop()

    _patient = _state.get("patient", "your loved one")
    _elapsed = int((datetime.now() - datetime.fromisoformat(_state["triggered_at"])).total_seconds())
    _address = _ADDRESSES.get(_patient, "Address on file")
    st.markdown(
        f"<p style='text-align:center;color:#d0d8e8;font-size:1.125rem;'>"
        f"{get_patient_name(_patient)} triggered a crisis alert <strong>{_elapsed}s ago</strong>.</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='background:#161d30;border:1px solid #1e2940;border-radius:10px;padding:16px;margin:12px 0;'>"
        f"<span style='color:#7a8aaa;font-size:0.8125rem;'>\U0001f4cd Last known location</span><br>"
        f"<span style='color:#e0e8f5;font-size:1rem;font-weight:600;'>{_address}</span></div>",
        unsafe_allow_html=True,
    )

    if "trustee_accepted" not in st.session_state:
        st.session_state.trustee_accepted = False

    if not st.session_state.trustee_accepted:
        if not _state.get("trustee_clicked") and not _state.get("trustee_acknowledged"):
            try:
                from crisis_ import trustee_link_clicked
                trustee_link_clicked()
            except Exception:
                pass
        if st.button("\u2705 Yes, I'm on my way!", type="primary", use_container_width=True):
            try:
                from crisis_ import acknowledge_trustee
                acknowledge_trustee()
            except Exception:
                pass
            st.session_state.trustee_accepted = True
            st.rerun()
    else:
        st.success("\U0001f680 **Thank you!** Your status has been updated.")
        st.markdown(
            "<div style='background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.3);"
            "border-radius:10px;padding:16px;text-align:center;color:#6ee7a7;font-weight:600;'>"
            "\U0001f464 You are marked as 'On the Way'.</div>",
            unsafe_allow_html=True,
        )
    st.markdown("---")
    st.caption("Sentinel \u2014 Crisis Response System")
    st.stop()


def _safe(func, default=None, *args, **kwargs):
    try:
        if func is not None:
            return func(*args, **kwargs)
    except Exception:
        pass
    return default
