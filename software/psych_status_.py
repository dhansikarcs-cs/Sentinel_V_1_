import streamlit as st

try:
    from data_manager_ import load_bookings, get_patient_history
except Exception:
    load_bookings = get_patient_history = None

try:
    from patient_profiles_ import get_all_patients
except Exception:
    get_all_patients = None

try:
    from psych_shared_ import safe
except Exception:
    safe = None


def render_psych_status(username: str):
    patients = safe(get_all_patients, [])
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

    cols = st.columns(4)
    with cols[0]:
        st.markdown(
            f"<div style='background:#1a2238;border:1px solid #1e2940;border-radius:10px;padding:10px;text-align:center;'>"
            f"<div style='color:#7a8aaa;font-size:0.6875rem;font-weight:500;'>Patients</div>"
            f"<div style='color:#60a5fa;font-size:1.125rem;font-weight:700;'>{n_patients}</div>"
            f"<div style='color:#5a6a8a;font-size:0.625rem;'>under care</div></div>",
            unsafe_allow_html=True,
        )
    with cols[1]:
        color = "#22c55e" if n_proposed == 0 else "#f59e0b"
        st.markdown(
            f"<div style='background:#1a2238;border:1px solid {color}30;border-radius:10px;padding:10px;text-align:center;'>"
            f"<div style='color:#7a8aaa;font-size:0.6875rem;font-weight:500;'>Pending</div>"
            f"<div style='color:{color};font-size:1.125rem;font-weight:700;'>{n_proposed}</div>"
            f"<div style='color:{color};font-size:0.625rem;'>booking approvals</div></div>",
            unsafe_allow_html=True,
        )
    with cols[2]:
        color = "#22c55e" if silent == 0 else "#ef4444"
        st.markdown(
            f"<div style='background:#1a2238;border:1px solid {color}30;border-radius:10px;padding:10px;text-align:center;'>"
            f"<div style='color:#7a8aaa;font-size:0.6875rem;font-weight:500;'>Silent</div>"
            f"<div style='color:{color};font-size:1.125rem;font-weight:700;'>{silent}</div>"
            f"<div style='color:{color};font-size:0.625rem;'>patients >48h</div></div>",
            unsafe_allow_html=True,
        )
    with cols[3]:
        st.markdown(
            f"<div style='background:#1a2238;border:1px solid #c97bff30;border-radius:10px;padding:10px;text-align:center;'>"
            f"<div style='color:#7a8aaa;font-size:0.6875rem;font-weight:500;'>Crisis</div>"
            f"<div style='color:#7a8aaa;font-size:0.875rem;font-weight:600;'>\u2014</div>"
            f"<div style='color:#5a6a8a;font-size:0.625rem;'>see alert above</div></div>",
            unsafe_allow_html=True,
        )
