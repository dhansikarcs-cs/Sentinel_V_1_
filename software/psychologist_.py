import streamlit as st
import traceback
from datetime import datetime

try:
    from ai_kernel_ import synthesize_clinical_notes, summarize_journal
except Exception:
    synthesize_clinical_notes = summarize_journal = None

try:
    from data_manager_ import save_clinical_note, get_clinical_notes
except Exception:
    save_clinical_note = get_clinical_notes = None

try:
    from patient_profiles_ import get_assigned_patients, get_patient_name
except Exception:
    get_assigned_patients = get_patient_name = None

try:
    from agent_ import (triage_summary, suggest_slots, draft_followup, journal_to_note,
        pre_session_brief, compliance_radar,
        silent_period_watch, relapse_indicators, cross_patient_patterns)
except Exception:
    triage_summary = suggest_slots = draft_followup = journal_to_note = None
    pre_session_brief = compliance_radar = None
    silent_period_watch = relapse_indicators = cross_patient_patterns = None

try:
    from smart_room_ import render_smart_room
except Exception:
    render_smart_room = None

try:
    from booking_ import render_booking_queue, render_booking_calendar
except Exception:
    render_booking_queue = render_booking_calendar = None

try:
    from followup_ import render_psychologist_followup
except Exception:
    render_psychologist_followup = None


try:
    from psych_shared_ import safe as _safe, read_crisis_state as _read_crisis_state
except Exception:
    def _safe(func, default=None, *args, **kwargs):
        try:
            if func is not None:
                return func(*args, **kwargs)
        except Exception:
            pass
        return default if default is not None else {}
    def _read_crisis_state():
        return {}

try:
    from psych_status_ import render_psych_status
except Exception:
    render_psych_status = None

try:
    from activity_feed_ import render_activity_feed
except Exception:
    render_activity_feed = None

try:
    from psych_onboarding_ import render_psych_onboarding
except Exception:
    render_psych_onboarding = None

try:
    from patient_profiles_ import get_onboarding_step
except Exception:
    get_onboarding_step = None

try:
    from dashboard_tour_ import render_dashboard_tour
except Exception:
    render_dashboard_tour = None


@st.fragment
def _ai_card(key: str, text: str):
    st.markdown(f"""<div style="background:#1e2336;border:1px solid #2d2d44;border-radius:10px;padding:14px;margin:8px 0;">
<div style="color:#c49ea4;font-size:0.8125rem;font-weight:600;margin-bottom:6px;">🤖 AI Suggestion</div>
<div style="color:#c0d0e0;font-size:0.8125rem;line-height:1.6;">{text}</div>
</div>""", unsafe_allow_html=True)
    _ac, _ec, _rc = st.columns(3)
    with _ac:
        if st.button("Accept", key=f"{key}_ac", use_container_width=True, type="primary"):
            st.session_state.pop(key, None)
    with _ec:
        if st.button("Edit", key=f"{key}_ed", use_container_width=True):
            st.session_state[f"{key}_edit"] = True
    with _rc:
        if st.button("Reject", key=f"{key}_rj", use_container_width=True):
            st.session_state.pop(key, None)
    if st.session_state.get(f"{key}_edit"):
        _ed = st.text_area("Edit", value=text, key=f"{key}_ea", height=100)
        _e1, _e2 = st.columns(2)
        with _e1:
            if st.button("Save", key=f"{key}_sv", use_container_width=True, type="primary"):
                st.session_state[key] = _ed
                st.session_state[f"{key}_edit"] = False
        with _e2:
            if st.button("Cancel", key=f"{key}_cn", use_container_width=True):
                st.session_state[f"{key}_edit"] = False


