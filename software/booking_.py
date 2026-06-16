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

    _avail_date_objs = []
    if selected_psych:
        _avail = load_psych_availability(selected_psych)
        _avail_strs = sorted([a["date"] for a in _avail if a["date"] >= date.today().isoformat()])
        _avail_date_objs = [datetime.strptime(d, "%Y-%m-%d").date() for d in _avail_strs]
        _avail_set = set(_avail_strs)

    sel_key = f"bk_sel_{selected_psych}"
    avail_opts = []
    avail_map = {}
    if _avail_date_objs:
        for d in sorted([d for d in _avail_date_objs if d >= date.today()]):
            lbl = d.strftime("%a, %b %d %Y")
            avail_opts.append(lbl)
            avail_map[lbl] = d.isoformat()
    if avail_opts:
        st.markdown("#### Step 2: Select Date")
        selected_label = st.selectbox("Available dates", avail_opts, key=f"bk_dd_{selected_psych}")
        st.session_state[sel_key] = avail_map[selected_label]
    else:
        st.markdown("#### Step 2: Select Date")
        st.caption("No available dates. Your psychologist hasn't opened slots yet.")
        st.session_state.pop(sel_key, None)

    st.markdown("#### Step 3: Attendance")
    if "booking_member_count" not in st.session_state:
        st.session_state.booking_member_count = 1

    member_count = st.number_input("How many members are attending?", min_value=1, max_value=6, value=st.session_state.booking_member_count, step=1, key="count_trigger")
    st.session_state.booking_member_count = member_count

    with st.form("booking_request_form", clear_on_submit=True):
        st.markdown("#### Step 4: Session Details")
        cols_top = st.columns(3)
        bk_date = st.session_state.get(f"bk_sel_{selected_psych}", "")
        try:
            bk_date_obj = datetime.strptime(bk_date, "%Y-%m-%d").date() if bk_date else None
        except Exception:
            bk_date_obj = None
        if bk_date_obj:
            cols_top[0].markdown(f"<div style='color:#c0d0e0;font-size:0.9rem;padding:8px 0;'>📅 {bk_date_obj.strftime('%a, %b %d %Y')}</div>", unsafe_allow_html=True)
        else:
            cols_top[0].markdown("<div style='color:#5a4a5a;font-size:0.8rem;padding:8px 0;'>Click an available date above</div>", unsafe_allow_html=True)
        bk_time = cols_top[1].time_input("Time")
        session_type = cols_top[2].selectbox("Type", ["Therapy", "Follow-up", "Crisis Check-in", "Mindfulness"])

        st.markdown("---")
        st.markdown("#### Step 5: Member Details")
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
            elif not bk_date:
                st.error("Please select an available date from the list.")
            elif not contact.strip() or not explanation.strip():
                st.error("Please complete the Contact and Context fields.")
            elif any(not name.strip() for name, _ in members):
                st.error("Please provide names for all members.")
            else:
                member_text = "; ".join([f"{name.strip()} ({age})" for name, age in members])
                try:
                    save_booking(patient_name, bk_date, bk_time.strftime("%H:%M"), session_type, member_text, contact.strip(), explanation.strip(), psychologist_username=selected_psych)
                    st.success(f"Request sent to {selected_psych_label}!")
                except Exception as err:
                    st.error(f"System Error: {err}")


def _cal_ym_changed():
    st.session_state["cal_ym"] = (st.session_state.cal_y, st.session_state.cal_m)


