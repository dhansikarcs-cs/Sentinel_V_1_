import streamlit as st

try:
    from patient_profiles_ import get_onboarding_step, set_onboarding_step, get_contact_info, set_contact_info, get_psych_trusted_contact, set_psych_trusted_contact, get_patient_name, get_patient_clinic
except Exception:
    get_onboarding_step = set_onboarding_step = get_contact_info = set_contact_info = get_psych_trusted_contact = set_psych_trusted_contact = get_patient_name = get_patient_clinic = None

try:
    from psych_shared_ import safe
except Exception:
    safe = None


@st.fragment
def render_psych_onboarding(username: str):
    db_step = safe(get_onboarding_step, 0, username)
    if db_step >= 99:
        st.session_state["_psych_onboarding"] = False
        return

    st.markdown("## \U0001f44b Welcome to Sentinel!")
    st.markdown(
        "<div style='background:linear-gradient(135deg, #1e2336, #2d2d44);border-radius:12px;padding:20px;margin:12px 0;'>"
        "<div style='color:#c0d0e0;font-size:0.9375rem;line-height:1.6;'>"
        "You are now registered as a <strong>psychologist</strong> on Sentinel. "
        "Monitor your patients\u2019 wellness, review AI-powered journal insights, manage bookings, "
        "and receive instant crisis alerts \u2014 all in one place."
        "</div></div>",
        unsafe_allow_html=True,
    )

    step = st.session_state.get("onboarding_step", db_step)
    progress = st.progress(step / 4, text=f"Step {step + 1} of 5")

    if step == 0:
        st.markdown("### \U0001f3e0 Step 1: Your Profile")
        clinic = safe(get_patient_clinic, "", username)
        doc_name = safe(get_patient_name, username, username)
        st.markdown(
            f"<div style='background:#1e2336;border:1px solid #2d2d44;border-radius:10px;padding:14px;margin:8px 0;'>"
            f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:10px;'>"
            f"<div><div style='color:#6a6474;font-size:0.75rem;'>Name</div>"
            f"<div style='color:#c0d0e0;font-size:1rem;font-weight:600;'>{doc_name}</div></div>"
            f"<div><div style='color:#6a6474;font-size:0.75rem;'>Clinic</div>"
            f"<div style='color:#c49ea4;font-size:1rem;font-weight:600;'>{clinic or 'Not assigned'}</div></div>"
            f"<div><div style='color:#6a6474;font-size:0.75rem;'>Username</div>"
            f"<div style='color:#c0d0e0;font-size:1rem;'>{username}</div></div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )
        if st.button("Next \u2192", key="psych_onb_step0", use_container_width=True, type="primary"):
            st.session_state.onboarding_step = 1
            safe(set_onboarding_step, None, username, 1)

    elif step == 1:
        st.markdown("### \U0001f4de Step 2: Your Contact Details")
        st.markdown(
            "<div style='color:#6a6474;font-size:0.8125rem;margin-bottom:8px;'>"
            "Provide a contact method (mobile or email) so patients can reach you for "
            "appointments, follow-ups, or questions.</div>",
            unsafe_allow_html=True,
        )
        existing_ci = safe(get_contact_info, "", username)
        ci = st.text_input("Mobile number or email", value=existing_ci, placeholder="e.g. +1 555-0123 or doctor@email.com")
        if st.button("Save \u2192", key="psych_onb_ci", use_container_width=True, type="primary"):
            if ci.strip():
                safe(set_contact_info, None, username, ci.strip())
            st.session_state.onboarding_step = 2
            safe(set_onboarding_step, None, username, 2)

    elif step == 2:
        st.markdown("### \U0001f465 Step 3: Trusted Contact (for Crisis Alerts)")
        st.markdown(
            "<div style='color:#6a6474;font-size:0.8125rem;margin-bottom:8px;'>"
            "If you trigger a self-crisis alert and cannot be reached, who should we notify? "
            "Provide a mobile number or email for your trusted contact.</div>",
            unsafe_allow_html=True,
        )
        existing_tc = safe(get_psych_trusted_contact, "", username)
        tc = st.text_input("Trusted contact mobile or email", value=existing_tc, placeholder="e.g. +1 555-9999 or spouse@email.com")
        if st.button("Save \u2192", key="psych_onb_tc", use_container_width=True, type="primary"):
            if tc.strip():
                safe(set_psych_trusted_contact, None, username, tc.strip())
            st.session_state.onboarding_step = 3
            safe(set_onboarding_step, None, username, 3)

    elif step == 3:
        st.markdown("### \U0001f52e Step 4: Quick Tips")
        st.markdown(
            "<div style='background:#1e2336;border:1px solid #2d2d44;border-radius:10px;padding:16px;margin:8px 0;'>"
            "<div style='display:flex;gap:12px;margin-bottom:10px;'>"
            "<span style='color:#c49ea4;font-size:1.2rem;'>\U0001f4ac</span>"
            "<div><div style='color:#c0d0e0;font-weight:600;font-size:0.875rem;'>AI Journal Summaries</div>"
            "<div style='color:#6a6474;font-size:0.75rem;'>Your patients\u2019 journal entries are summarized by AI. Review them in the Clinical Notes tab.</div></div></div>"
            "<div style='display:flex;gap:12px;margin-bottom:10px;'>"
            "<span style='color:#4ade80;font-size:1.2rem;'>\u26a0\ufe0f</span>"
            "<div><div style='color:#c0d0e0;font-weight:600;font-size:0.875rem;'>Crisis Alerts</div>"
            "<div style='color:#6a6474;font-size:0.75rem;'>Elevated vitals or high-risk journal entries trigger instant alerts. Acknowledge and escalate from the dashboard.</div></div></div>"
            "<div style='display:flex;gap:12px;'>"
            "<span style='color:#fbbf24;font-size:1.2rem;'>\U0001f4c5</span>"
            "<div><div style='color:#c0d0e0;font-weight:600;font-size:0.875rem;'>Availability & Bookings</div>"
            "<div style='color:#6a6474;font-size:0.75rem;'>Set your available dates in the Booking tab. Patients will book based on their assigned psychologist.</div></div></div>"
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button("Finish \u2192", key="psych_onb_tips", use_container_width=True, type="primary"):
            st.session_state.onboarding_step = 4
            safe(set_onboarding_step, None, username, 4)

    elif step >= 4:
        st.markdown("### \u2705 You\u2019re all set!")
        st.markdown(
            "<div style='background:#1e2336;border:1px solid #22c55e30;border-radius:10px;padding:16px;margin:12px 0;text-align:center;'>"
            "<div style='color:#22c55e;font-size:1.25rem;font-weight:700;'>\u2705 Onboarding Complete</div>"
            "<div style='color:#6a6474;font-size:0.8125rem;margin-top:6px;'>"
            "Your dashboard is ready. Use the tabs above to manage patients, view journals, set your availability, and more.</div></div>",
            unsafe_allow_html=True,
        )
        if st.button("Open Dashboard \U0001f680", key="psych_onb_done", use_container_width=True, type="primary"):
            st.session_state.onboarding_step = 99
            safe(set_onboarding_step, None, username, 99)
            st.session_state["_psych_onboarding"] = False
            st.rerun()

    return True
