import streamlit as st

try:
    from patient_profiles_ import authenticate, register_user, get_patient_name, get_psychologist_name
except Exception:
    authenticate = register_user = get_patient_name = get_psychologist_name = None


def render_login():
    _header()
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_signin, tab_register = st.tabs(["Sign In", "Register New User"])
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
    st.markdown("##### Demo Credentials")
    cols = st.columns(2)
    with cols[0]:
        st.markdown("**Patients**")
        st.code("test_patient_1 / test123  (CLINIC_ALPHA)")
        st.code("test_patient_5 / test123  (CLINIC_BETA)")
        st.code("test_patient_10 / test123 (CLINIC_GAMMA)")
        st.code("test_extra_1 / extra123")
    with cols[1]:
        st.markdown("**Psychologists**")
        st.code("test_psych_1 / doc123  (CLINIC_ALPHA)")
        st.code("test_psych_2 / doc123  (CLINIC_BETA)")
        st.code("test_psych_3 / doc123  (CLINIC_GAMMA)")
        st.code("test_psych_4 / doc123  (CLINIC_DELTA)")
        st.code("test_psych_5 / doc123  (CLINIC_EPSILON)")
        st.code("test_extra_3 / extra123")


def _register_tab():
    st.markdown("#### Create Account")
    is_psych = st.checkbox("I am a Psychologist", key="reg_is_psych")
    with st.form("register_form"):
        r_username = st.text_input("Username")
        r_password = st.text_input("Password", type="password")
        r_password_confirm = st.text_input("Confirm Password", type="password")
        r_name = st.text_input("Full Name")
        r_age = st.number_input("Age", min_value=1, max_value=120, value=25, step=1)
        r_occupation = st.text_input("Occupation")
        clinic_code = st.text_input("Clinic Code", help="Contact your clinic to get a registration code")
        prof_code = ""
        if st.session_state.get("reg_is_psych", False):
            st.markdown("""
            <div class="psych-box">
                <div class="psych-box-title">Psychologist Verification</div>
                <div class="psych-box-desc">Enter your unique profession code to verify your credentials.</div>
            </div>
            """, unsafe_allow_html=True)
            prof_code = st.text_input("Profession Code", help="Provided by the clinic for psychologist registration")
        submitted = st.form_submit_button("Register", type="primary", use_container_width=True)

    if submitted:
        _handle_registration(r_username, r_password, r_password_confirm, r_name, r_age, r_occupation, clinic_code, prof_code)


def _handle_registration(r_username, r_password, r_password_confirm, r_name, r_age, r_occupation, clinic_code, prof_code):
    if not all([r_username, r_password, r_password_confirm, r_name, r_occupation, clinic_code]):
        st.error("All fields except Profession Code are required.")
    elif r_password != r_password_confirm:
        st.error("Passwords do not match.")
    elif st.session_state.get("reg_is_psych", False) and not prof_code:
        st.error("Profession Code is required for psychologist registration.")
    else:
        role = "psychologist" if st.session_state.get("reg_is_psych", False) else "patient"
        ok, msg = register_user(
            r_username.strip(), r_password, r_name.strip(),
            r_age, r_occupation.strip(), role, clinic_code.strip(),
            prof_code.strip() if prof_code else None,
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