@st.fragment
def _booking_agent_panel(username, patients):
    st.markdown("#### \U0001f916 Booking Agent")
    _bpat = st.selectbox("Patient", patients, format_func=lambda p: _safe(get_patient_name, p, p), key="b_pat")
    if st.button("\U0001f916 Analyze & Suggest Slots", key="b_btn", use_container_width=True):
        _sl = suggest_slots(_bpat, username)
        if _sl:
            st.session_state["b_agent"] = _sl
    if st.session_state.get("b_agent"):
        _agent = st.session_state["b_agent"]
        _pri = _agent.get("priority", "low")
        _pri_icon = {"high": "\U0001f534", "medium": "\U0001f7e1", "low": "\U0001f7e2"}.get(_pri, "\u26aa")
        _urg = _agent.get("urgency_score", 0)
        _wl = _agent.get("workload", {}).get("pending_bookings", 0)
        _reason = _agent.get("reasoning", "")
        st.markdown(f"""<div style="background:#1e2336;border:1px solid #2d2d44;border-radius:10px;padding:12px;margin:4px 0;">
<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
<span style="color:#c0d0e0;font-size:0.75rem;">Priority: <strong>{_pri_icon} {_pri.title()}</strong></span>
<span style="color:#5a4a5a;">|</span>
<span style="color:#c0d0e0;font-size:0.75rem;">Urgency: <strong>{_urg}/10</strong></span>
<span style="color:#5a4a5a;">|</span>
<span style="color:#c0d0e0;font-size:0.75rem;">Pending: <strong>{_wl}</strong></span>
</div>
<div style="color:#6a6474;font-size:0.6875rem;margin-top:6px;">{_reason}</div>
</div>""", unsafe_allow_html=True)
        _slots = _agent.get("suggested_slots", [])
        if _slots:
            for i, _s in enumerate(_slots):
                _sc1, _sc2 = st.columns([3, 1])
                with _sc1:
                    st.markdown(f"<div style='color:#c49ea4;font-size:0.8125rem;font-weight:600;padding:4px 0;'>{_s['label']}</div>", unsafe_allow_html=True)
                with _sc2:
                    if st.button("Propose", key=f"b_create_{i}", use_container_width=True, type="primary"):
                        try:
                            from data_manager_ import save_booking
                            save_booking(_bpat, _s["date"], _s["time"], "Therapy Session", "1", "", "AI-suggested booking", status="Proposed", psychologist_username=username)
                            st.success(f"Booking proposed: {_s['label']} — waiting for patient to confirm.")
                            del st.session_state["b_agent"]
                        except Exception as _be:
                            st.error(f"Booking failed: {_be}")


@st.fragment
def _followup_agent_panel(username, patients):
    st.markdown("#### \U0001f916 Follow-Up Agent")
    _fpat = st.selectbox("Patient", patients, format_func=lambda p: _safe(get_patient_name, p, p), key="f_pat")
    if st.button("\U0001f916 Analyze & Draft Tasks", key="f_btn", use_container_width=True):
        _fd = draft_followup(_fpat, username)
        if _fd:
            st.session_state["f_agent"] = _fd
    if st.session_state.get("f_agent"):
        _fagent = st.session_state["f_agent"]
        _reason = _fagent.get("reasoning", "")
        st.markdown(
            f"<div style='color:#6a6474;font-size:0.6875rem;padding:6px 0;'>{_reason}</div>",
            unsafe_allow_html=True,
        )
        _ftasks = _fagent.get("tasks", [])
        if _ftasks:
            for i, _t in enumerate(_ftasks):
                st.markdown(f"""<div style="background:#1e2336;border:1px solid #2d2d44;border-radius:10px;padding:10px;margin:6px 0;">
<div style="color:#c49ea4;font-size:0.8125rem;font-weight:600;">{_t['title']}</div>
<div style="color:#9a92a2;font-size:0.75rem;margin-top:4px;">{_t['description']}</div>
</div>""", unsafe_allow_html=True)
                if st.button(f"\u21b3 Fill Form", key=f"f_fill_{i}", use_container_width=True):
                    st.session_state["fu_ai_patient"] = _fpat
                    st.session_state["fu_ai_title"] = _t["title"]
                    st.session_state["fu_ai_desc"] = _t["description"]
                    st.session_state["f_agent"] = None


