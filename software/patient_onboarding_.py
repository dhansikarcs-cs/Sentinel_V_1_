import streamlit as st

try:
    from data_manager_ import get_patient_history, save_journal_entry
except Exception:
    get_patient_history = save_journal_entry = None

try:
    from patient_profiles_ import get_patient_clinic, get_onboarding_step, set_onboarding_step, get_contact_info, set_contact_info
except Exception:
    get_patient_clinic = get_onboarding_step = set_onboarding_step = get_contact_info = set_contact_info = None

try:
    from patient_shared_ import safe
except Exception:
    safe = None

STEPS = [
    ("\U0001f3e0", "About You"),
    ("\U0001f4dd", "First Entry"),
    ("\U0001f6e1\ufe0f", "Emergency"),
    ("\U0001f4f1", "Contact"),
]


@st.fragment
def render_patient_onboarding(username: str):
    db_step = safe(get_onboarding_step, 0, username)
    if db_step >= 99:
        st.session_state["_patient_onboarding"] = False
        return

    st.markdown("""
    <div style="text-align:center;margin-bottom:24px;">
        <div style="font-size:2rem;font-weight:700;background:linear-gradient(135deg,#c49ea4,#d8b4ba);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">
            Welcome to Sentinel
        </div>
        <div style="color:#6a6474;font-size:0.85rem;margin-top:4px;">
            Let's get you set up in a few quick steps
        </div>
    </div>
    """, unsafe_allow_html=True)

    step = st.session_state.get("onboarding_step", db_step)

    step_labels = [label for _, label in STEPS]
    current_idx = min(step, len(STEPS))
    cols = st.columns(len(STEPS))
    for i, (emoji, label) in enumerate(STEPS):
        with cols[i]:
            done = i < current_idx
            active = i == current_idx
            if done:
                bg = "#1a3a2a"
                border = "#22c55e40"
                color = "#22c55e"
                icon = "\u2705"
            elif active:
                bg = "#2a2040"
                border = "#c49ea460"
                color = "#c49ea4"
                icon = emoji
            else:
                bg = "#1e2336"
                border = "#2d2d44"
                color = "#5a4a5a"
                icon = emoji
            st.markdown(
                f"<div style='background:{bg};border:1px solid {border};border-radius:8px;padding:10px 6px;text-align:center;transition:all 0.3s;'>"
                f"<div style='font-size:1.2rem;'>{icon}</div>"
                f"<div style='color:{color};font-size:0.65rem;font-weight:{'600' if active or done else '400'};margin-top:2px;'>{label}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<div style='margin:16px 0;'>", unsafe_allow_html=True)

    if step == 0:
        st.markdown("### \U0001f3e0 About You")
        clinic = safe(get_patient_clinic, "", username)
        st.markdown(
            f"<div style='background:linear-gradient(135deg,#1e2336,#1e2a45);border:1px solid #2d2d44;border-radius:12px;padding:20px;margin:12px 0;'>"
            f"<div style='color:#6a6474;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.5px;'>Your Clinic</div>"
            f"<div style='color:#e0e8f0;font-size:1.1rem;font-weight:600;margin-top:4px;'>{clinic or 'Not assigned'}</div>"
            f"<div style='color:#6a6474;font-size:0.75rem;margin-top:8px;line-height:1.5;'>"
            f"You\u2019re registered with your clinic. A psychologist will review your journals and vitals to support your well-being.</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        if st.button("Next Step \u2192", key="onb_step0", use_container_width=True, type="primary"):
            st.session_state.onboarding_step = 1
            safe(set_onboarding_step, None, username, 1)

    elif step == 1:
        st.markdown("### \U0001f4dd Your First Journal Entry")
        st.markdown(
            "<div style='color:#6a6474;font-size:0.8rem;margin-bottom:12px;'>"
            "Write a few lines about how you\u2019re feeling. Your psychologist will see an AI summary — your raw words stay private.</div>",
            unsafe_allow_html=True,
        )
        text = st.text_area("", placeholder="How are you feeling right now?", height=140, label_visibility="collapsed")
        cols = st.columns([1, 1])
        with cols[0]:
            if st.button("Save & Continue", type="primary", use_container_width=True):
                if text.strip():
                    summary = safe(lambda t: t[:200] + ("..." if len(t) > 200 else ""), "Onboarding entry", text)
                    safe(save_journal_entry, None, username, text, summary)
                    st.session_state.onboarding_step = 2
                    safe(set_onboarding_step, None, username, 2)
                else:
                    st.warning("Write something first.")
        with cols[1]:
            if st.button("Skip for now", use_container_width=True):
                st.session_state.onboarding_step = 2
                safe(set_onboarding_step, None, username, 2)

    elif step == 2:
        st.markdown("### \U0001f6e1\ufe0f Emergency Contact")
        st.markdown(
            "<div style='color:#6a6474;font-size:0.8rem;margin-bottom:12px;'>"
            "If you trigger a crisis alert, your trusted contact will be notified. "
            "You can update this later in your profile.</div>",
            unsafe_allow_html=True,
        )
        existing_tc = st.session_state.get("trusted_contact", "")
        tc = st.text_input("Trusted contact email or phone", value=existing_tc, placeholder="e.g. partner@email.com", label_visibility="visible")
        cols = st.columns([1, 1])
        with cols[0]:
            if st.button("Save \u2192", key="onb_tc", use_container_width=True, type="primary"):
                if tc:
                    st.session_state.trusted_contact = tc
                st.session_state.onboarding_step = 3
                safe(set_onboarding_step, None, username, 3)
        with cols[1]:
            if st.button("Skip", use_container_width=True):
                st.session_state.onboarding_step = 3
                safe(set_onboarding_step, None, username, 3)

    elif step == 3:
        st.markdown("### \U0001f4f1 Contact Preference")
        st.markdown(
            "<div style='color:#6a6474;font-size:0.8rem;margin-bottom:12px;'>"
            "How should your psychologist reach you for appointments or check-ins?</div>",
            unsafe_allow_html=True,
        )
        existing_ci = safe(get_contact_info, "", username)
        ci = st.text_input("Mobile number or email", value=existing_ci, placeholder="e.g. +1 555-0123", label_visibility="visible")
        cols = st.columns([1, 1])
        with cols[0]:
            if st.button("Save \u2192", key="onb_ci", use_container_width=True, type="primary"):
                if ci.strip():
                    safe(set_contact_info, None, username, ci.strip())
                st.session_state.onboarding_step = 4
                safe(set_onboarding_step, None, username, 4)
        with cols[1]:
            if st.button("Skip", use_container_width=True):
                st.session_state.onboarding_step = 4
                safe(set_onboarding_step, None, username, 4)

    elif step >= 4:
        st.markdown(
            f"<div style='background:linear-gradient(135deg,#1a1e30,#1a3a2a);border:1px solid #22c55e40;border-radius:16px;padding:32px;margin:12px 0;text-align:center;'>"
            f"<div style='font-size:3rem;margin-bottom:8px;'>\u2705</div>"
            f"<div style='color:#22c55e;font-size:1.5rem;font-weight:700;'>You\u2019re all set!</div>"
            f"<div style='color:#6a6474;font-size:0.85rem;margin-top:8px;line-height:1.6;'>"
            f"Your dashboard is ready. Track your wellness, write journal entries, manage bookings, and more.</div>"
            f"<div style='margin-top:20px;'>"
            f"<button onclick=\"document.querySelector('[data-testid=\\'baseButton-primary\\']').click()\" style='background:linear-gradient(135deg,#22c55e,#16a34a);border:none;color:white;padding:10px 32px;border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer;'>Open Dashboard \U0001f680</button>"
            f"</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        if st.button("Open Dashboard \U0001f680", key="onb_done", use_container_width=True, type="primary"):
            st.session_state.onboarding_step = 99
            safe(set_onboarding_step, None, username, 99)
            st.session_state["_patient_onboarding"] = False
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
