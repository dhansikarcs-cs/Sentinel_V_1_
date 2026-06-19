import streamlit as st
import traceback

try:
    from data_manager_ import get_all_patient_summaries, get_clinical_notes, get_patient_history
except Exception:
    get_all_patient_summaries = get_clinical_notes = get_patient_history = None

try:
    from patient_profiles_ import get_patient_name, get_assigned_patients
except Exception:
    get_patient_name = get_assigned_patients = None


def _safe(func, default=None, *args, **kwargs):
    try:
        if func is not None:
            return func(*args, **kwargs)
    except Exception as e:
        import sys; print(f"[_safe] {func.__name__ if func else 'None'}: {e}", file=sys.stderr)
    return default if default is not None else {}


_CARD = "background:#1a2238;border:1px solid #1e2940;border-radius:8px;padding:12px;margin:2px 0;"


def render_psych_export(username: str):
    st.markdown("### \U0001f4e6 Export Center")
    export_type = st.radio("Export Type", ["Patients", "Myself"], horizontal=True)
    try:
        if export_type == "Patients":
            _patients_export(username)
        else:
            _self_export(username)
    except Exception as e:
        st.error(f"Export Center unavailable:\n{traceback.format_exc()}")


def _patients_export(username: str):
    summaries = _safe(get_all_patient_summaries, {})
    notes = _safe(get_clinical_notes, [], username)
    patient_usernames = _safe(get_assigned_patients, [], username)
    has_data = any(p in summaries for p in patient_usernames)
    if not has_data:
        st.info("No patient data available.")
        return
    st.markdown("#### Select a patient")
    valid_pats = [p for p in patient_usernames if p in summaries]
    if not valid_pats:
        st.info("No data for registered patients.")
        return
    cols = st.columns(len(valid_pats))
    sel_pat = None
    for ci, p in enumerate(valid_pats):
        if cols[ci].button(_safe(get_patient_name, p, p), key=f"exp_pat_{p}", use_container_width=True):
            sel_pat = p
    if sel_pat is None and "exp_sel_pat" in st.session_state:
        sel_pat = st.session_state.exp_sel_pat
    if not sel_pat:
        return
    st.session_state.exp_sel_pat = sel_pat
    st.markdown(f"#### {_safe(get_patient_name, sel_pat, sel_pat)}")
    st.markdown("**Journal Entries**")
    entries = summaries[sel_pat]
    for ei, e in enumerate(entries):
        key = f"exp_j_{sel_pat}_{ei}"
        ts = e["timestamp"][:16]
        if st.button(f"\U0001f4c4 {ts}", key=key, use_container_width=True):
            st.session_state[key + "_open"] = not st.session_state.get(key + "_open", False)
        if st.session_state.get(key + "_open", False):
            st.markdown(
                f"<div style='{_CARD}'><span style='color:#c0d0e0;font-size:0.8125rem;'>{e['summary']}</span></div>",
                unsafe_allow_html=True,
            )
            st.download_button(
                "\u2b07 Download",
                f'"{ts}","{e["summary"]}"\n'.encode("utf-8"),
                file_name=f"{sel_pat}_journal_{ei}.csv",
                key=f"exp_j_dl_{sel_pat}_{ei}",
            )
    clin_notes = [n for n in notes if n["patient"] == sel_pat]
    if clin_notes:
        st.markdown("**Clinical Notes**")
        for ni, n in enumerate(clin_notes):
            key = f"exp_c_{sel_pat}_{ni}"
            ts = n["timestamp"][:16]
            if st.button(f"\U0001f4c4 {ts}", key=key, use_container_width=True):
                st.session_state[key + "_open"] = not st.session_state.get(key + "_open", False)
            if st.session_state.get(key + "_open", False):
                st.markdown(
                    f"<div style='{_CARD}'><span style='color:#c0d0e0;font-size:0.8125rem;'>{n['ai_synthesis']}</span></div>",
                    unsafe_allow_html=True,
                )
                st.download_button(
                    "\u2b07 Download",
                    f'"{ts}","{n["ai_synthesis"]}"\n'.encode("utf-8"),
                    file_name=f"{sel_pat}_clinical_{ni}.csv",
                    key=f"exp_c_dl_{sel_pat}_{ni}",
                )


def _self_export(username: str):
    journal = _safe(get_patient_history, [], username)
    if not journal:
        st.info("No journal entries yet.")
        return
    for ji, e in enumerate(reversed(journal)):
        key = f"exp_jrnl_{ji}"
        ts = e["timestamp"][:16]
        if st.button(f"\U0001f4c4 {ts}", key=key, use_container_width=True):
            st.session_state[key + "_open"] = not st.session_state.get(key + "_open", False)
        if st.session_state.get(key + "_open", False):
            st.markdown(
                f"<div style='{_CARD}'><span style='color:#c0d0e0;font-size:0.8125rem;'>{e['summary']}</span></div>",
                unsafe_allow_html=True,
            )
            st.download_button(
                "\u2b07 Download",
                f'"{ts}","{e["summary"]}"\n'.encode("utf-8"),
                file_name=f"journal_{ji}.csv",
                key=f"exp_jrnl_dl_{ji}",
            )
