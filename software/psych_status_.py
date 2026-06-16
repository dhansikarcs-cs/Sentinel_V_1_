import streamlit as st

try:
    from data_manager_ import load_bookings, get_patient_history
except Exception:
    load_bookings = get_patient_history = None

try:
    from patient_profiles_ import get_assigned_patients
except Exception:
    get_assigned_patients = None


try:
    from psych_shared_ import safe
except Exception:
    safe = None


def render_psych_status(username: str):
    patients = safe(get_assigned_patients, [], username)
    n_patients = len(patients)

    bookings = safe(load_bookings, [])
    proposed = [b for b in bookings if b.get("status") == "Proposed" and b.get("psychologist_username") == username]
    n_proposed = len(proposed)

    silent = 0
    for p in patients:
        entries = safe(get_patient_history, [], p)
        if not entries:
            silent += 1
        else:
            from datetime import datetime, timedelta
            last = entries[-1]["timestamp"]
            try:
                if datetime.now() - datetime.fromisoformat(last) > timedelta(hours=48):
                    silent += 1
            except Exception:
                silent += 1

    st.markdown("""
    <style>
    .stat-card {background:#1e2336;border:1px solid #2d2d44;border-radius:8px;padding:8px 12px;display:flex;align-items:center;gap:12px;}
    .stat-val {font-size:1.125rem;font-weight:700;}
    .stat-label {color:#6a6474;font-size:0.6875rem;font-weight:500;}
    </style>
    """, unsafe_allow_html=True)

    cols = st.columns(4)
    with cols[0]:
        st.markdown(f"<div class='stat-card'><div><div class='stat-label'>Patients</div><div class='stat-val' style='color:#c49ea4;'>{n_patients}</div></div><div style='color:#5a4a5a;font-size:0.625rem;'>under care</div></div>", unsafe_allow_html=True)
    with cols[1]:
        c = "#22c55e" if n_proposed == 0 else "#f59e0b"
        st.markdown(f"<div class='stat-card'><div><div class='stat-label'>Pending</div><div class='stat-val' style='color:{c};'>{n_proposed}</div></div><div style='color:{c};font-size:0.625rem;'>booking approvals</div></div>", unsafe_allow_html=True)
    with cols[2]:
        c = "#22c55e" if silent == 0 else "#ef4444"
        st.markdown(f"<div class='stat-card'><div><div class='stat-label'>Silent</div><div class='stat-val' style='color:{c};'>{silent}</div></div><div style='color:{c};font-size:0.625rem;'>patients >48h</div></div>", unsafe_allow_html=True)
    with cols[3]:
        st.markdown(f"<div class='stat-card'><div><div class='stat-label'>Crisis</div><div class='stat-val' style='color:#6a6474;'>\u2014</div></div><div style='color:#5a4a5a;font-size:0.625rem;'>see alert above</div></div>", unsafe_allow_html=True)
