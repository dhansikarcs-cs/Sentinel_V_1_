import streamlit as st
from datetime import date

from patient_profiles_ import get_patient_clinic, get_clinic_psychologists, get_assigned_psych, get_psychologist_name, get_contact_info
try:
    from data_manager_ import get_available_psychologists
except Exception:
    get_available_psychologists = None

try:
    from crisis_ import get_crisis_status, handle_escalation
except Exception:
    get_crisis_status = handle_escalation = None

try:
    from data_manager_ import load_bookings
except Exception:
    load_bookings = None

try:
    from smart_room_ import render_smart_room
except Exception:
    render_smart_room = None

try:
    from booking_ import render_booking_form
except Exception:
    render_booking_form = None

try:
    from followup_ import render_patient_followup
except Exception:
    render_patient_followup = None

try:
    from patient_shared_ import safe
except Exception:
    safe = lambda func=None, default=None, *a, **kw: default if default is not None else {}

try:
    from patient_wellness_ import render_patient_wellness
except Exception:
    render_patient_wellness = None

try:
    from patient_journal_ import render_patient_journal
except Exception:
    render_patient_journal = None

try:
    from patient_emergency_ import render_patient_emergency
except Exception:
    render_patient_emergency = None

try:
    from patient_status_ import render_patient_status
except Exception:
    render_patient_status = None

try:
    from activity_feed_ import render_activity_feed
except Exception:
    render_activity_feed = None

try:
    from patient_onboarding_ import render_patient_onboarding
except Exception:
    render_patient_onboarding = None

try:
    from patient_profiles_ import get_onboarding_step
except Exception:
    get_onboarding_step = None

try:
    from dashboard_tour_ import render_dashboard_tour
except Exception:
    render_dashboard_tour = None


