import streamlit as st
from datetime import date

try:
    from ring_ import get_ring_data
except Exception:
    get_ring_data = None

try:
    from data_manager_ import get_patient_history, load_bookings
except Exception:
    get_patient_history = load_bookings = None

try:
    from patient_shared_ import safe
except Exception:
    safe = None


def render_patient_status(username: str):
    ring = safe(get_ring_data, {"bpm":72,"stress":35,"sleep":7,"spo2":98,"mood":"neutral"}, username, 1.0)
    entries = safe(get_patient_history, [], username)
    today_str = date.today().isoformat()
    journaled_today = any(e["timestamp"].startswith(today_str) for e in entries) if entries else False

    bookings = safe(load_bookings, [])
    my_bookings = [b for b in bookings if b["patient"] == username]
    confirmed = [b for b in my_bookings if b["status"] in ("Accepted", "Pending")]
    proposals = [b for b in my_bookings if b["status"] == "Proposed"]

    cols = st.columns(4)
    with cols[0]:
        st.markdown(
            f"<div style='background:#1a2238;border:1px solid #1e2940;border-radius:10px;padding:10px;text-align:center;'>"
            f"<div style='color:#7a8aaa;font-size:0.6875rem;font-weight:500;'>Heart</div>"
            f"<div style='color:#ff6b6b;font-size:1.125rem;font-weight:700;'>{ring['bpm']}</div>"
            f"<div style='color:#5a6a8a;font-size:0.625rem;'>bpm</div></div>",
            unsafe_allow_html=True,
        )
    with cols[1]:
        color = "#22c55e" if journaled_today else "#f59e0b"
        icon = "\u2705" if journaled_today else "\u270f\ufe0f"
        label = "Written today" if journaled_today else "Not yet today"
        st.markdown(
            f"<div style='background:#1a2238;border:1px solid {color}30;border-radius:10px;padding:10px;text-align:center;'>"
            f"<div style='color:#7a8aaa;font-size:0.6875rem;font-weight:500;'>Journal</div>"
            f"<div style='color:{color};font-size:1.125rem;font-weight:700;'>{icon}</div>"
            f"<div style='color:{color};font-size:0.625rem;'>{label}</div></div>",
            unsafe_allow_html=True,
        )
    with cols[2]:
        if confirmed:
            b = confirmed[-1]
            st.markdown(
                f"<div style='background:#1a2238;border:1px solid #60a5fa30;border-radius:10px;padding:10px;text-align:center;'>"
                f"<div style='color:#7a8aaa;font-size:0.6875rem;font-weight:500;'>Next Session</div>"
                f"<div style='color:#60a5fa;font-size:0.8125rem;font-weight:600;'>{b['date'][5:]}</div>"
                f"<div style='color:#60a5fa;font-size:0.75rem;'>{b['time']}</div></div>",
                unsafe_allow_html=True,
            )
        elif proposals:
            st.markdown(
                f"<div style='background:#1a2238;border:1px solid #f59e0b30;border-radius:10px;padding:10px;text-align:center;'>"
                f"<div style='color:#7a8aaa;font-size:0.6875rem;font-weight:500;'>Proposals</div>"
                f"<div style='color:#f59e0b;font-size:1.125rem;font-weight:700;'>{len(proposals)}</div>"
                f"<div style='color:#f59e0b;font-size:0.625rem;'>pending</div></div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div style='background:#1a2238;border:1px solid #1e2940;border-radius:10px;padding:10px;text-align:center;'>"
                f"<div style='color:#7a8aaa;font-size:0.6875rem;font-weight:500;'>Bookings</div>"
                f"<div style='color:#7a8aaa;font-size:0.875rem;font-weight:600;'>\u2014</div>"
                f"<div style='color:#5a6a8a;font-size:0.625rem;'>none</div></div>",
                unsafe_allow_html=True,
            )
    with cols[3]:
        mood = ring["mood"].title()
        st.markdown(
            f"<div style='background:#1a2238;border:1px solid #c97bff30;border-radius:10px;padding:10px;text-align:center;'>"
            f"<div style='color:#7a8aaa;font-size:0.6875rem;font-weight:500;'>Mood</div>"
            f"<div style='color:#c97bff;font-size:1.125rem;font-weight:700;'>{mood}</div>"
            f"<div style='color:#5a6a8a;font-size:0.625rem;'>today</div></div>",
            unsafe_allow_html=True,
        )
