import streamlit as st
import pandas as pd

try:
    from ring_ import get_ring_data, get_seeded_history
except Exception:
    get_ring_data = get_seeded_history = None

try:
    from agent_ import patient_insights, mood_trend, relapse_indicators
except Exception:
    patient_insights = mood_trend = relapse_indicators = None

try:
    from patient_shared_ import safe, metric_card, trend_chart
except Exception:
    safe = metric_card = trend_chart = None


def render_patient_wellness(username: str):
    st.markdown("### \U0001f4ca Wellness Dashboard")
    ring = safe(get_ring_data, {"bpm":72,"stress":35,"sleep":7,"spo2":98,"mood":"neutral"}, username, 1.0)
    cols = st.columns(5)
    metrics = [
        ("Heart Rate", f"{ring['bpm']}", "bpm", "#ff6b6b"),
        ("Stress", f"{ring['stress']}", "%", "#ffd93d"),
        ("Sleep", f"{ring['sleep']}", "hrs", "#6bcbff"),
        ("SpO\u2082", f"{ring['spo2']}", "%", "#6bffb8"),
        ("Mood", ring["mood"].title(), "", "#c97bff"),
    ]
    for col, (label, val, unit, color) in zip(cols, metrics):
        with col:
            metric_card(label, val, unit, color)

    view_toggle = st.toggle("Show as table", key="wellness_view")
    if view_toggle:
        st.markdown("#### 24h Trends \u2014 Table View")
        all_data = {}
        for m, lbl, _ in [("bpm", "Heart Rate", "#ff6b6b"), ("stress", "Stress", "#ffd93d"), ("sleep", "Sleep", "#6bcbff"), ("spo2", "SpO\u2082", "#6bffb8")]:
            all_data[lbl] = safe(get_seeded_history, [], username, m, 24)
        st.dataframe(pd.DataFrame(all_data), height=180, use_container_width=True)
    else:
        hcols = st.columns([10, 1])
        with hcols[0]:
            st.markdown("#### 24h Trends")
        with hcols[1]:
            if st.button("\u21ba", key="reset_trends_patient", help="Reset chart zoom"):
                pass
        trend_cols = st.columns(4)
        trends = [("bpm", "Heart Rate", "#ff6b6b"), ("stress", "Stress", "#ffd93d"), ("sleep", "Sleep", "#6bcbff"), ("spo2", "SpO\u2082", "#6bffb8")]
        for col, (metric, label, color) in zip(trend_cols, trends):
            with col:
                st.markdown(f"**{label}**")
                trend_chart(username, metric, label, color)

    with st.expander("\U0001f4ca My Insights (AI-Powered)"):
        _ins = safe(patient_insights, {}, username)
        if _ins:
            _ic1, _ic2, _ic3 = st.columns(3)
            with _ic1:
                st.metric("\U0001f4dd Journals (7d)", _ins.get("journal_count", 0))
            with _ic2:
                st.metric("\u2705 Compliance", f"{_ins.get('compliance', 0):.0f}%")
            with _ic3:
                st.metric("\u274c Missed", _ins.get("missed", 0))
            g = _ins.get("grades", {})
            if g.get("green") or g.get("yellow") or g.get("red"):
                st.caption(f"Grades: \U0001f7e2{g['green']}  \U0001f7e1{g['yellow']}  \U0001f534{g['red']}")
            _mt = safe(mood_trend, {}, username)
            if _mt and _mt.get("message"):
                st.markdown(_mt["message"])
            _ri = safe(relapse_indicators, {}, username)
            if _ri and _ri.get("flag"):
                st.warning(_ri["message"])
        else:
            st.caption("Keep journaling! Insights will appear as you build more entries.")
