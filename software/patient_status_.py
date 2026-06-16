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

    st.markdown("""
    <style>
    .stat-card {background:#1e2336;border:1px solid #2d2d44;border-radius:8px;padding:8px 12px;display:flex;align-items:center;gap:12px;}
    .stat-val {font-size:1.125rem;font-weight:700;}
    .stat-label {color:#6a6474;font-size:0.6875rem;font-weight:500;}
    </style>
    """, unsafe_allow_html=True)

    cols = st.columns(4)
    with cols[0]:
        st.markdown(f"<div class='stat-card'><div><div class='stat-label'>Heart</div><div class='stat-val' style='color:#ff6b6b;'>{ring['bpm']}</div></div><div style='color:#5a4a5a;font-size:0.625rem;'>bpm</div></div>", unsafe_allow_html=True)
    with cols[1]:
        c = "#22c55e" if journaled_today else "#f59e0b"
        lbl = "Written today" if journaled_today else "Not yet today"
        ico = chr(10003) if journaled_today else chr(9999)
        st.markdown(f"<div class='stat-card'><div><div class='stat-label'>Journal</div><div class='stat-val' style='color:{c};'>{ico}</div></div><div style='color:{c};font-size:0.625rem;'>{lbl}</div></div>", unsafe_allow_html=True)
    with cols[2]:
        if confirmed:
            b = confirmed[-1]
            st.markdown(f"<div class='stat-card'><div><div class='stat-label'>Next Session</div><div class='stat-val' style='color:#c49ea4;font-size:0.8125rem;'>{b['date'][5:]} @ {b['time']}</div></div></div>", unsafe_allow_html=True)
        elif proposals:
            st.markdown(f"<div class='stat-card'><div><div class='stat-label'>Proposals</div><div class='stat-val' style='color:#f59e0b;'>{len(proposals)}</div></div><div style='color:#f59e0b;font-size:0.625rem;'>pending</div></div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='stat-card'><div><div class='stat-label'>Bookings</div><div class='stat-val' style='color:#6a6474;'>\u2014</div></div><div style='color:#5a4a5a;font-size:0.625rem;'>none</div></div>", unsafe_allow_html=True)
    with cols[3]:
        mood = ring["mood"].title()
        st.markdown(f"<div class='stat-card'><div><div class='stat-label'>Mood</div><div class='stat-val' style='color:#c49ea4;'>{mood}</div></div><div style='color:#5a4a5a;font-size:0.625rem;'>today</div></div>", unsafe_allow_html=True)
