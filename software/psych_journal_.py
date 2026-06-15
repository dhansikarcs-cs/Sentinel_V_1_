import streamlit as st

try:
    from data_manager_ import save_journal_entry, get_patient_history
except Exception:
    save_journal_entry = get_patient_history = None

try:
    from ai_kernel_ import summarize_journal
except Exception:
    summarize_journal = None

try:
    from patient_shared_ import safe
except Exception:
    safe = None


def render_psych_journal(username: str):
    st.markdown("""
    <div style="margin-bottom:20px;">
        <div style="font-size:1.35rem;font-weight:700;color:#e0e8f0;">&#x1f4d3; My Journal</div>
        <div style="color:#7a8aaa;font-size:0.8rem;margin-top:2px;">Personal reflections & session notes</div>
    </div>
    """, unsafe_allow_html=True)

    tab_write, tab_view = st.tabs(["✍️ Write Entry", "📖 History"])

    with tab_write:
        with st.form("psych_journal_form"):
            raw_text = st.text_area(
                "",
                placeholder="Write freely about your day, thoughts, or sessions...",
                height=220,
                label_visibility="collapsed",
            )

            meta_cols = st.columns([1, 1, 2])
            with meta_cols[0]:
                wc = len(raw_text.split()) if raw_text.strip() else 0
                st.markdown(
                    f"<span style='color:#5a6a8a;font-size:0.7rem;'>{wc} words</span>",
                    unsafe_allow_html=True,
                )
            with meta_cols[1]:
                cc = len(raw_text)
                st.markdown(
                    f"<span style='color:#5a6a8a;font-size:0.7rem;'>{cc} characters</span>",
                    unsafe_allow_html=True,
                )
            with meta_cols[2]:
                submitted = st.form_submit_button("💾 Save Entry", type="primary", use_container_width=True)

        if submitted:
            if raw_text.strip():
                with st.spinner("Reflecting..."):
                    summary = safe(summarize_journal, "Summary unavailable", raw_text)
                safe(save_journal_entry, None, username, raw_text, summary)
                st.success("Journal entry saved.")
                st.rerun()
            else:
                st.warning("Write something before saving.")

    with tab_view:
        entries = safe(get_patient_history, [], username)
        if entries:
            st.markdown(
                f"<div style='color:#7a8aaa;font-size:0.75rem;margin-bottom:8px;'>Showing last {min(20, len(entries))} entries</div>",
                unsafe_allow_html=True,
            )
            for ei, e in enumerate(reversed(entries[-20:])):
                key = f"doc_j_{ei}"
                ts = e["timestamp"][:16]
                btn_label = f"\U0001f4c4 {ts}"

                if st.button(btn_label, key=key, use_container_width=True):
                    st.session_state[key + "_open"] = not st.session_state.get(key + "_open", False)

                if st.session_state.get(key + "_open", False):
                    with st.container():
                        st.markdown(
                            f"<div style='background:linear-gradient(135deg,#1a2238,#1e2a45);border:1px solid #1e3a5a;border-radius:10px;padding:16px;margin:2px 0 8px 0;'>"
                            f"<div style='color:#5a6a8a;font-size:0.7rem;margin-bottom:6px;'>{ts}</div>"
                            f"<div style='color:#9aa8c0;font-size:0.8125rem;line-height:1.5;'>{e['summary']}</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                        st.download_button(
                            "\u2b07 Download",
                            f'"{ts}","{e["summary"]}"\n'.encode("utf-8"),
                            file_name=f"journal_{ei}.csv",
                            key=f"doc_j_dl_{ei}",
                        )
        else:
            st.info("\U0001f4ac No journal entries yet.")
