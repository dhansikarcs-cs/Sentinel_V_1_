import streamlit as st
import plotly.graph_objects as go
import pandas as pd

try:
    from ring_ import get_ring_data, get_seeded_history
except Exception:
    get_ring_data = get_seeded_history = None

try:
    from ai_kernel_ import summarize_journal
except Exception:
    summarize_journal = None

try:
    from data_manager_ import save_journal_entry, get_patient_history
except Exception:
    save_journal_entry = get_patient_history = None

try:
    from psych_shared_ import safe, psych_metric, mini_chart
except Exception:
    safe = psych_metric = mini_chart = None


def _hex_to_rgba(hex_color: str, alpha: float = 0.6) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _gauge_fig(value: float, title: str, bar_color: str, suffix: str = "",
               low: float = 40, high: float = 120) -> go.Figure:
    steps = [
        {"range": [low, (low + high) / 2], "color": "#0a1510"},
        {"range": [(low + high) / 2, high], "color": "#131b2e"},
    ]
    if title == "SpO\u2082":
        steps = [
            {"range": [90, 95], "color": "#150808"},
            {"range": [95, 100], "color": "#0a1510"},
        ]
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value,
        number={"font": {"color": bar_color, "size": 28}, "suffix": suffix},
        gauge={
            "axis": {"range": [low, high], "visible": False},
            "bar": {"color": _hex_to_rgba(bar_color), "thickness": 0.3},
            "bgcolor": "#161d30", "borderwidth": 0,
            "steps": steps,
            "threshold": {"line": {"color": "rgba(255,255,255,0.3)", "width": 1}, "thickness": 0.5, "value": value},
        },
        domain={"x": [0, 1], "y": [0, 0.9]},
    ))
    fig.update_layout(
        height=140, margin=dict(l=10, r=10, t=15, b=0),
        paper_bgcolor="rgba(0,0,0,0)", font={"color": "#7a8aaa"},
        title={"text": title, "font": {"color": "#4a5a7a", "size": 12}, "x": 0.5},
    )
    return fig


