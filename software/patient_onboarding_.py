import streamlit as st

try:
    from data_manager_ import get_patient_history, save_journal_entry
except Exception:
    get_patient_history = save_journal_entry = None

try:
    from patient_profiles_ import get_patient_clinic
except Exception:
    get_patient_clinic = None

try:
    from patient_shared_ import safe
except Exception:
    safe = None


def _has_journaled(username: str) -> bool:
    entries = safe(get_patient_history, [], username)
    return len(entries) > 0


def render_patient_onboarding(username: str) -> bool:
    if _has_journaled(username):
        return False

    st.markdown("## \U0001f44b Welcome to Sentinel!")
    st.markdown(
        "<div style='background:linear-gradient(135deg, #1a2238, #1e2940);border-radius:12px;padding:20px;margin:12px 0;'>"
        "<div style='color:#c0d0e0;font-size:0.9375rem;line-height:1.6;'>"
        "Sentinel connects you with your psychologist through <strong>real-time wellness monitoring</strong>, "
        "<strong>AI-powered journal insights</strong>, and <strong>smart crisis detection</strong>. "
        "Your ring data, journal entries, and vitals work together to keep you safe."
        "</div></div>",
        unsafe_allow_html=True,
    )

    step = st.session_state.get("onboarding_step", 0)
    progress = st.progress(step / 3, text=f"Step {step + 1} of 4")

    if step == 0:
        st.markdown("### \U0001f3e0 Step 1: About You")
        clinic = safe(get_patient_clinic, "", username)
        st.markdown(
            f"<div style='background:#1a2238;border:1px solid #1e2940;border-radius:10px;padding:14px;margin:8px 0;'>"
            f"<div style='color:#7a8aaa;font-size:0.75rem;'>Your Clinic</div>"
            f"<div style='color:#60a5fa;font-size:1rem;font-weight:600;'>{clinic or 'Not assigned'}</div>"
            f"<div style='color:#7a8aaa;font-size:0.75rem;margin-top:4px;'>"
            f"You\u2019re registered and connected. A psychologist from your clinic will review your journals and vitals.</div></div>",
            unsafe_allow_html=True,
        )
        if st.button("Next \u2192", key="onb_step0", use_container_width=True, type="primary"):
            st.session_state.onboarding_step = 1

    elif step == 1:
        st.markdown("### \U0001f4dd Step 2: Your First Journal Entry")
        st.markdown(
            "<div style='color:#7a8aaa;font-size:0.8125rem;margin-bottom:8px;'>"
            "Write about how you\u2019re feeling today. Your psychologist will see an AI summary.</div>",
            unsafe_allow_html=True,
        )
        with st.form("onboarding_journal"):
            text = st.text_area("How are you feeling?", placeholder="Write freely...", height=120)
            if st.form_submit_button("Save & Continue", type="primary", use_container_width=True):
                if text.strip():
                    summary = safe(lambda t: t[:200] + ("..." if len(t) > 200 else ""), "Onboarding entry", text)
                    safe(save_journal_entry, None, username, text, summary)
                    st.session_state.onboarding_step = 2
                else:
                    st.warning("Write something first, or skip below.")

        if st.button("Skip \u2192", key="onb_skip1"):
            st.session_state.onboarding_step = 2

    elif step == 2:
        st.markdown("### \U0001f6e1\ufe0f Step 3: Emergency & Trusted Contact")
        st.markdown(
            "<div style='color:#7a8aaa;font-size:0.8125rem;margin-bottom:8px;'>"
            "If you ever trigger a crisis alert, your trusted contact will be notified. "
            "You can set or update this later in your profile.</div>",
            unsafe_allow_html=True,
        )
        existing = st.session_state.get("trusted_contact", "")
        tc = st.text_input("Trusted contact email or phone (optional)", value=existing, placeholder="e.g. partner@email.com")
        if st.button("Save \u2192", key="onb_tc", use_container_width=True, type="primary"):
            if tc:
                st.session_state.trusted_contact = tc
            st.session_state.onboarding_step = 3

    elif step >= 3:
        st.markdown("### \u2705 You\u2019re all set!")
        st.markdown(
            "<div style='background:#1a2238;border:1px solid #22c55e30;border-radius:10px;padding:16px;margin:12px 0;text-align:center;'>"
            "<div style='color:#22c55e;font-size:1.25rem;font-weight:700;'>\u2705 Onboarding Complete</div>"
            "<div style='color:#7a8aaa;font-size:0.8125rem;margin-top:6px;'>"
            "Your dashboard is ready. Explore the tabs to check your wellness, journal, manage bookings, and more.</div></div>",
            unsafe_allow_html=True,
        )
        if st.button("Open Dashboard \U0001f680", key="onb_done", use_container_width=True, type="primary"):
            st.session_state.onboarding_step = 99
            st.rerun()

    return True
