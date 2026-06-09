import streamlit as st
from datetime import datetime, date, timedelta
import calendar
try:
    from data_manager_ import load_bookings, save_booking, update_booking_status, save_psych_availability, delete_psych_availability, load_psych_availability
except Exception:
    load_bookings = save_booking = update_booking_status = save_psych_availability = delete_psych_availability = load_psych_availability = None


def render_booking_form(patient_name: str, clinic_psychs=None, patient_clinic=""):
    st.markdown("### 📅 Clinic Booking Portal")

    with st.container():
        bookings = load_bookings()
        patient_bookings = [b for b in bookings if b['patient'] == patient_name]
        if patient_bookings:
            latest_status = patient_bookings[-1]['status']
            if latest_status == "Accepted":
                st.success("✅ Your last request was **Accepted**. Check your contact for details.")
            elif latest_status == "Waitlisted":
                st.warning("⏳ You are currently on the **Waitlist**. We will notify you soon.")
            else:
                st.info("📩 Your request is **Pending Review** by the clinician.")

    psych_options = []
    psych_map = {}
    if clinic_psychs:
        for p in clinic_psychs:
            label = p["name"]
            psych_options.append(label)
            psych_map[label] = p["username"]
    if not psych_options:
        st.info("No psychologists available from your clinic yet. A psychologist must mark availability first.")
        return

    selected_psych_label = st.selectbox("Psychologist", psych_options, key="bk_psych_sel")
    selected_psych = psych_map.get(selected_psych_label, "")

    _avail_dates = []
    if selected_psych:
        _avail = load_psych_availability(selected_psych)
        _avail_dates = sorted([a["date"] for a in _avail if a["date"] >= date.today().isoformat()])
    if _avail_dates:
        st.markdown(f"<div style='color:#4ade80;font-size:0.8125rem;margin-bottom:8px;'>✅ {selected_psych_label} has {len(_avail_dates)} free date(s)</div>", unsafe_allow_html=True)

    st.markdown("#### Step 2: Attendance")
    if "booking_member_count" not in st.session_state:
        st.session_state.booking_member_count = 1

    member_count = st.number_input("How many members are attending?", min_value=1, max_value=6, value=st.session_state.booking_member_count, step=1, key="count_trigger")
    st.session_state.booking_member_count = member_count

    with st.form("booking_request_form", clear_on_submit=True):
        st.markdown("#### Step 3: Session Details")
        cols_top = st.columns(3)
        bk_date = cols_top[0].date_input("Date")
        bk_time = cols_top[1].time_input("Time")
        session_type = cols_top[2].selectbox("Type", ["Therapy", "Follow-up", "Crisis Check-in", "Mindfulness"])

        st.markdown("---")
        st.markdown("#### Step 4: Member Details")
        members = []
        for idx in range(member_count):
            c1, c2 = st.columns([3, 1])
            m_name = c1.text_input(f"Member {idx + 1} Full Name", key=f"name_input_{idx}")
            m_age = c2.number_input("Age", min_value=0, max_value=120, value=25, key=f"age_input_{idx}")
            members.append((m_name, m_age))

        st.markdown("---")
        contact = st.text_input("Preferred Contact (Phone/Email)")
        explanation = st.text_area("Context for the session", placeholder="Briefly describe the goal for this visit.")

        if st.form_submit_button("Submit Request"):
            if not selected_psych:
                st.error("Please select a psychologist.")
            elif not contact.strip() or not explanation.strip():
                st.error("Please complete the Contact and Context fields.")
            elif any(not name.strip() for name, _ in members):
                st.error("Please provide names for all members.")
            else:
                member_text = "; ".join([f"{name.strip()} ({age})" for name, age in members])
                try:
                    save_booking(patient_name, bk_date.isoformat(), bk_time.strftime("%H:%M"), session_type, member_text, contact.strip(), explanation.strip(), psychologist_username=selected_psych)
                    st.success(f"Request sent to {selected_psych_label}!")
                except Exception as err:
                    st.error(f"System Error: {err}")


def _cal_ym_changed():
    st.session_state["cal_ym"] = (st.session_state.cal_y, st.session_state.cal_m)


