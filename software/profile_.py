import streamlit as st

try:
    from patient_profiles_ import authenticate, get_patient_name, get_patient_clinic, get_contact_info, set_contact_info, get_any_trusted_contact, set_any_trusted_contact, get_psych_trusted_contact, set_psych_trusted_contact
except Exception:
    authenticate = get_patient_name = get_patient_clinic = get_contact_info = set_contact_info = get_any_trusted_contact = set_any_trusted_contact = get_psych_trusted_contact = set_psych_trusted_contact = None

try:
    from psych_shared_ import safe
except Exception:
    def safe(func, default=None, *args, **kwargs):
        try:
            if func is not None:
                return func(*args, **kwargs)
        except Exception:
            pass
        return default if default is not None else {}


def render_profile(username: str):
    role = st.session_state.get("role", "")
    doc_name = safe(get_patient_name, username, username)
    clinic = safe(get_patient_clinic, "", username)
    contact_info = safe(get_contact_info, "", username)
    if role == "Psychologist":
        trusted_contact = safe(get_psych_trusted_contact, "", username)
    else:
        trusted_contact = safe(get_any_trusted_contact, "", username)

    st.markdown("### \U0001f464 My Profile")
    _dash = "\u2014"
    st.markdown(
        "<div style='background:#1e2336;border:1px solid #2d2d44;border-radius:10px;padding:16px;margin:8px 0;'>"
        "<div style='display:grid;grid-template-columns:1fr 1fr;gap:12px;'>"
        f"<div><div style='color:#6a6474;font-size:0.75rem;'>Name</div>"
        f"<div style='color:#c0d0e0;font-size:1rem;font-weight:600;'>{doc_name}</div></div>"
        f"<div><div style='color:#6a6474;font-size:0.75rem;'>Username</div>"
        f"<div style='color:#c0d0e0;font-size:1rem;'>{username}</div></div>"
        f"<div><div style='color:#6a6474;font-size:0.75rem;'>Clinic</div>"
        f"<div style='color:#c49ea4;font-size:1rem;font-weight:600;'>{clinic or 'Not assigned'}</div></div>"
        f"<div><div style='color:#6a6474;font-size:0.75rem;'>Contact</div>"
        f"<div style='color:#c0d0e0;font-size:0.9rem;'>{contact_info or _dash}</div></div>"
        f"<div style='grid-column:1/-1;'><div style='color:#6a6474;font-size:0.75rem;'>Trusted Contact (Crisis)</div>"
        f"<div style='color:#c0d0e0;font-size:0.9rem;'>{trusted_contact or _dash}</div></div>"
        "</div></div>",
        unsafe_allow_html=True,
    )

    if not st.session_state.get("profile_edit_auth", False):
        if st.button("\u270f Edit Profile", key="prof_edit_btn", use_container_width=True, type="primary"):
            st.session_state.profile_edit_auth = True
            st.rerun()
    else:
        st.markdown("---")
        st.markdown("#### \u270f Edit Profile")
        pwd = st.text_input("Enter your password to edit", type="password", key="prof_pwd")
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Authenticate", key="prof_auth", use_container_width=True, type="primary"):
                if authenticate and authenticate(username, pwd):
                    st.session_state.profile_editing = True
                    st.rerun()
                else:
                    st.error("Incorrect password")
        with col2:
            if st.button("Cancel", key="prof_cancel", use_container_width=True):
                st.session_state.profile_edit_auth = False
                st.rerun()

        if st.session_state.get("profile_editing", False):
            st.markdown("---")
            new_ci = st.text_input("Contact info (mobile or email)", value=contact_info, key="prof_ci")
            new_tc = st.text_input("Trusted contact (mobile or email)", value=trusted_contact, key="prof_tc")
            sc1, sc2 = st.columns([1, 1])
            with sc1:
                if st.button("Save Changes", key="prof_save", use_container_width=True, type="primary"):
                    if new_ci.strip():
                        safe(set_contact_info, None, username, new_ci.strip())
                    if new_tc.strip():
                        if role == "Psychologist":
                            safe(set_psych_trusted_contact, None, username, new_tc.strip())
                        else:
                            safe(set_any_trusted_contact, None, username, new_tc.strip())
                    st.session_state.profile_editing = False
                    st.session_state.profile_edit_auth = False
                    st.success("Profile updated")
                    st.rerun()
            with sc2:
                if st.button("Discard", key="prof_discard", use_container_width=True):
                    st.session_state.profile_editing = False
                    st.rerun()

    if st.button("\u2190 Back to Dashboard", key="prof_back", use_container_width=True):
        st.session_state.show_profile = False
        st.rerun()