def render_patient_portal():
    username = st.session_state.username
    patient_name = st.session_state.get("patient_name", username)

    # ── Profile settings (triggered from sidebar) ──
    if st.session_state.get("show_profile", False):
        try:
            from profile_ import render_profile
            render_profile(username)
        except Exception:
            st.error("Profile settings unavailable.")
        return

    # ── Onboarding wizard for first-time patients ──
    db_step = get_onboarding_step(username) if get_onboarding_step else 99
    st.session_state["_patient_onboarding"] = db_step < 99
    if db_step < 99:
        try:
            if render_patient_onboarding:
                render_patient_onboarding(username)
        except Exception:
            pass
        return

    # ── Auto-refresh to detect crisis state changes ──
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=5000, key="patient_poll")
    except Exception:
        pass

    st.markdown(f"# \U0001f33f Welcome, {patient_name}")
    try:
        _assigned_psych = get_assigned_psych(username)
        if _assigned_psych:
            _psych_name = safe(get_psychologist_name, _assigned_psych, _assigned_psych)
            _psych_email = safe(get_contact_info, "", _assigned_psych)
            st.markdown(
                f"<div style='font-size:0.8125rem;color:#7a8aaa;margin-bottom:8px;'>"
                f"\U0001f489 Your psychologist: <strong style='color:#c0d0e0;'>{_psych_name}</strong>"
                f" &nbsp;|&nbsp; \U0001f4e7 <span style='color:#60a5fa;'>{_psych_email}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
    except Exception:
        pass
    st.markdown("---")

    # ── Crisis banner ──
    try:
        crisis = safe(get_crisis_status, {"active": False, "stage": "", "elapsed": 0})
        if crisis["active"] and crisis["patient"] == username:
            safe(handle_escalation)
            if crisis.get("acknowledged"):
                st.success(f"Crisis acknowledged. Support is active. {crisis['message']}")
            elif crisis.get("trustee_coming"):
                st.info("\U0001f7e1 **Trusted contact is on the way.**")
            elif crisis.get("trustee_clicked"):
                st.info("\U0001f464 **Trusted contact has been notified.** They will confirm shortly.")
            elif crisis.get("stage") == "trustee_notified":
                st.warning("\U0001f464 **Trusted contact has been emailed.** Awaiting confirmation.")
            elif crisis.get("stage") == "helpline_escalated":
                st.error("\U0001f6a8 **Crisis escalated to helpline.** Help is being dispatched.")
            else:
                st.error("\U0001f6a8 **Emergency siren is active.** A psychologist has been alerted.")
                st.markdown("<div style='background:rgba(239,68,68,0.12);padding:12px;border-radius:8px;color:#fca5a5;text-align:center;font-weight:600;'>Help is on the way. You are not alone.</div>", unsafe_allow_html=True)

            elapsed = min(crisis.get("elapsed", 0), 60)
            stage = crisis.get("stage", "triggered")
            is_terminal = stage in ("acknowledged", "trustee_coming", "trustee_clicked", "helpline_escalated")
            stages = [("triggered", "\U0001f6a8 Triggered", 0), ("trustee_notified", "\U0001f464 Trusted Contact", 30), ("helpline_escalated", "\U0001f3e5 Helpline", 60)]
            bars_html = ""
            for key, label, sec in stages:
                active = key == stage or (is_terminal and stage == "trustee_coming" and key == "trustee_notified")
                passed = elapsed >= sec
                if not active:
                    active = is_terminal and stage in ("helpline_escalated", "acknowledged") and key == "helpline_escalated"
                fc = "#ef4444" if active else ("#22c55e" if passed else "#3a4a5a")
                bg = "rgba(239,68,68,0.15)" if active else ("rgba(34,197,94,0.12)" if passed else "rgba(26,34,56,0.6)")
                bd = "1px solid rgba(239,68,68,0.4)" if active else ("1px solid rgba(34,197,94,0.3)" if passed else "1px solid #1e2940")
                bars_html += f"<div style='flex:1;text-align:center;padding:8px;margin:0 4px;border-radius:8px;background:{bg};border:{bd};color:{fc};font-size:0.8125rem;font-weight:600;'>{label}<br><span style='font-size:0.6875rem;font-weight:400;'>{sec}s</span></div>"
            display_time = "60+" if crisis.get("elapsed", 0) >= 60 else str(elapsed)
            status_tag = ""
            if stage == "helpline_escalated":
                status_tag = "<span style='color:#f87171;font-weight:600;'>\U0001f3e5 Helpline contacted</span>"
            elif stage == "trustee_coming":
                status_tag = "<span style='color:#4ade80;font-weight:600;'>\U0001f464 Trusted contact on the way</span>"
            elif stage == "trustee_clicked":
                status_tag = "<span style='color:#6ee7a7;font-weight:600;'>\U0001f464 Trusted contact notified</span>"
            elif stage == "acknowledged":
                status_tag = "<span style='color:#4ade80;font-weight:600;'>\u2705 Psychologist acknowledged</span>"
            st.markdown(
                f"<div style='background:#161d30;border:1px solid #1e2940;border-radius:10px;padding:12px;margin-top:8px;'>"
                f"<div style='display:flex;align-items:center;gap:12px;margin-bottom:8px;'>"
                f"<span style='color:#fca5a5;font-size:1.125rem;'>\u23f1\ufe0f</span>"
                f"<span style='color:#f0f4ff;font-size:1.25rem;font-weight:700;'>{display_time}s</span>"
                f"<span style='color:#7a8aaa;font-size:0.8125rem;'>elapsed</span>"
                f"<div style='margin-left:auto;'>{status_tag}</div>"
                f"</div>"
                f"<div style='display:flex;'>{bars_html}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
    except Exception:
        pass

    # ── Booking notification ──
    try:
        if "booking_notified" not in st.session_state:
            st.session_state.booking_notified = {}
        bookings = safe(load_bookings, [])
        my_bookings = [b for b in bookings if b["patient"] == username]
        if my_bookings:
            latest = my_bookings[-1]
            idx = len(bookings) - 1 - bookings[::-1].index(latest)
            prev_status = st.session_state.booking_notified.get(str(idx))
            _is_ai = "AI-suggested" in latest.get("explanation", "")
            _tab = "Psych Suggested" if _is_ai else "Book Appointment"
            if latest["status"] in ("Accepted", "Waitlisted", "Proposed", "Declined") and prev_status != latest["status"]:
                if latest["status"] == "Accepted":
                    st.success(f"\u2705 **Booking Accepted!** Your session has been confirmed. Check the **{_tab}** tab.")
                elif latest["status"] == "Waitlisted":
                    st.warning(f"\u23f3 **Booking Waitlisted.** Check the **{_tab}** tab for updates.")
                elif latest["status"] == "Proposed":
                    st.info(f"\U0001f4a1 **New appointment proposed!** Your psychologist suggested a slot. Check the **Psych Suggested** tab to confirm or decline.")
                elif latest["status"] == "Declined":
                    st.info(f"\u2139\ufe0f **Appointment declined.** That slot is no longer available. Check the **{_tab}** tab to book a different time.")
                st.session_state.booking_notified[str(idx)] = latest["status"]
    except Exception:
        pass

    # ── Today's Overview ──
    try:
        render_patient_status(username)
    except Exception:
        pass

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

    # ── Tab content helpers ──

    def _pt_booking_actions(bookings):
        for _bi, _b in enumerate(bookings):
            st.markdown(
                f"<div style='background:linear-gradient(135deg,#1a2238,#1e2a45);border:1px solid #f59e0b;"
                f"border-radius:10px;padding:14px;margin:8px 0;'>"
                f"<div style='color:#f59e0b;font-size:0.9rem;font-weight:600;'>"
                f"{_b['date']} @ {_b['time']}</div>"
                f"<div style='color:#7a8aaa;font-size:0.75rem;margin-top:4px;'>{_b.get('explanation','')}</div>"
                f"</div>", unsafe_allow_html=True,
            )
            _ac1, _ac2 = st.columns(2)
            with _ac1:
                if st.button(f"Accept", key=f"pt_bk_acc_{_bi}", type="primary", use_container_width=True):
                    from data_manager_ import update_booking_status_by_id, load_bookings
                    _all_b = load_bookings()
                    _real_idx = next((i for i, x in enumerate(_all_b) if x == _b), None)
                    if _real_idx is not None:
                        update_booking_status_by_id(_real_idx, "Accepted")
                        st.success("Accepted!")
                        st.rerun()
            with _ac2:
                if st.button(f"Decline", key=f"pt_bk_dec_{_bi}", use_container_width=True):
                    from data_manager_ import update_booking_status_by_id, load_bookings
                    _all_b = load_bookings()
                    _real_idx = next((i for i, x in enumerate(_all_b) if x == _b), None)
                    if _real_idx is not None:
                        update_booking_status_by_id(_real_idx, "Declined")
                        st.info("Declined.")
                        st.rerun()

    def _pt_smart_room_toggle():
        if st.button("⚡ Intense" if st.session_state.get("patient_room_intense", False) else "🌙 Calm", key="pt_room_toggle", use_container_width=True):
            st.session_state.patient_room_intense = not st.session_state.patient_room_intense
            st.rerun()

    def _render_wellness_tab():
        try:
            render_patient_wellness(username)
        except Exception:
            st.error("Wellness dashboard unavailable.")

    def _render_journal_tab():
        try:
            render_patient_journal(username)
        except Exception:
            st.error("Journal tab unavailable.")

    def _render_booking_tab():
        try:
            from data_manager_ import load_bookings, update_booking_status_by_id, load_psych_availability
            _all_my = [b for b in load_bookings() if b["patient"] == username]
            _ai_bookings = [b for b in _all_my if "AI-suggested" in b.get("explanation", "")]
            _manual_bookings = [b for b in _all_my if "AI-suggested" not in b.get("explanation", "")]
            _btabs = st.tabs(["\U0001f4e9 Psych Suggested", "\U0001f4c5 Book Appointment"])
            with _btabs[0]:
                _proposed = [b for b in _ai_bookings if b["status"] == "Proposed"]
                _past_ai = [b for b in _ai_bookings if b["status"] != "Proposed"]
                if _proposed:
                    st.markdown(
                        f"<div style='background:#1a2238;border:1px solid #f59e0b;border-radius:10px;padding:14px;margin:8px 0;'>"
                        f"<div style='color:#f59e0b;font-size:0.75rem;font-weight:600;'>\U0001f4a1 NEW \u2014 Psychologist Suggested</div>"
                        f"<div style='color:#7a8aaa;font-size:0.75rem;margin-top:4px;'>"
                        f"Your psychologist recommended the following appointment. "
                        f"Accept to request a review or decline to suggest a different time.</div></div>",
                        unsafe_allow_html=True,
                    )
                    _pt_booking_actions(_proposed)
                else:
                    st.info("No suggestions from your psychologist yet.")
                if _past_ai:
                    st.markdown("#### History")
                    for _b in reversed(_past_ai[-5:]):
                        _icon = {"Accepted": "\u2705", "Declined": "\u274c", "Waitlisted": "\U0001f7e1", "Pending": "\u23f3"}.get(_b["status"], "\u26aa")
                        _clr = {"Accepted": "#22c55e", "Declined": "#ef4444", "Waitlisted": "#f59e0b", "Pending": "#60a5fa"}.get(_b["status"], "#7a8aaa")
                        st.markdown(
                            f"<div style='font-size:0.75rem;padding:4px 0;color:#c0d0e0;line-height:1.5;'>"
                            f"{_icon} <strong>{_b['date']} @ {_b['time']}</strong> \u2014 "
                            f"<span style='color:{_clr};'>{_b['status']}</span></div>",
                            unsafe_allow_html=True,
                        )
            with _btabs[1]:
                _clinic = get_patient_clinic(username)
                _psychs = []
                if _clinic:
                    _psychs = get_clinic_psychologists(_clinic)
                    if not _psychs:
                        _psychs = get_available_psychologists(_clinic)
                safe(render_booking_form, None, username, _psychs, _clinic)
                if _manual_bookings:
                    st.markdown("#### Your Requests")
                    for _b in reversed(_manual_bookings[-5:]):
                        _icon = {"Accepted": "\u2705", "Declined": "\u274c", "Waitlisted": "\U0001f7e1", "Pending": "\u23f3"}.get(_b["status"], "\u26aa")
                        _clr = {"Accepted": "#22c55e", "Declined": "#ef4444", "Waitlisted": "#f59e0b", "Pending": "#60a5fa"}.get(_b["status"], "#7a8aaa")
                        st.markdown(
                            f"<div style='font-size:0.75rem;padding:4px 0;color:#c0d0e0;line-height:1.5;'>"
                            f"{_icon} <strong>{_b['date']} @ {_b['time']}</strong> \u2014 "
                            f"<span style='color:{_clr};'>{_b['status']}</span></div>",
                            unsafe_allow_html=True,
                        )
        except Exception:
            st.error("Booking unavailable.")

    def _render_followup_tab():
        try:
            safe(render_patient_followup, None, username)
        except Exception:
            st.error("Follow-Up unavailable.")

    def _render_smart_room_tab():
        try:
            head_col1, head_col2 = st.columns([3, 1])
            with head_col1:
                st.markdown("### \U0001f9e0 Smart Room")
            with head_col2:
                _pt_smart_room_toggle()
            room_mode = "intense" if st.session_state.get("patient_room_intense", False) else "calm"
            safe(render_smart_room, None, room_mode, 2.0 if room_mode == "intense" else 1.0)
        except Exception:
            st.error("Smart Room unavailable.")

    def _render_emergency_tab():
        try:
            render_patient_emergency(username)
        except Exception:
            st.error("Emergency section unavailable.")

    # ── Tab selector (segmented control works with tour) ──
    _pt_tab_names = ["\U0001f4ca Wellness", "\U0001f4dd Journal", "\U0001f4c5 Booking", "\U0001f4cb Follow-Up", "\U0001f9e0 Smart Room", "\U0001f6ae Emergency"]
    _pt_renderers = [_render_wellness_tab, _render_journal_tab, _render_booking_tab, _render_followup_tab, _render_smart_room_tab, _render_emergency_tab]

    _tour_tab = render_dashboard_tour("Patient") if render_dashboard_tour else ""
    if _tour_tab:
        st.session_state["pt_selected_tab"] = _tour_tab

    _tab_default = st.session_state.get("pt_selected_tab", _pt_tab_names[0])
    _selected = st.segmented_control(
        "", _pt_tab_names, default=_tab_default,
        key="pt_selected_tab", selection_mode="single", label_visibility="collapsed",
    )
    _active_idx = _pt_tab_names.index(_selected) if _selected in _pt_tab_names else 0
    if 0 <= _active_idx < len(_pt_renderers):
        _pt_renderers[_active_idx]()

    st.markdown("---")
    st.caption("Sentinel \u2014 Your wellness, monitored with care.")
