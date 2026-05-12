import streamlit as st
from data_manager import load_bookings, save_booking, update_booking_status


def render_booking_form(patient_name: str):
    st.markdown("### 📅 Clinic Booking Portal")

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

    st.markdown("#### Step 1: Attendance")
    if "booking_member_count" not in st.session_state:
        st.session_state.booking_member_count = 1

    member_count = st.number_input(
        "How many members are attending?",
        min_value=1, max_value=6,
        value=st.session_state.booking_member_count,
        step=1, key="count_trigger",
    )
    st.session_state.booking_member_count = member_count

    with st.form("booking_request_form", clear_on_submit=True):
        st.markdown("#### Step 2: Session Details")
        cols_top = st.columns(3)
        date = cols_top[0].date_input("Date")
        time = cols_top[1].time_input("Time")
        session_type = cols_top[2].selectbox("Type", ["Therapy", "Follow-up", "Crisis Check-in", "Mindfulness"])

        st.markdown("---")
        st.markdown("#### Step 3: Member Details")
        members = []
        for idx in range(member_count):
            c1, c2 = st.columns([3, 1])
            m_name = c1.text_input(f"Member {idx + 1} Full Name", key=f"name_input_{idx}")
            m_age = c2.number_input("Age", min_value=0, max_value=120, value=25, key=f"age_input_{idx}")
            members.append((m_name, m_age))

        st.markdown("---")
        contact = st.text_input("Preferred Contact (Phone/Email)")
        explanation = st.text_area("Context for the session", placeholder="Briefly describe the goal for this visit.")

        submitted = st.form_submit_button("Submit Request")

        if submitted:
            if not contact.strip() or not explanation.strip():
                st.error("Please complete the Contact and Context fields.")
            elif any(not name.strip() for name, _ in members):
                st.error("Please provide names for all members.")
            else:
                member_text = "; ".join([f"{name.strip()} ({age})" for name, age in members])
                try:
                    save_booking(
                        patient_name,
                        date.isoformat(),
                        time.strftime("%H:%M"),
                        session_type,
                        member_text,
                        contact.strip(),
                        explanation.strip(),
                    )
                    st.success("Request sent!")
                except Exception as err:
                    st.error(f"System Error: {err}")


def render_booking_queue():
    st.markdown("### 📋 Booking Management")
    bookings = load_bookings()
    if not bookings:
        st.info("The queue is currently empty.")
        return

    for index, item in enumerate(bookings):
        status_color = "🟢" if item['status'] == "Accepted" else "🟡" if item['status'] == "Waitlisted" else "⚪"

        with st.expander(f"{status_color} {item['patient']} — {item['date']} @ {item['time']}"):
            st.write(f"**Status:** {item['status']}")
            st.write(f"**Members:** {item.get('members', 'N/A')}")
            st.write(f"**Contact:** {item.get('contact', 'N/A')}")
            st.info(f"**Reason:** {item.get('explanation', 'N/A')}")

            current_status = item['status']

            if current_status != "Accepted":
                st.markdown("---")
                btn_cols = st.columns([1, 1, 2])

                if btn_cols[0].button("Accept", key=f"acc_{index}"):
                    update_booking_status(index, "Accepted")
                    st.rerun()

                if current_status != "Waitlisted":
                    if btn_cols[1].button("Waitlist", key=f"wait_{index}"):
                        update_booking_status(index, "Waitlisted")
                        st.rerun()
