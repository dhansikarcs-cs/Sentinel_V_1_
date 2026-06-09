import streamlit as st

try:
    from data_manager_ import save_journal_entry, get_patient_history
except Exception:
    save_journal_entry = get_patient_history = None

try:
    from agent_ import summarize_journal
except Exception:
    summarize_journal = None

try:
    from patient_shared_ import safe
except Exception:
    safe = None


def render_patient_journal(username: str):
    st.markdown("### \U0001f4dd Wellness Journal")
    tab_journal, tab_history = st.tabs(["Write Entry", "Past Entries"])
    with tab_journal:
        with st.form("journal_form"):
            raw_text = st.text_area("How are you feeling right now?", placeholder="Write freely...", height=150)
            col1, col2 = st.columns([3, 1])
            with col2:
                submitted = st.form_submit_button("Save Entry", type="primary", use_container_width=True)
            if submitted and raw_text.strip():
                with st.spinner("Analyzing your entry..."):
                    summary = safe(summarize_journal, "Summary unavailable", raw_text)
                safe(save_journal_entry, None, username, raw_text, summary)
                st.success("Entry saved. Your psychologist can see the summarized insights.")
    with tab_history:
        entries = safe(get_patient_history, [], username)
        if entries:
            for ei, e in enumerate(reversed(entries[-10:])):
                key = f"pt_j_{ei}"
                ts = e["timestamp"][:16]
                if st.button(f"\U0001f4c4 {ts}", key=key, use_container_width=True):
                    st.session_state[key + "_open"] = not st.session_state.get(key + "_open", False)
                if st.session_state.get(key + "_open", False):
                    st.markdown(
                        f"<div style='background:#1a2238;border:1px solid #1e2940;border-radius:8px;padding:12px;margin:2px 0;'>"
                        f"<span style='color:#c0d0e0;font-size:0.8125rem;'>{e['summary']}</span></div>",
                        unsafe_allow_html=True,
                    )
                    st.download_button(
                        "\u2b07 Download",
                        f'"{ts}","{e["summary"]}"\n'.encode("utf-8"),
                        file_name=f"journal_{ei}.csv",
                        key=f"pt_j_dl_{ei}",
                    )
        else:
            st.info("No journal entries yet.")