def render_psych_journal(username: str):
    try:
        ring = safe(get_ring_data, {"bpm":72,"stress":35,"sleep":7,"spo2":98,"mood":"neutral"}, username + "_doc", 1.0)
        col_gauge, col_chart = st.columns([1, 2])
        with col_gauge:
            st.plotly_chart(
                _gauge_fig(ring["bpm"], "BPM", "#ff6b6b", low=40, high=120),
                use_container_width=True, config={"displayModeBar": False},
            )
            st.plotly_chart(
                _gauge_fig(ring["spo2"], "SpO\u2082", "#6bffb8", suffix="%", low=90, high=100),
                use_container_width=True, config={"displayModeBar": False},
            )
        with col_chart:
            if st.toggle("Show as table", key="trend_table"):
                days = 7 * 24
                hr_vals = safe(get_seeded_history, [], username + "_doc", "bpm", days)
                stress_vals = safe(get_seeded_history, [], username + "_doc", "stress", days)
                df_trend = pd.DataFrame({"Hour": list(range(days)), "BPM": hr_vals, "Stress %": stress_vals})
                st.dataframe(df_trend, height=220, use_container_width=True)
            else:
                hcols = st.columns([10, 1])
                with hcols[0]:
                    st.markdown("#### 7-Day Trend")
                with hcols[1]:
                    if st.button("\u21ba", key="reset_trend_7d", help="Reset chart zoom"):
                        st.rerun()
                days = 7 * 24
                hr_vals = safe(get_seeded_history, [], username + "_doc", "bpm", days)
                stress_vals = safe(get_seeded_history, [], username + "_doc", "stress", days)
                fig_trend = go.Figure()
                fig_trend.add_trace(go.Scatter(
                    y=hr_vals, mode="lines", name="BPM",
                    line=dict(color="#ff6b6b", width=1.5, shape="spline"), opacity=0.7,
                ))
                fig_trend.add_trace(go.Scatter(
                    y=stress_vals, mode="lines", name="Stress %",
                    line=dict(color="#ffd93d", width=1.5, shape="spline"), opacity=0.7, yaxis="y2",
                ))
                fig_trend.update_layout(
                    height=200, margin=dict(l=10, r=10, t=20, b=20),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    legend=dict(orientation="h", y=1.1, font={"color": "#7a8aaa", "size": 11}),
                    xaxis=dict(visible=False, showgrid=False),
                    yaxis=dict(
                        title=dict(text="BPM", font={"color": "#4a5a7a", "size": 10}),
                        color="#4a5a7a", range=[50, 100], showgrid=False,
                    ),
                    yaxis2=dict(
                        title=dict(text="Stress %", font={"color": "#4a5a7a", "size": 10}),
                        color="#4a5a7a", overlaying="y", side="right", range=[0, 100], showgrid=False,
                    ),
                    title={"text": "7-Day Trend", "font": {"color": "#7a8aaa", "size": 13}, "x": 0.5},
                    hovermode="x unified", dragmode=False,
                )
                st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": False, "displaylogo": False})

        st.markdown("#### Vital Signs")
        ring2 = safe(get_ring_data, {"bpm":72,"stress":35,"sleep":7,"spo2":98,"mood":"neutral"}, username + "_doc", 1.0)
        vcols = st.columns(5)
        vital_metrics = [
            ("Heart Rate", f"{ring2['bpm']}", "bpm", "#ff6b6b"),
            ("Stress", f"{ring2['stress']}", "%", "#ffd93d"),
            ("Sleep", f"{ring2['sleep']}", "hrs", "#6bcbff"),
            ("SpO\u2082", f"{ring2['spo2']}", "%", "#6bffb8"),
            ("Mood", ring2["mood"].title(), "", "#c97bff"),
        ]
        for col, (label, val, unit, color) in zip(vcols, vital_metrics):
            with col:
                psych_metric(label, val, unit, color)

        if st.toggle("Show as table", key="stress_table"):
            stress_vals = safe(get_seeded_history, [], username + "_doc", "stress", 24)
            st.dataframe(
                pd.DataFrame({"Hour": list(range(24)), "Stress %": stress_vals}),
                height=160, use_container_width=True,
            )
        else:
            hcols = st.columns([10, 1])
            with hcols[0]:
                st.markdown("#### 24h Stress")
            with hcols[1]:
                if st.button("\u21ba", key="reset_stress_24h", help="Reset chart zoom"):
                    st.rerun()
            stress_vals = safe(get_seeded_history, [], username + "_doc", "stress", 24)
            fig_stress = go.Figure()
            fig_stress.add_trace(go.Scatter(
                y=stress_vals, mode="lines",
                line=dict(color="#ffd93d", width=1.5, shape="spline"), opacity=0.7,
            ))
            fig_stress.update_layout(
                margin=dict(l=10, r=10, t=10, b=20), height=140,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(title=dict(text="Hours", font={"color": "#4a5a7a", "size": 10}), color="#4a5a7a", showgrid=False),
                yaxis=dict(title=dict(text="Stress %", font={"color": "#4a5a7a", "size": 10}), color="#4a5a7a", range=[0, 100], showgrid=False),
                hovermode="x unified", dragmode=False,
            )
            st.plotly_chart(fig_stress, use_container_width=True, config={"displayModeBar": False, "displaylogo": False})

        st.markdown("### \U0001f4d3 My Journal")
        tab_write, tab_view = st.tabs(["Write Entry", "History"])
        with tab_write:
            with st.form("psych_journal_form"):
                raw_text = st.text_area("Reflect on your sessions...", placeholder="Write freely...", height=150)
                if st.form_submit_button("Save Journal Entry", type="primary", use_container_width=True):
                    if raw_text.strip():
                        with st.spinner("Analyzing..."):
                            summary = safe(summarize_journal, "Summary unavailable", raw_text)
                        safe(save_journal_entry, None, username, raw_text, summary)
                        st.success("Journal entry saved.")
        with tab_view:
            entries = safe(get_patient_history, [], username)
            if entries:
                for ei, e in enumerate(reversed(entries[-10:])):
                    key = f"doc_j_{ei}"
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
                            key=f"doc_j_dl_{ei}",
                        )
            else:
                st.info("No journal entries yet.")
    except Exception as e:
        st.error(f"Journal & Wellness tab unavailable:\n{e}")