@st.fragment
def _psych_crisis_alert(username):
    try:
        from crisis_ import play_alert
    except Exception:
        play_alert = None
    try:
        from data_manager_ import acknowledge_crisis
    except Exception:
        acknowledge_crisis = None
    try:
        from crisis_ import resolve_crisis
    except Exception:
        resolve_crisis = None
    _cs = _read_crisis_state()
    if not _cs.get("active"):
        return
    _patient = _cs.get("patient", "Unknown")
    _triggered_by = _cs.get("triggered_by", "")
    if _triggered_by == "psychologist_self":
        _self_user = _patient[6:] if _patient.startswith("psych:") else ""
        if _self_user == username:
            return
    else:
        try:
            from patient_profiles_ import get_patient_clinic, get_clinic_psychologists
            _clinic = get_patient_clinic(_patient)
            if _clinic:
                _assigned = get_clinic_psychologists(_clinic)
                if username not in _assigned:
                    return
        except Exception:
            pass
    _elapsed = int((datetime.now() - datetime.fromisoformat(_cs["triggered_at"])).total_seconds())
    try:
        from crisis_ import crisis_elapsed_html
    except Exception:
        crisis_elapsed_html = None
    try:
        if _cs.get("acknowledged"):
            _by = _cs.get("acknowledged_by", "clinician")
            _resolved = int((datetime.fromisoformat(_cs["acknowledged_at"]) - datetime.fromisoformat(_cs["triggered_at"])).total_seconds()) if _cs.get("acknowledged_at") else _elapsed
            _tc_msg = " | \U0001f464 Trusted Contact was also on the way" if _cs.get("trustee_acknowledged") else ""
            st.success(f"\u2705 **Crisis Acknowledged by {_by}** \u2014 Resolved in {_resolved}s{_tc_msg}")
            _rc1, _rc2 = st.columns([1, 4])
            with _rc1:
                if st.button("\U0001f5d1 Resolve", key="ps_resolve_ack", use_container_width=True):
                    _safe(resolve_crisis, None, username)
                    st.rerun()
        elif _cs.get("trustee_acknowledged"):
            st.info(f"\U0001f7e1 **Trusted Contact En Route \u2014 {_patient}**")
            if crisis_elapsed_html:
                st.markdown(crisis_elapsed_html(_elapsed), unsafe_allow_html=True)
            _rc1, _rc2 = st.columns([1, 1])
            with _rc1:
                if st.button("\u2713 Acknowledge Crisis", type="primary", key="ps_ack_tc", use_container_width=True):
                    _safe(acknowledge_crisis, None, username)
            with _rc2:
                if st.button("\U0001f5d1 Resolve", key="ps_resolve_tc", use_container_width=True):
                    _safe(resolve_crisis, None, username)
                    st.rerun()
        elif _elapsed >= 60:
            _helpline_msg = f"\U0001f6a8 **CRISIS ESCALATION \u2014 HELPLINE CONTACTED \u2014 {_patient}** \U0001f6a8"
            if _cs.get("trustee_acknowledged"):
                _helpline_msg += " \U0001f464 TC is on the way"
            elif _cs.get("trustee_clicked"):
                _helpline_msg += " \U0001f464 TC notified"
            elif _cs.get("trusted_contact_notified"):
                _helpline_msg += " \U0001f464 TC emailed"
            st.error(_helpline_msg)
            if crisis_elapsed_html:
                st.markdown(crisis_elapsed_html(60, large=True, icon_color="#ff9999", text_color="white", label_color="#889"), unsafe_allow_html=True)
            _rc1, _rc2 = st.columns([1, 1])
            with _rc1:
                if st.button("\u2713 Acknowledge Crisis", type="primary", key="ps_ack_h", use_container_width=True):
                    _safe(acknowledge_crisis, None, username)
            with _rc2:
                if st.button("\U0001f5d1 Resolve", key="ps_resolve_h", use_container_width=True):
                    _safe(resolve_crisis, None, username)
                    st.rerun()
        elif _cs.get("trustee_clicked"):
            st.info(f"\U0001f464 **Trusted Contact Notified \u2014 {_patient}**")
            if crisis_elapsed_html:
                st.markdown(crisis_elapsed_html(_elapsed), unsafe_allow_html=True)
            _rc1, _rc2 = st.columns([1, 1])
            with _rc1:
                if st.button("\u2713 Acknowledge Crisis", type="primary", key="ps_ack_tcn", use_container_width=True):
                    _safe(acknowledge_crisis, None, username)
            with _rc2:
                if st.button("\U0001f5d1 Resolve", key="ps_resolve_tcn", use_container_width=True):
                    _safe(resolve_crisis, None, username)
                    st.rerun()
        elif _elapsed >= 30:
            _tc_status = ""
            if _cs.get("trusted_contact_notified"):
                _tc_status = " \U0001f464 Trusted Contact emailed"
            if _cs.get("trustee_clicked"):
                _tc_status = " \U0001f464 Trusted Contact has been notified"
            if _cs.get("trustee_acknowledged"):
                _tc_status = " \U0001f464 Trusted Contact is on the way"
            st.warning(f"\u26a0\ufe0f **Crisis Alert \u2014 {_patient}**{_tc_status}")
            if crisis_elapsed_html:
                st.markdown(crisis_elapsed_html(_elapsed, large=True, icon_color="#ff9999", text_color="white", label_color="#889"), unsafe_allow_html=True)
            _rc1, _rc2 = st.columns([1, 1])
            with _rc1:
                if st.button("\u2713 Acknowledge Crisis", type="primary", key="ps_ack_30", use_container_width=True):
                    _safe(acknowledge_crisis, None, username)
            with _rc2:
                if st.button("\U0001f5d1 Resolve", key="ps_resolve_30", use_container_width=True):
                    _safe(resolve_crisis, None, username)
                    st.rerun()
        else:
            st.error(f"\U0001f6a8 **Emergency Siren \u2014 {_patient}**")
            if crisis_elapsed_html:
                st.markdown(crisis_elapsed_html(_elapsed, large=True, icon_color="#ff9999", text_color="white", label_color="#889"), unsafe_allow_html=True)
            _rc1, _rc2 = st.columns([1, 1])
            with _rc1:
                if st.button("\u2713 Acknowledge Crisis", type="primary", key="ps_ack_0", use_container_width=True):
                    _safe(acknowledge_crisis, None, username)
            with _rc2:
                if st.button("\U0001f5d1 Resolve", key="ps_resolve_0", use_container_width=True):
                    _safe(resolve_crisis, None, username)
                    st.rerun()
    except Exception:
        st.error(f"Crisis display error.\n{traceback.format_exc()}")