@st.fragment
def render_booking_queue(psych_username=None):
    st.markdown("### 📋 Booking Management")
    bookings = load_bookings()
    if psych_username:
        bookings = [b for b in bookings if b.get("psychologist_username", "") == psych_username or b.get("psychologist_username", "") == ""]
    if not bookings:
        st.info("The queue is currently empty.")
        return

    for index, item in enumerate(bookings):
        _s = item['status']
        _psych = item.get("psychologist_username", "")
        _psych_label = f" 🧑‍⚕️{_psych}" if _psych else ""
        status_color = {"Accepted": "🟢", "Waitlisted": "🟡", "Pending": "⚪", "Proposed": "💡", "Declined": "🔴", "Confirmed": "🟢"}.get(_s, "⚪")

        with st.expander(f"{status_color} {item['patient']}{_psych_label} — {item['date']} @ {item['time']}"):
            st.write(f"**Status:** {item['status']}")
            st.write(f"**Psychologist:** {_psych if _psych else 'Not assigned'}")
            st.write(f"**Members:** {item.get('members', 'N/A')}")
            st.write(f"**Contact:** {item.get('contact', 'N/A')}")
            st.info(f"**Reason:** {item.get('explanation', 'N/A')}")

            current_status = item['status']

            if current_status == "Proposed":
                st.markdown(f"<span style='color:#f59e0b;font-size:0.8125rem;'>💡 AI-suggested — waiting for patient to confirm.</span>", unsafe_allow_html=True)
            elif current_status == "Declined":
                st.markdown(f"<span style='color:#ef4444;font-size:0.8125rem;'>❌ Patient declined this AI-suggested slot.</span>", unsafe_allow_html=True)
            elif current_status == "Pending":
                st.markdown("---")
                btn_cols = st.columns([1, 1, 2])
                if btn_cols[0].button("Accept", key=f"acc_{index}"):
                    update_booking_status(index, "Accepted")
                if current_status != "Waitlisted":
                    if btn_cols[1].button("Waitlist", key=f"wait_{index}"):
                        update_booking_status(index, "Waitlisted")


@st.fragment
def render_booking_calendar(psych_username=""):
    today = date.today()
    _ym = st.session_state.get("cal_ym", (today.year, today.month))
    y, m = _ym
    first = date(y, m, 1)
    _, days_in_month = calendar.monthrange(y, m)
    weekday = first.weekday()

    cal1, cal2, _ = st.columns([1, 1, 4])
    with cal1:
        st.selectbox("Month", range(1, 13), index=m - 1, format_func=lambda x: calendar.month_name[x], key="cal_m", on_change=_cal_ym_changed)
    with cal2:
        st.selectbox("Year", range(today.year - 1, today.year + 3), index=1, key="cal_y", on_change=_cal_ym_changed)

    _ym2 = st.session_state.get("cal_ym", (today.year, today.month))
    y2, m2 = _ym2
    _, days_in_month2 = calendar.monthrange(y2, m2)

    bookings = load_bookings()
    booked = {}
    for b in bookings:
        try:
            bd = datetime.strptime(b["date"][:10], "%Y-%m-%d").date()
            if bd.year == y2 and bd.month == m2:
                booked.setdefault(bd.day, []).append(b)
        except ValueError:
            pass

    _db_free = set()
    if psych_username:
        _avail = load_psych_availability(psych_username)
        _db_free = set(a["date"] for a in _avail)

    days_header = "".join(f"<div style='text-align:center;color:#5a6a8a;font-size:0.65rem;padding:2px;'>{d}</div>" for d in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"])
    st.markdown(f"<div style='display:grid;grid-template-columns:repeat(7,1fr);gap:1px;'>{days_header}</div>", unsafe_allow_html=True)
    cells = []
    for _ in range(weekday):
        cells.append("<div></div>")
    for d in range(1, days_in_month2 + 1):
        ds = f"{y2}-{m2:02d}-{d:02d}"
        bs = booked.get(d, [])
        has_book = any(b["status"] in ("Accepted", "Confirmed", "Pending", "Proposed") for b in bs)
        is_free = ds in _db_free
        is_today = (y2, m2, d) == (today.year, today.month, today.day)
        bg = "#2a5a2a" if is_free else ("#2a3a5a" if has_book else ("#1a2940" if is_today else "#1a2238"))
        bdr = "2px solid #4ade80" if is_free else ("2px solid #3b82f6" if is_today else ("2px solid #4a7a5a" if has_book else "1px solid #1e3a5a"))
        names = ", ".join(b["patient"][:6] for b in bs[:2]) + ("\u2026" if len(bs) > 2 else "") if bs else ""
        extra = f"<div style='color:#7a8aaa;font-size:0.5rem;line-height:1;'>{names}</div>" if names else ""
        cells.append(f"<div style='background:{bg};border:{bdr};border-radius:6px;padding:2px;text-align:center;min-height:34px;display:flex;flex-direction:column;justify-content:center;'><div style='color:#c0d0e0;font-weight:600;font-size:0.75rem;'>{d}</div>{extra}</div>")
    st.markdown(f"<div style='display:grid;grid-template-columns:repeat(7,1fr);gap:2px;'>{''.join(cells)}</div>", unsafe_allow_html=True)
    st.markdown("---")

    if psych_username:
        st.markdown("##### Toggle Your Availability")
        col_row = st.columns(7)
        for i, d in enumerate(range(1, days_in_month2 + 1)):
            with col_row[i % 7]:
                ds = f"{y2}-{m2:02d}-{d:02d}"
                fg = ds in _db_free
                if st.button("✅" if fg else "⬜", key=f"cal_d_{ds}", help=f"{'Unmark' if fg else 'Mark'} {ds} as free", use_container_width=True):
                    if fg:
                        delete_psych_availability(psych_username, ds)
                    else:
                        save_psych_availability(psych_username, ds)
