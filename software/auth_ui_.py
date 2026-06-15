import streamlit as st

try:
    from patient_profiles_ import authenticate, register_user, get_patient_name, get_psychologist_name, get_clinic_psychs_for_registration
except Exception:
    authenticate = register_user = get_patient_name = get_psychologist_name = get_clinic_psychs_for_registration = None


def render_login():
    _header()
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_signin, tab_register = st.tabs(["Sign In", "Register"])
        with tab_signin:
            _signin_tab()
        with tab_register:
            _register_tab()


def _header():
    st.markdown(
        "<h1 style='text-align:center;font-size:2.5rem;background:linear-gradient(135deg,#60a5fa,#a78bfa);"
        "-webkit-background-clip:text;-webkit-text-fill-color:transparent;"
        "margin-bottom:0.25rem;'>"
        "\U0001f9e0 Sentinel</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center;color:#7a8aaa;font-size:1rem;"
        "margin-top:0;'>"
        "AI-Assisted Mental Health Ecosystem</p>",
        unsafe_allow_html=True,
    )


def _signin_tab():
    st.markdown("#### Sign In")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Authenticate", type="primary", use_container_width=True):
            role = authenticate(username, password)
            if role:
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.role = role
                if role == "Patient":
                    st.session_state.patient_name = get_patient_name(username)
                else:
                    st.session_state.psychologist_name = get_psychologist_name(username)
                st.rerun()
            else:
                st.error("Invalid credentials. Check ACCOUNTS.md for valid accounts.")

    st.markdown("---")
    st.markdown("##### Demo Accounts")
    st.code("Patient:  cel / 123456")
    st.code("Psych:    alaya / 654321")


def _register_tab():
    st.markdown("#### Create Account")

    role_choice = st.radio("I am a...", ["Patient", "Psychologist"], horizontal=True, key="reg_role")

    clinic_code = st.text_input("Clinic Code", key="reg_clinic_code", help="Enter the clinic code provided by your clinic")

    assigned_psych = ""
    prof_code = ""

    if role_choice == "Psychologist":
        st.markdown("""
        <div style="background:#1a2238;border:1px solid #7c3aed;border-radius:10px;padding:14px;margin:8px 0;">
            <div style="color:#a78bfa;font-size:0.8125rem;font-weight:600;margin-bottom:6px;">\U0001f9ec Psychologist Verification</div>
        """, unsafe_allow_html=True)
        prof_code = st.text_input("Profession Code", key="reg_prof_code", help="Provided by your clinic for psychologist registration")
        st.markdown("</div>", unsafe_allow_html=True)
    elif role_choice == "Patient" and clinic_code.strip():
        st.markdown("""
        <div style="background:#1a2238;border:1px solid #60a5fa;border-radius:10px;padding:14px;margin:8px 0;">
            <div style="color:#60a5fa;font-size:0.8125rem;font-weight:600;margin-bottom:6px;">\U0001f465 Select Your Psychologist</div>
        """, unsafe_allow_html=True)
        try:
            psychs = get_clinic_psychs_for_registration(clinic_code.strip())
        except Exception:
            psychs = []
        if psychs:
            psych_options = {f"{p['name']} (@{p['username']})": p["username"] for p in psychs}
            st.selectbox("Psychologist", list(psych_options.keys()), key="reg_psych_sel", label_visibility="collapsed")
        else:
            st.markdown("<div style='color:#7a8aaa;font-size:0.75rem;'>No psychologists found in this clinic yet.</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with st.form("register_form"):
        r_username = st.text_input("Username")
        r_password = st.text_input("Password", type="password")
        r_password_confirm = st.text_input("Confirm Password", type="password")
        r_name = st.text_input("Full Name")
        r_age = st.number_input("Age", min_value=1, max_value=120, value=25, step=1)
        r_occupation = st.text_input("Occupation")

        submitted = st.form_submit_button("Register", type="primary", use_container_width=True)

    if submitted:
        _assigned = st.session_state.get("reg_psych_sel", "")
        if _assigned:
            try:
                psych_opts = {f"{p['name']} (@{p['username']})": p["username"] for p in (get_clinic_psychs_for_registration(clinic_code.strip()) if clinic_code.strip() else [])}
                _assigned = psych_opts.get(_assigned, _assigned)
            except Exception:
                pass
        _handle_registration(r_username, r_password, r_password_confirm, r_name, r_age, r_occupation, clinic_code, role_choice, prof_code, _assigned)


def _handle_registration(r_username, r_password, r_password_confirm, r_name, r_age, r_occupation, clinic_code, role_choice, prof_code="", assigned_psych=""):
    if not all([r_username, r_password, r_password_confirm, r_name, r_occupation, clinic_code]):
        st.error("All fields are required.")
    elif r_password != r_password_confirm:
        st.error("Passwords do not match.")
    elif role_choice == "Psychologist" and not prof_code:
        st.error("Profession Code is required for psychologist registration.")
    elif role_choice == "Patient" and not assigned_psych:
        st.error("Please select a psychologist from your clinic.")
    else:
        role = "psychologist" if role_choice == "Psychologist" else "patient"
        ok, msg = register_user(
            r_username.strip(), r_password, r_name.strip(),
            r_age, r_occupation.strip(), role, clinic_code.strip(),
            prof_code.strip() if prof_code else None,
            assigned_psych,
        )
        if ok:
            st.session_state.authenticated = True
            st.session_state.username = r_username.strip()
            st.session_state.role = "Patient" if role == "patient" else "Psychologist"
            if role == "patient":
                st.session_state.patient_name = r_name.strip()
            else:
                st.session_state.psychologist_name = r_name.strip()
            st.rerun()
        else:
            st.error(msg)