@st.fragment
def _cn_ai_panel(username):
    st.markdown("#### \U0001f916 Journal \u2192 Note")
    pts = _safe(get_assigned_patients, [], username)
    if not pts:
        return
    _cnjpat = st.selectbox("Patient", pts, format_func=lambda p: _safe(get_patient_name, p, p), key="cn_j2n_pat")
    try:
        from data_manager_ import get_patient_history
    except Exception:
        get_patient_history = None
    _cnj = _safe(get_patient_history, [], _cnjpat)
    if not _cnj:
        st.caption("No journal entries yet.")
        return
    _cnj_raw = _cnj[-1].get("raw_content", "")
    _cnj_clinical = _safe(summarize_journal, "Clinical summary unavailable", _cnj_raw, "clinical")
    st.markdown(
        f"<div style='background:linear-gradient(135deg,#1e2336,#1e2a45);border:1px solid #2d2d44;border-radius:10px;padding:14px;margin:8px 0;'>"
        f"<div style='display:flex;align-items:center;gap:6px;margin-bottom:6px;'>"
        f"<span style='color:#6a6474;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.5px;'>"
        f"Latest journal ({_cnj[-1].get('timestamp','')[:10]})</span>"
        f"<span style='background:#2a2040;color:#c49ea4;font-size:0.6rem;padding:1px 6px;border-radius:3px;font-weight:600;'>CLINICAL</span>"
        f"</div>"
        f"<div style='color:#9a92a2;font-size:0.75rem;line-height:1.5;'>{_cnj_clinical[:300]}{'...' if len(_cnj_clinical)>300 else ''}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    if st.button("\U0001f916 Analyze & Draft Clinical Note", key="cn_btn", use_container_width=True, type="primary"):
        _j2n = journal_to_note(_cnjpat, _cnj_raw, _cnj_clinical)
        if _j2n:
            st.session_state["cn_card"] = _j2n
    if st.session_state.get("cn_card"):
        _j2n = st.session_state["cn_card"]
        _cn_txt = _j2n.get("suggestion", "Could not generate note.")
        _themes = _j2n.get("themes", [])
        _matched = _j2n.get("matched_therapies", [])
        if _themes or _matched:
            st.markdown(f"""<div style="background:#1e2336;border:1px solid #2d2d44;border-radius:10px;padding:12px;margin:8px 0;">
<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
<span style="color:#c49ea4;font-size:0.75rem;">Detected: </span>
{''.join(f'<span style="background:#2d2d44;color:#9a92a2;font-size:0.6875rem;padding:2px 8px;border-radius:4px;">{t.title()}</span>' for t in _themes)}
<span style="color:#5a4a5a;margin:0 4px;">|</span>
<span style="color:#c49ea4;font-size:0.75rem;">Suggested: </span>
{''.join(f'<span style="background:#1a1e30;color:#d8b4ba;font-size:0.6875rem;padding:2px 8px;border-radius:4px;">{t.split("(")[0].strip()}</span>' for t in _matched)}
</div>
</div>""", unsafe_allow_html=True)
        st.markdown(f"""<div style="background:#1e2336;border:1px solid #2d2d44;border-radius:10px;padding:14px;margin:8px 0;">
<div style="color:#d8b4ba;font-size:13px;font-weight:600;margin-bottom:6px;">\U0001f916 AI Draft</div>
<div style="color:#c0d0e0;font-size:13px;line-height:1.5;">{_cn_txt}</div>
</div>""", unsafe_allow_html=True)
        _cnc1, _cnc2, _cnc3 = st.columns(3)
        with _cnc1:
            if st.button("Accept \u2192 Editor", key="cn_ac", use_container_width=True, type="primary"):
                st.session_state["cn_draft"] = _cn_txt
                del st.session_state["cn_card"]
        with _cnc2:
            if st.button("Edit", key="cn_ed", use_container_width=True):
                st.session_state["cn_editing"] = True
        with _cnc3:
            if st.button("Reject", key="cn_rj", use_container_width=True):
                del st.session_state["cn_card"]
        if st.session_state.get("cn_editing"):
            _cn_ed = st.text_area("Edit", value=_cn_txt, key="cn_ea", height=100)
            _cne1, _cne2 = st.columns(2)
            with _cne1:
                if st.button("Save", key="cn_sv", use_container_width=True, type="primary"):
                    st.session_state["cn_card"] = _j2n
                    st.session_state["cn_editing"] = False
            with _cne2:
                if st.button("Cancel", key="cn_cn", use_container_width=True):
                    st.session_state["cn_editing"] = False


def render_psychologist_portal():
    username = st.session_state.username
    doc_name = st.session_state.get("psychologist_name", username)

    # ── Profile settings (triggered from sidebar) ──
    if st.session_state.get("show_profile", False):
        try:
            from profile_ import render_profile
            render_profile(username)
        except Exception:
            st.error("Profile settings unavailable.")
        return

    # ── Onboarding wizard for first-time psychologists ──
    _psych_db_step = _safe(get_onboarding_step, 0, username)
    st.session_state["_psych_onboarding"] = _psych_db_step < 99
    if _psych_db_step < 99:
        try:
            if render_psych_onboarding:
                render_psych_onboarding(username)
        except Exception:
            pass
        return

    _poll_cs = _read_crisis_state()
    _interval = 5000 if _poll_cs.get("active") else 300000
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=_interval, key="psych_crisis_poll")
    except Exception:
        pass

    try:
        from crisis_ import handle_escalation, play_alert
    except Exception:
        handle_escalation = play_alert = None
    if handle_escalation:
        _safe(handle_escalation)

    _crisis_ts = _poll_cs.get("triggered_at", "")
    _last_alerted = st.session_state.get("crisis_alert_ts", "")
    if _poll_cs.get("active") and _crisis_ts != _last_alerted:
        _safe(play_alert)
        st.session_state.crisis_alert_ts = _crisis_ts
    elif not _poll_cs.get("active") and _last_alerted:
        st.session_state.pop("crisis_alert_ts", None)

    _psych_crisis_alert(username)

    # ── AI Triage ──
    try:
        if _poll_cs.get("active") and not _poll_cs.get("acknowledged"):
            if st.button("🤖 AI Triage Summary", key="triage_btn", use_container_width=True):
                _tr = triage_summary(_poll_cs["patient"])
                if _tr and _tr.get("suggestion"):
                    _p = _tr.get("priority", "")
                    _c = {"high": "🚨", "medium": "⚠️", "low": "ℹ️"}.get(_p, "🤖")
                    st.info(f"{_c} **AI Triage**: {_tr['suggestion']}")
    except Exception:
        pass

    # ── AGENT SIDEBAR (removed — moved to main sidebar)
    # ── End of agent sidebar ──
    st.markdown("---")

    # ── Today's Overview ──
    try:
        render_psych_status(username)
    except Exception:
        pass

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

    # ── Tab content helpers ──

    def _render_triage_tab():
        try:
            from psych_triage_ import render_psych_triage
            render_psych_triage(username)
        except Exception as e:
            st.error(f"Patient triage unavailable:\n{traceback.format_exc()}")

    def _render_clinical_notes_tab():
        try:
            st.markdown("### Clinical Documentation")
            _cncol1, _cncol2 = st.columns([2, 1])
            with _cncol1:
                st.markdown("#### New Session Note")
                pts = _safe(get_assigned_patients, [], username)
                if pts:
                    sel = st.selectbox("Patient", pts, format_func=lambda p: _safe(get_patient_name, p, p), key="cn_pat")
                    with st.form("clinical_note_form"):
                        raw_notes = st.text_area("Session Observations (write your own notes)", value=st.session_state.get("cn_draft", ""), placeholder="Enter your session notes...", height=200)
                        if st.form_submit_button("Generate & Save Note", type="primary", use_container_width=True):
                            if raw_notes.strip():
                                with st.spinner("Synthesizing clinical note..."):
                                    synthesis = synthesize_clinical_notes(raw_notes) or "Synthesis unavailable"
                                save_clinical_note(username, sel, raw_notes, synthesis)
                                st.session_state["cn_draft"] = ""
                                st.success("Clinical note saved.")
            with _cncol2:
                _cn_ai_panel(username)
        except Exception as e:
            st.error(f"Clinical notes section unavailable:\n{traceback.format_exc()}")

        try:
            st.markdown("#### Saved Notes")
            notes = _safe(get_clinical_notes, [], username)
            if notes:
                for ni, n in enumerate(reversed(notes[-10:])):
                    with st.expander(f"{n['patient']} \u2014 {n['timestamp']}"):
                        st.markdown(f"**Patient**: {_safe(get_patient_name, n['patient'], n['patient'])}")
                        st.markdown(n["ai_synthesis"])
            else:
                st.info("No notes yet.")
        except Exception as e:
            st.error(f"Saved notes unavailable:\n{traceback.format_exc()}")

    def _render_journal_wellness_tab():
        try:
            from psych_journal_ import render_psych_journal
            render_psych_journal(username)
        except Exception as e:
            st.error(f"Journal & Wellness tab unavailable:\n{traceback.format_exc()}")

    def _render_bookings_tab():
        try:
            _bpats = _safe(get_assigned_patients, [], username)
            _bcol1, _bcol2 = st.columns([3, 1])
            with _bcol1:
                cal_tab, queue_tab = st.tabs(["\U0001f4c5 Calendar", "\U0001f4cb Queue"])
                with cal_tab:
                    render_booking_calendar(username)
                with queue_tab:
                    render_booking_queue(username)
            with _bcol2:
                _booking_agent_panel(username, _bpats)
        except Exception as e:
            st.error(f"Bookings unavailable:\n{traceback.format_exc()}")

    def _render_followup_tab():
        try:
            _fupats = _safe(get_assigned_patients, [], username)
            _fcol1, _fcol2 = st.columns([3, 1])
            with _fcol1:
                render_psychologist_followup(username)
            with _fcol2:
                _followup_agent_panel(username, _fupats)
        except Exception as e:
            st.error(f"Follow-Up unavailable:\n{traceback.format_exc()}")

    def _render_smart_room_tab():
        try:
            head_col1, head_col2 = st.columns([3, 1])
            with head_col1:
                st.markdown("### \U0001f9e0 Smart Room")
            with head_col2:
                if st.button("\u26a1 Intense" if st.session_state.get("psych_room_intense", False) else "\U0001f319 Calm", key="psych_room_toggle", use_container_width=True):
                    st.session_state.psych_room_intense = not st.session_state.psych_room_intense
            room_mode = "intense" if st.session_state.get("psych_room_intense", False) else "calm"
            render_smart_room(room_mode, 2.0 if room_mode=="intense" else 1.0)
        except Exception as e:
            st.error(f"Smart Room unavailable:\n{traceback.format_exc()}")

    def _render_export_tab():
        try:
            from psych_export_ import render_psych_export
            render_psych_export(username)
        except Exception as e:
            st.error(f"Export Center unavailable:\n{traceback.format_exc()}")

    # ── Tab selector (segmented control works with tour) ──
    _psych_tab_names = ["\U0001f4cb Patient Triage", "\U0001f4dd Clinical Notes", "\U0001f4d3 Journal & Wellness", "\U0001f4c5 Bookings", "\U0001f4cb Follow-Up", "\U0001f9e0 Smart Room", "\U0001f4e6 Export Center"]
    _psych_renderers = [_render_triage_tab, _render_clinical_notes_tab, _render_journal_wellness_tab, _render_bookings_tab, _render_followup_tab, _render_smart_room_tab, _render_export_tab]

    _tour_tab = render_dashboard_tour("Psychologist") if render_dashboard_tour else ""
    if _tour_tab:
        st.session_state["psych_selected_tab"] = _tour_tab

    _tab_default = st.session_state.get("psych_selected_tab", _psych_tab_names[0])
    _selected = st.segmented_control(
        "", _psych_tab_names, default=_tab_default,
        key="psych_selected_tab", selection_mode="single", label_visibility="collapsed",
    )
    _active_idx = _psych_tab_names.index(_selected) if _selected in _psych_tab_names else 0
    if 0 <= _active_idx < len(_psych_renderers):
        _psych_renderers[_active_idx]()

    st.markdown("---")
    st.caption("Sentinel \u2014 Clinician Portal")
