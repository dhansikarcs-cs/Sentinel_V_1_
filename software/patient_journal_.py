import streamlit as st

try:
    from data_manager_ import save_journal_entry, get_patient_history, save_mood, get_today_mood
except Exception:
    save_journal_entry = get_patient_history = save_mood = get_today_mood = None

try:
    from ai_kernel_ import summarize_journal
except Exception:
    summarize_journal = None

try:
    from patient_shared_ import safe
except Exception:
    safe = None

MOODS = [
    ("\U0001f622", "Sad"),
    ("\U0001f641", "Down"),
    ("\U0001f610", "Okay"),
    ("\U0001f642", "Good"),
    ("\U0001f601", "Great"),
]


def render_patient_journal(username: str):
    st.markdown("""
    <div style="margin-bottom:20px;">
        <div style="font-size:1.35rem;font-weight:700;color:#e0e8f0;">&#x1f4dd; Wellness Journal</div>
        <div style="color:#7a8aaa;font-size:0.8rem;margin-top:2px;">Write freely — your psychologist sees only the AI summary</div>
    </div>
    """, unsafe_allow_html=True)

    tab_journal, tab_history = st.tabs(["✍️ Write Entry", "📖 Past Entries"])

    with tab_journal:
        today_mood = safe(get_today_mood, None, username)
        mood_locked = today_mood is not None

        st.markdown(
            "<div style='color:#7a8aaa;font-size:0.75rem;margin-bottom:6px;'>How are you feeling?</div>",
            unsafe_allow_html=True,
        )

        if mood_locked:
            st.markdown(
                f"<div style='text-align:center;font-size:1.5rem;padding:4px 0 8px;'>"
                f"{today_mood['emoji']} <span style='color:#9aa8c0;font-size:0.85rem;'>{today_mood['label']}</span>"
                f"<span style='color:#5a6a8a;font-size:0.65rem;margin-left:8px;'>locked for today</span></div>",
                unsafe_allow_html=True,
            )
        else:
            cols = st.columns(len(MOODS))
            for i, (emoji, label) in enumerate(MOODS):
                with cols[i]:
                    if st.button(emoji, key=f"mood_{i}", help=label, use_container_width=True):
                        safe(save_mood, None, username, emoji, label)
                        st.rerun()

        with st.form("journal_form", clear_on_submit=True):
            raw_text = st.text_area(
                "",
                placeholder="What's on your mind? Write freely...",
                height=200,
                label_visibility="collapsed",
            )

            meta_cols = st.columns([1, 1, 2])
            with meta_cols[0]:
                word_count = len(raw_text.split()) if raw_text.strip() else 0
                st.markdown(
                    f"<span style='color:#5a6a8a;font-size:0.7rem;'>{word_count} words</span>",
                    unsafe_allow_html=True,
                )
            with meta_cols[1]:
                char_count = len(raw_text)
                st.markdown(
                    f"<span style='color:#5a6a8a;font-size:0.7rem;'>{char_count} characters</span>",
                    unsafe_allow_html=True,
                )
            with meta_cols[2]:
                submitted = st.form_submit_button("💾 Save Entry", type="primary", use_container_width=True)

        if submitted:
            if raw_text.strip():
                with st.spinner("Analyzing your entry..."):
                    summary = safe(summarize_journal, "Summary unavailable", raw_text)
                safe(save_journal_entry, None, username, raw_text, summary)
                st.success("Entry saved. Check Past Entries to read the AI summary.")
            else:
                st.warning("Write something before saving.")

    with tab_history:
        entries = safe(get_patient_history, [], username)
        if entries:
            st.markdown(
                f"<div style='color:#7a8aaa;font-size:0.75rem;margin-bottom:8px;'>Showing last {min(20, len(entries))} entries</div>",
                unsafe_allow_html=True,
            )
            for ei, e in enumerate(reversed(entries[-20:])):
                key = f"pt_j_{ei}"
                ts = e["timestamp"][:16]
                summary_text = e.get("summary", "") or "No summary"
                is_open = st.session_state.get(key + "_open", False)
                emoji = "\U0001f4c4"

                if st.button(
                    f"{emoji} {ts}",
                    key=key,
                    use_container_width=True,
                    help="Click to expand",
                ):
                    st.session_state[key + "_open"] = not is_open

                if st.session_state.get(key + "_open", False):
                    with st.container():
                        st.markdown(
                            f"<div style='background:linear-gradient(135deg,#1a2238,#1e2a45);border:1px solid #1e3a5a;border-radius:10px;padding:16px;margin:2px 0 8px 0;'>"
                            f"<div style='color:#9aa8c0;font-size:0.8125rem;line-height:1.5;'>{summary_text}</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                        action_cols = st.columns([1, 1, 2])
                        with action_cols[0]:
                            if summary_text in ("Summary unavailable", "", "No summary") and summarize_journal:
                                if st.button("\U0001f504 Re-summarize", key=f"pt_j_rs_{ei}"):
                                    with st.spinner("Re-analyzing..."):
                                        new_summary = summarize_journal(e.get("raw_content", ""))
                                    if new_summary:
                                        from data_manager_ import _ensure_migrated
                                        from database import get_db
                                        _ensure_migrated()
                                        with get_db() as db:
                                            db.execute(
                                                "UPDATE journal_entries SET summary = ? WHERE patient_username = ? AND timestamp = ?",
                                                (new_summary, username, e["timestamp"])
                                            )
                                        st.success("Re-summarized!")
                        with action_cols[1]:
                            st.download_button(
                                "\u2b07 Download",
                                f'"{ts}","{summary_text}"\n'.encode("utf-8"),
                                file_name=f"journal_{ei}.csv",
                                key=f"pt_j_dl_{ei}",
                            )
        else:
            st.info("\U0001f4ac No journal entries yet. Write your first entry above.")
