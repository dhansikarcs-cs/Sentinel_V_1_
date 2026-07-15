import streamlit as st

try:
    from data_manager_ import save_journal_entry, get_patient_history, save_mood, get_today_mood, get_mood_history
except Exception:
    save_journal_entry = get_patient_history = save_mood = get_today_mood = get_mood_history = None

try:
    import plotly.graph_objects as go
except Exception:
    go = None

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

MOOD_SCORE = {"Sad": 1, "Down": 2, "Okay": 3, "Good": 4, "Great": 5}
MOOD_COLORS = {"Sad": "#ef4444", "Down": "#f59e0b", "Okay": "#eab308", "Good": "#22c55e", "Great": "#16a34a"}
MOOD_EMOJI_MAP = {e: l for e, l in MOODS}
MOOD_LABEL_EMOJI = dict(MOODS)


def _mood_card(today_mood: dict | None, username: str):
    if today_mood:
        emoji = today_mood["emoji"]
        label = today_mood["label"]
        color = MOOD_COLORS.get(label, "#888")
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#1a2844,#1e2a45);border:2px solid {color}44;border-radius:16px;padding:20px;text-align:center;margin-bottom:16px;">
            <div style="font-size:3.5rem;line-height:1.2;">{emoji}</div>
            <div style="color:{color};font-size:1.3rem;font-weight:700;margin-top:2px;">{label}</div>
            <div style="color:#5a6a8a;font-size:0.7rem;margin-top:4px;">Today's mood — locked</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#1a2844,#1e2a45);border:2px dashed #2a3a5a;border-radius:16px;padding:20px;text-align:center;margin-bottom:16px;">
            <div style="font-size:2.5rem;line-height:1.2;opacity:0.6;">\U0001f3a8</div>
            <div style="color:#5a6a8a;font-size:0.85rem;margin-top:4px;">Tap an emoji to log your mood</div>
        </div>
        """, unsafe_allow_html=True)
        cols = st.columns(len(MOODS))
        for i, (emoji, label) in enumerate(MOODS):
            with cols[i]:
                if st.button(emoji, key=f"mood_{i}", help=label, use_container_width=True):
                    safe(save_mood, None, username, emoji, label)
                    st.rerun()


def _mood_chart(username: str):
    _mood_history = safe(get_mood_history, [], username, 14)
    if _mood_history and go is not None:
        _mh = sorted(_mood_history, key=lambda x: x["date"])
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[m["date"][-5:] for m in _mh],
            y=[MOOD_SCORE.get(m["label"], 3) for m in _mh],
            mode="lines+markers",
            marker=dict(size=10, color=[MOOD_COLORS.get(m["label"], "#888") for m in _mh], line=dict(width=1.5, color="#fff")),
            line=dict(color="#c06a8b88", width=2.5, shape="spline"),
            fill="tozeroy", fillcolor="rgba(192,106,139,0.08)",
            hovertemplate="%{x}<br>%{text}<extra></extra>",
            text=[m["label"] for m in _mh],
        ))
        fig.update_layout(
            margin=dict(l=0, r=0, t=4, b=0), height=140,
            showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(visible=False), yaxis=dict(visible=False, range=[0.5, 5.5]),
            hovermode="x unified", dragmode=False,
        )
        st.markdown(f"<div style='color:#5a6a8a;font-size:0.7rem;margin:4px 0 0 0;'>Mood trend — last 14 days</div>", unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "displaylogo": False})


def render_patient_journal(username: str):
    st.markdown("""
    <div style="margin-bottom:8px;">
        <div style="font-size:1.35rem;font-weight:700;color:#e0e8f0;">&#x1f4dd; Wellness Journal</div>
        <div style="color:#7a8aaa;font-size:0.8rem;margin-top:2px;">Write freely — your psychologist sees only the AI summary</div>
    </div>
    """, unsafe_allow_html=True)

    today_mood = safe(get_today_mood, None, username)
    _mood_card(today_mood, username)

    tab_journal, tab_history = st.tabs(["✍️ Write Entry", "📖 Past Entries"])

    with tab_journal:
        _mood_chart(username)

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
                st.markdown(f"<span style='color:#5a6a8a;font-size:0.7rem;'>{word_count} words</span>", unsafe_allow_html=True)
            with meta_cols[1]:
                char_count = len(raw_text)
                st.markdown(f"<span style='color:#5a6a8a;font-size:0.7rem;'>{char_count} characters</span>", unsafe_allow_html=True)
            with meta_cols[2]:
                submitted = st.form_submit_button("💾 Save Entry", type="primary", use_container_width=True)

        if submitted:
            if raw_text.strip():
                with st.spinner("Analyzing your entry..."):
                    _result = safe(summarize_journal, {"text": "Summary unavailable", "source": "", "emotions": ""}, raw_text)
                summary_text = _result.get("text", "Summary unavailable") if isinstance(_result, dict) else "Summary unavailable"
                ai_source = _result.get("source", "") if isinstance(_result, dict) else ""
                emotions = _result.get("emotions", "") if isinstance(_result, dict) else ""
                safe(save_journal_entry, None, username, raw_text, summary_text, ai_source, emotions)
                if emotions:
                    st.markdown(
                        f"<div style='color:#9aa8c0;font-size:0.75rem;margin-bottom:4px;'>Detected emotions: {emotions}</div>",
                        unsafe_allow_html=True,
                    )
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
                _emotions = e.get("emotions", "") or ""
                _ai_source = e.get("ai_source", "") or ""
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
                        _badges = ""
                        if _ai_source:
                            _sc = {"ollama": "#c49ea4", "groq": "#22c55e", "rule": "#f59e0b"}.get(_ai_source, "#888")
                            _badges += f"<span style='background:{_sc}22;color:{_sc};font-size:0.6rem;padding:1px 6px;border-radius:3px;font-weight:600;border:1px solid {_sc}44;margin-right:6px;'>{_ai_source.title()}</span>"
                        if _emotions:
                            _badges += f"<span style='color:#9aa8c0;font-size:0.65rem;'>Emotions: {_emotions}</span>"
                        _badges_html = '<div style="margin-bottom:6px;">' + _badges + '</div>' if _badges else ''
                        st.markdown(
                            f"<div style='background:linear-gradient(135deg,#1a2238,#1e2a45);border:1px solid #1e3a5a;border-radius:10px;padding:16px;margin:2px 0 8px 0;'>"
                            f"{_badges_html}"
                            f"<div style='color:#9aa8c0;font-size:0.8125rem;line-height:1.5;'>{summary_text}</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                        action_cols = st.columns([1, 1, 2])
                        with action_cols[0]:
                            if summary_text in ("Summary unavailable", "", "No summary") and summarize_journal:
                                if st.button("\U0001f504 Re-summarize", key=f"pt_j_rs_{ei}"):
                                    with st.spinner("Re-analyzing..."):
                                        _new = summarize_journal(e.get("raw_content", ""))
                                        new_summary = _new.get("text", "") if isinstance(_new, dict) else ""
                                    if new_summary:
                                        from data_manager_ import _ensure_migrated
                                        from database import get_db
                                        _ensure_migrated()
                                        with get_db() as db:
                                            db.execute(
                                                "UPDATE journal_entries SET summary = ?, ai_source = ?, emotions = ? WHERE patient_username = ? AND timestamp = ?",
                                                (new_summary, _new.get("source", "") if isinstance(_new, dict) else "", _new.get("emotions", "") if isinstance(_new, dict) else "", username, e["timestamp"])
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