def render_booking_queue(psych_username=None):
    st.markdown("### 📋 Booking Management")
    bookings = load_bookings()
    if psych_username:
        bookings = [b for b in bookings if b.get("psychologist_username", "") == psych_username]
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
            st.write(f"**Patient:** {item['patient']}")
            st.write(f"**Date:** {item['date']}")
            st.write(f"**Time:** {item['time']}")
            st.write(f"**Members:** {item.get('members', 'N/A')}")
            st.write(f"**Contact:** {item.get('contact', 'N/A')}")
            st.info(f"**Reason:** {item.get('explanation', 'N/A')}")

            current_status = item['status']

            if current_status == "Proposed":
                _ts = item.get("timestamp", item.get("date", ""))[:16]
                st.markdown(
                    f"<div style='background:#2a2a00;border:1px solid #f59e0b;border-radius:8px;padding:12px;margin:8px 0;'>"
                    f"<div style='color:#f59e0b;font-weight:600;margin-bottom:4px;'>💡 Proposed Appointment</div>"
                    f"<div style='color:#c0d0e0;font-size:0.8125rem;'>Proposed to <strong>{item['patient']}</strong> on <strong>{item['date']} @ {item['time']}</strong></div>"
                    f"<div style='color:#6a6474;font-size:0.6875rem;margin-top:4px;'>Proposed at: {_ts} — Awaiting patient response</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            elif current_status == "Declined":
                st.markdown(f"<div style='background:#2a0a0a;border:1px solid #ef4444;border-radius:8px;padding:8px;margin:4px 0;'><span style='color:#ef4444;'>❌ Patient declined this slot.</span></div>", unsafe_allow_html=True)
            elif current_status == "Pending":
                st.markdown("---")
                btn_cols = st.columns([1, 1, 2])
                if btn_cols[0].button("Accept", key=f"acc_{index}"):
                    update_booking_status(index, "Accepted")
                if current_status != "Waitlisted":
                    if btn_cols[1].button("Waitlist", key=f"wait_{index}"):
                        update_booking_status(index, "Waitlisted")


def render_booking_calendar(psych_username=""):
    today = date.today()
    _ym = st.session_state.get("cal_ym", (today.year, today.month))
    y, m = _ym

    cal1, cal2, _ = st.columns([1, 1, 4])
    with cal1:
        st.selectbox("Month", range(1, 13), index=m - 1, format_func=lambda x: calendar.month_name[x], key="cal_m", on_change=_cal_ym_changed)
    with cal2:
        st.selectbox("Year", range(today.year - 1, today.year + 3), index=1, key="cal_y", on_change=_cal_ym_changed)

    _ym2 = st.session_state.get("cal_ym", (today.year, today.month))
    y2, m2 = _ym2
    _, days_in_month2 = calendar.monthrange(y2, m2)
    first2 = date(y2, m2, 1)
    weekday2 = first2.weekday()

    _db_free = set()
    if psych_username:
        _avail = load_psych_availability(psych_username)
        _db_free = set(a["date"] for a in _avail)

    st.markdown("""
    <style>
    .cal-wrap { display:grid; grid-template-columns:repeat(7,1fr); gap:2px; margin-bottom:4px; }
    .cal-hdr { text-align:center; color:#5a4a5a; font-size:0.65rem; font-weight:600; padding:2px 0; }
    .cal-cell { text-align:center; font-size:0.75rem; padding:4px; border-radius:6px; cursor:default; }
    .cal-past { color:#4a5a6a; }
    .cal-day { color:#c0d0e0; }
    .cal-today { color:#c0d0e0; border:1px solid #c49ea4; }
    .cal-avail { background:#1a4a2a; color:#4ade80; font-weight:700; }
    </style>
    """, unsafe_allow_html=True)

    hdrs = "".join(f"<div class='cal-hdr'>{d}</div>" for d in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"])
    st.markdown(f"<div class='cal-wrap'>{hdrs}</div>", unsafe_allow_html=True)

    _cells = []
    for _ in range(weekday2):
        _cells.append("<div></div>")

    for d in range(1, days_in_month2 + 1):
        ds = f"{y2}-{m2:02d}-{d:02d}"
        is_free = ds in _db_free
        is_today = (y2, m2, d) == (today.year, today.month, today.day)
        is_past = date(y2, m2, d) < today
        _cls = "cal-cell"
        if is_past:
            _cls += " cal-past"
        elif is_free:
            _cls += " cal-avail"
        elif is_today:
            _cls += " cal-today"
        else:
            _cls += " cal-day"
        _cells.append(f"<div class='{_cls}'>{d}</div>")

    st.markdown(f"<div class='cal-wrap'>{''.join(_cells)}</div>", unsafe_allow_html=True)

    if psych_username:
        st.markdown("##### Block Unavailable Dates")
        _rows_needed = (weekday2 + days_in_month2 + 6) // 7
        day_num = 1
        for row in range(_rows_needed):
            cols = st.columns(7)
            for ci in range(7):
                if row == 0 and ci < weekday2:
                    cols[ci].write("")
                    continue
                if day_num > days_in_month2:
                    break
                ds = f"{y2}-{m2:02d}-{day_num:02d}"
                is_free = ds in _db_free
                is_past = date(y2, m2, day_num) < today
                with cols[ci]:
                    if is_past:
                        st.markdown(f"<div style='text-align:center;color:#4a5a6a;font-size:0.75rem;padding:4px;'>{day_num}</div>", unsafe_allow_html=True)
                    elif is_free:
                        if st.button(f"\u2716 {day_num}", key=f"cal_{ds}", use_container_width=True, type="primary"):
                            delete_psych_availability(psych_username, ds)
                    else:
                        if st.button(str(day_num), key=f"cal_{ds}", use_container_width=True, type="secondary"):
                            save_psych_availability(psych_username, ds)
                day_num += 1

        _free_count = len(_db_free)
        st.markdown("---")
        st.markdown(f"<div style='display:flex;gap:16px;font-size:0.75rem;'>"
                    f"<span><span style='display:inline-block;width:12px;height:12px;background:#ef4444;border-radius:3px;vertical-align:middle;margin-right:4px;'></span> Blocked ({_free_count})</span>"
                    f"<span style='color:#5a4a5a;'>Click a date to toggle available/blocked</span></div>", unsafe_allow_html=True)
