import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import json, os
from datetime import datetime

from ring import get_ring_data, get_seeded_history
from ai_kernel import summarize_journal, synthesize_clinical_notes
from data_manager import (
    get_all_patient_summaries,
    save_clinical_note,
    get_clinical_notes,
    save_journal_entry,
    get_patient_history,
)
from crisis import acknowledge_crisis, get_crisis_status
from patient_profiles import get_all_patients, get_patient_name
from smart_room import render_smart_room
from booking import render_booking_queue
from followup import render_psychologist_followup


def _build_psychologist_metric(label, value, unit, color):
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, {color}22, {color}11);
            padding: 14px;
            border-radius: 10px;
            border: 1px solid {color}44;
            text-align: center;
        ">
            <div style="color:#889;font-size:12px;">{label}</div>
            <div style="color:white;font-size:24px;font-weight:700;">{value}</div>
            <div style="color:#889;font-size:11px;">{unit}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _build_mini_chart(username, metric, color):
    values = get_seeded_history(username, metric, 24)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=values, mode="lines+markers",
        marker=dict(size=2, color=color),
        line=dict(color=color, width=2, shape="linear"),
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0), height=60,
        showlegend=False, paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        hovermode="x unified", dragmode=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "displaylogo": False})


def render_psychologist_portal():
    username = st.session_state.username
    doc_name = st.session_state.get("psychologist_name", username)

    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=5000, key="psych_crisis_poll")

    from crisis import handle_escalation, _play_alert
    handle_escalation()

    # ── CRISIS CHECK (reads file directly) ──
    _p = "data/crisis_state.json"
    if os.path.exists(_p):
        with open(_p) as _f:
            _cs = json.load(_f)
        if _cs.get("active"):
            _patient = _cs.get("patient", "Unknown")
            _elapsed = int((datetime.now() - datetime.fromisoformat(_cs["triggered_at"])).total_seconds())
            _display = "60+" if _elapsed >= 60 else str(_elapsed)
            if _cs.get("acknowledged"):
                _by = _cs.get("acknowledged_by", "clinician")
                if _cs.get("acknowledged_at"):
                    _resolved = int((datetime.fromisoformat(_cs["acknowledged_at"]) - datetime.fromisoformat(_cs["triggered_at"])).total_seconds())
                else:
                    _resolved = _elapsed
                _tc_msg = ""
                if _cs.get("trustee_acknowledged"):
                    _tc_msg = " | 👤 Trusted Contact was also on the way"
                st.success(f"✅ **Crisis Acknowledged by {_by}** — Resolved in {_resolved}s{_tc_msg}")
            elif _cs.get("trustee_acknowledged"):
                _play_alert()
                st.info(f"🟢 **Trusted Contact En Route — {_patient}**")
                st.markdown(f"<div style='background:#0d1117;border:1px solid #2a3050;border-radius:8px;padding:6px 10px;margin-bottom:6px;display:flex;align-items:center;gap:8px;font-size:13px;'><span style='color:#ff9999;'>⏱️</span><span style='color:white;font-weight:700;'>{_display}s</span><span style='color:#889;'>elapsed</span></div>", unsafe_allow_html=True)
                if st.button("✓ Acknowledge Crisis", type="primary", key="ps_ack_tc", use_container_width=True):
                    acknowledge_crisis(username)
                    st.rerun()
            elif _elapsed >= 60:
                _play_alert()
                _helpline_msg = f"🚨 **CRISIS ESCALATION — HELPLINE CONTACTED — {_patient}** 🚨"
                if _cs.get("trustee_clicked"):
                    _helpline_msg += " 👤 (TC notified)"
                st.error(_helpline_msg)
                st.markdown(f"<div style='background:#0d1117;border:1px solid #2a3050;border-radius:8px;padding:6px 10px;margin-bottom:6px;display:flex;align-items:center;gap:8px;font-size:13px;'><span style='color:#ff9999;'>⏱️</span><span style='color:white;font-weight:700;'>60+s</span><span style='color:#889;'>elapsed</span></div>", unsafe_allow_html=True)
                if st.button("✓ Acknowledge Crisis", type="primary", key="ps_ack_h", use_container_width=True):
                    acknowledge_crisis(username)
                    st.rerun()
            elif _cs.get("trustee_clicked"):
                _play_alert()
                st.info(f"👤 **Trusted Contact Notified — {_patient}**")
                st.markdown(f"<div style='background:#0d1117;border:1px solid #2a3050;border-radius:8px;padding:6px 10px;margin-bottom:6px;display:flex;align-items:center;gap:8px;font-size:13px;'><span style='color:#ff9999;'>⏱️</span><span style='color:white;font-weight:700;'>{_display}s</span><span style='color:#889;'>elapsed</span></div>", unsafe_allow_html=True)
                if st.button("✓ Acknowledge Crisis", type="primary", key="ps_ack_tcn", use_container_width=True):
                    acknowledge_crisis(username)
                    st.rerun()
            elif _elapsed >= 30:
                _play_alert()
                st.warning(f"⚠️ **Crisis Alert — {_patient}**")
                st.markdown(f"<div style='background:#0d1117;border:1px solid #2a3050;border-radius:8px;padding:6px 10px;margin-bottom:6px;display:flex;align-items:center;gap:8px;font-size:13px;'><span style='color:#ff9999;'>⏱️</span><span style='color:white;font-weight:700;'>{_elapsed}s</span><span style='color:#889;'>elapsed</span></div>", unsafe_allow_html=True)
                if st.button("✓ Acknowledge Crisis", type="primary", key="ps_ack_30", use_container_width=True):
                    acknowledge_crisis(username)
                    st.rerun()
            else:
                _play_alert()
                st.error(f"🚨 **Emergency Siren — {_patient}**")
                st.markdown(f"<div style='background:#0d1117;border:1px solid #2a3050;border-radius:8px;padding:6px 10px;margin-bottom:6px;display:flex;align-items:center;gap:8px;font-size:13px;'><span style='color:#ff9999;'>⏱️</span><span style='color:white;font-weight:700;'>{_elapsed}s</span><span style='color:#889;'>elapsed</span></div>", unsafe_allow_html=True)
                if st.button("✓ Acknowledge Crisis", type="primary", key="ps_ack_0", use_container_width=True):
                    acknowledge_crisis(username)
                    st.rerun()

    st.markdown(f"# 🏥 Welcome, {doc_name}")
    st.markdown("---")

    # --- Tabs ---
    tabs = st.tabs([
        "📋 Patient Triage",
        "📝 Clinical Notes",
        "📓 Journal & Wellness",
        "📅 Bookings",
        "📋 Follow-Up",
        "🧠 Smart Room",
        "📦 Export Center",
    ])

    # ─────────────────────────────────────────────────
    # TAB 1: Patient Triage
    # ─────────────────────────────────────────────────
    with tabs[0]:
        st.markdown("### Patient Triage Dashboard")

        patients = get_all_patients()
        if not patients:
            st.info("No patients registered.")
        else:
            summaries = get_all_patient_summaries()

            for patient in patients:
                pname = get_patient_name(patient)
                ring = get_ring_data(patient)
                crisis = get_crisis_status()

                is_crisis = crisis["active"] and crisis["patient"] == patient
                border = "2px solid #ff4444" if is_crisis else "1px solid rgba(255,255,255,0.1)"

                with st.expander(f"{'🚨 ' if is_crisis else ''}{pname} (@{patient})", expanded=is_crisis):
                    st.markdown(f"<div style='border:{border};border-radius:10px;padding:10px;'>", unsafe_allow_html=True)

                    cols = st.columns(5)
                    bio_metrics = [
                        ("BPM", f"{ring['bpm']}", "#ff6b6b"),
                        ("Stress", f"{ring['stress']}%", "#ffd93d"),
                        ("Sleep", f"{ring['sleep']}h", "#6bcbff"),
                        ("SpO₂", f"{ring['spo2']}%", "#6bffb8"),
                        ("Mood", ring["mood"].title(), "#c97bff"),
                    ]
                    for col, (label, val, color) in zip(cols, bio_metrics):
                        with col:
                            _build_psychologist_metric(label, val, "", color)

                    if st.toggle("Show as table", key=f"triage_tab_{patient}"):
                        chart_data = {}
                        for m, lbl, _ in [
                            ("bpm", "HR", "#ff6b6b"),
                            ("stress", "Stress", "#ffd93d"),
                            ("sleep", "Sleep", "#6bcbff"),
                            ("spo2", "SpO₂", "#6bffb8"),
                        ]:
                            chart_data[lbl] = get_seeded_history(patient, m, 24)
                        df = pd.DataFrame(chart_data)
                        st.dataframe(df, height=140, use_container_width=True)
                    else:
                        chart_cols = st.columns(4)
                        trends = [
                            ("bpm", "HR", "#ff6b6b"),
                            ("stress", "Stress", "#ffd93d"),
                            ("sleep", "Sleep", "#6bcbff"),
                            ("spo2", "SpO₂", "#6bffb8"),
                        ]
                        for col, (m, lbl, c) in zip(chart_cols, trends):
                            with col:
                                st.caption(lbl)
                                _build_mini_chart(patient, m, c)

                    # AI Insight
                    patient_summaries = summaries.get(patient, [])
                    if patient_summaries:
                        latest = patient_summaries[-1]["summary"]
                        st.markdown(f"**AI Clinical Insight**: {latest}")
                    else:
                        st.caption("No journal data yet.")

                    st.markdown("</div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────
    # TAB 2: Clinical Notes
    # ─────────────────────────────────────────────────
    with tabs[1]:
        st.markdown("### Clinical Documentation")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### New Session Note")
            patients = get_all_patients()
            if patients:
                selected_patient = st.selectbox("Patient", patients, format_func=lambda p: get_patient_name(p))

                with st.form("clinical_note_form"):
                    raw_notes = st.text_area(
                        "Session Observations",
                        placeholder="Enter your session notes. AI will structure them into a clinical note...",
                        height=200,
                    )
                    if st.form_submit_button("Generate & Save Note", type="primary", use_container_width=True):
                        if raw_notes.strip():
                            with st.spinner("Synthesizing clinical note..."):
                                synthesis = synthesize_clinical_notes(raw_notes)
                            save_clinical_note(username, selected_patient, raw_notes, synthesis)
                            st.success("Clinical note saved.")
                            st.rerun()

        with col2:
            st.markdown("#### Saved Notes")
            notes = get_clinical_notes(username)
            if notes:
                for n in reversed(notes[-10:]):
                    with st.expander(f"{n['patient']} — {n['timestamp']}"):
                        st.markdown(f"**Patient**: {get_patient_name(n['patient'])}")
                        st.markdown(n["ai_synthesis"])
            else:
                st.info("No notes yet.")

    # ─────────────────────────────────────────────────
    # TAB 2: My Journal (Psychologist)
    # ─────────────────────────────────────────────────
    with tabs[2]:
        ring = get_ring_data(username + "_doc", 1.0)

        col_gauge, col_chart = st.columns([1, 2])

        with col_gauge:
            fig_bpm = go.Figure(go.Indicator(
                mode="gauge+number",
                value=ring["bpm"],
                number={"font": {"color": "#ff6b6b", "size": 28}},
                gauge={
                    "axis": {"range": [40, 120], "visible": False},
                    "bar": {"color": "#ff6b6b", "thickness": 0.4},
                    "bgcolor": "#111827",
                    "borderwidth": 0,
                    "steps": [
                        {"range": [40, 60], "color": "#1a2a1a"},
                        {"range": [60, 100], "color": "#1a1f2e"},
                        {"range": [100, 120], "color": "#2a1a1a"},
                    ],
                    "threshold": {
                        "line": {"color": "white", "width": 2},
                        "thickness": 0.6,
                        "value": ring["bpm"],
                    },
                },
                domain={"x": [0, 1], "y": [0, 0.9]},
            ))
            fig_bpm.update_layout(
                height=160, margin=dict(l=10, r=10, t=20, b=0),
                paper_bgcolor="rgba(0,0,0,0)", font={"color": "#aaa"},
                title={"text": "BPM", "font": {"color": "#ff6b6b", "size": 13}, "x": 0.5},
            )
            st.plotly_chart(fig_bpm, use_container_width=True, config={"displayModeBar": False})

            fig_spo2 = go.Figure(go.Indicator(
                mode="gauge+number",
                value=ring["spo2"],
                number={"font": {"color": "#6bffb8", "size": 28}, "suffix": "%"},
                gauge={
                    "axis": {"range": [90, 100], "visible": False},
                    "bar": {"color": "#6bffb8", "thickness": 0.4},
                    "bgcolor": "#111827",
                    "borderwidth": 0,
                    "steps": [
                        {"range": [90, 95], "color": "#2a1a1a"},
                        {"range": [95, 100], "color": "#1a2a1a"},
                    ],
                    "threshold": {
                        "line": {"color": "white", "width": 2},
                        "thickness": 0.6,
                        "value": ring["spo2"],
                    },
                },
                domain={"x": [0, 1], "y": [0, 0.9]},
            ))
            fig_spo2.update_layout(
                height=160, margin=dict(l=10, r=10, t=20, b=0),
                paper_bgcolor="rgba(0,0,0,0)", font={"color": "#aaa"},
                title={"text": "SpO₂", "font": {"color": "#6bffb8", "size": 13}, "x": 0.5},
            )
            st.plotly_chart(fig_spo2, use_container_width=True, config={"displayModeBar": False})

        with col_chart:
            if st.toggle("Show as table", key="trend_table"):
                days = 7 * 24
                hr_vals = get_seeded_history(username + "_doc", "bpm", days)
                stress_vals = get_seeded_history(username + "_doc", "stress", days)
                df_trend = pd.DataFrame({"Hour": list(range(days)), "BPM": hr_vals, "Stress %": stress_vals})
                st.dataframe(df_trend, height=220, use_container_width=True)
            else:
                hcols = st.columns([10, 1])
                with hcols[0]:
                    st.markdown("#### 7-Day Trend")
                with hcols[1]:
                    if st.button("↺", key="reset_trend_7d", help="Reset chart zoom"):
                        st.rerun()
                days = 7 * 24
                hr_vals = get_seeded_history(username + "_doc", "bpm", days)
                stress_vals = get_seeded_history(username + "_doc", "stress", days)

                fig_trend = go.Figure()
                fig_trend.add_trace(go.Scatter(
                    y=hr_vals, mode="lines+markers", name="BPM",
                    marker=dict(size=2, color="#ff6b6b"),
                    line=dict(color="#ff6b6b", width=1.5, shape="linear"),
                ))
                fig_trend.add_trace(go.Scatter(
                    y=stress_vals, mode="lines+markers", name="Stress %",
                    marker=dict(size=2, color="#ffd93d"),
                    line=dict(color="#ffd93d", width=1.5, shape="linear"),
                    yaxis="y2",
                ))
                fig_trend.update_layout(
                    height=220, margin=dict(l=10, r=10, t=20, b=30),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    legend=dict(orientation="h", y=1.1, font={"color": "#aaa", "size": 11}),
                    xaxis=dict(visible=False),
                    yaxis=dict(title="BPM", color="#ff6b6b", range=[50, 100]),
                    yaxis2=dict(
                        title="Stress %", color="#ffd93d", overlaying="y", side="right",
                        range=[0, 100],
                    ),
                    title={"text": "7-Day Trend", "font": {"color": "#ccc", "size": 14}, "x": 0.5},
                    hovermode="x unified", dragmode=False,
                )
                fig_trend.update_xaxes(showspikes=True, spikecolor="#556", spikethickness=1)
                fig_trend.update_yaxes(showspikes=True, spikecolor="#556", spikethickness=1)
                st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": False, "displaylogo": False})

        st.markdown("#### Vital Signs")
        ring2 = get_ring_data(username + "_doc", 1.0)
        vcols = st.columns(5)
        vital_metrics = [
            ("Heart Rate", f"{ring2['bpm']}", "bpm", "#ff6b6b"),
            ("Stress", f"{ring2['stress']}", "%", "#ffd93d"),
            ("Sleep", f"{ring2['sleep']}", "hrs", "#6bcbff"),
            ("SpO₂", f"{ring2['spo2']}", "%", "#6bffb8"),
            ("Mood", ring2["mood"].title(), "", "#c97bff"),
        ]
        for col, (label, val, unit, color) in zip(vcols, vital_metrics):
            with col:
                _build_psychologist_metric(label, val, unit, color)

        if st.toggle("Show as table", key="stress_table"):
            stress_vals = get_seeded_history(username + "_doc", "stress", 24)
            df_stress = pd.DataFrame({"Hour": list(range(24)), "Stress %": stress_vals})
            st.dataframe(df_stress, height=160, use_container_width=True)
        else:
            hcols = st.columns([10, 1])
            with hcols[0]:
                st.markdown("#### 24h Stress")
            with hcols[1]:
                if st.button("↺", key="reset_stress_24h", help="Reset chart zoom"):
                    st.rerun()
            stress_vals = get_seeded_history(username + "_doc", "stress", 24)
            fig_stress = go.Figure()
            fig_stress.add_trace(go.Scatter(
                y=stress_vals, mode="lines+markers",
                marker=dict(size=2, color="#ffd93d"),
                line=dict(color="#ffd93d", width=2, shape="linear"),
            ))
            fig_stress.update_layout(
                margin=dict(l=10, r=10, t=10, b=30), height=160,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(title="Hours", color="#556"),
                yaxis=dict(title="Stress %", color="#556", range=[0, 100]),
                hovermode="x unified", dragmode=False,
            )
            fig_stress.update_xaxes(showspikes=True, spikecolor="#556", spikethickness=1)
            fig_stress.update_yaxes(showspikes=True, spikecolor="#556", spikethickness=1)
            st.plotly_chart(fig_stress, use_container_width=True, config={"displayModeBar": False, "displaylogo": False})

        st.markdown("### 📓 My Journal")

        tab_write, tab_view = st.tabs(["Write Entry", "History"])

        with tab_write:
            with st.form("psych_journal_form"):
                raw_text = st.text_area(
                    "Reflect on your sessions, thoughts, or clinical observations",
                    placeholder="Write freely. AI will generate a summary for your records...",
                    height=150,
                )
                if st.form_submit_button("Save Journal Entry", type="primary", use_container_width=True):
                    if raw_text.strip():
                        with st.spinner("Analyzing..."):
                            summary = summarize_journal(raw_text)
                        save_journal_entry(username, raw_text, summary)
                        st.success("Journal entry saved.")
                        st.rerun()

        with tab_view:
            entries = get_patient_history(username)
            if entries:
                for e in reversed(entries[-10:]):
                    with st.expander(f"{e['timestamp']}"):
                        st.markdown(f"**Summary**: {e['summary']}")
                        st.caption("Raw content is private.")
                df = pd.DataFrame([
                    {"Date": e["timestamp"], "Summary": e["summary"]}
                    for e in reversed(entries)
                ])
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇ Download My Journal (CSV)",
                    csv,
                    f"{username}_journal_export.csv",
                    "text/csv",
                    use_container_width=True,
                )
            else:
                st.info("No journal entries yet.")

    # ─────────────────────────────────────────────────
    # TAB 3: Bookings
    # ─────────────────────────────────────────────────
    with tabs[3]:
        render_booking_queue()

    # ─────────────────────────────────────────────────
    # TAB 4: Follow-Up
    # ─────────────────────────────────────────────────
    with tabs[4]:
        render_psychologist_followup(username)

    # ─────────────────────────────────────────────────
    # TAB 5: Smart Room
    # ─────────────────────────────────────────────────
    with tabs[5]:
        head_col1, head_col2 = st.columns([3, 1])
        with head_col1:
            st.markdown("### 🧠 Smart Room")
        with head_col2:
            intense = st.button(
                "⚡ Intense" if st.session_state.get("psych_room_intense", False) else "🌙 Calm",
                key="psych_room_toggle",
                use_container_width=True,
            )
            if intense:
                st.session_state.psych_room_intense = not st.session_state.psych_room_intense
                st.rerun()

        room_mode = "intense" if st.session_state.get("psych_room_intense", False) else "calm"
        render_smart_room(room_mode, 2.0 if room_mode == "intense" else 1.0)

    # ─────────────────────────────────────────────────
    # TAB 6: Export Center
    # ─────────────────────────────────────────────────
    with tabs[6]:
        st.markdown("### 📦 Export Center")

        export_type = st.radio("Export Type", ["Patient Journal Summaries", "My Clinical Notes", "My Journal"], horizontal=True)

        if export_type == "Patient Journal Summaries":
            summaries = get_all_patient_summaries()
            if not summaries:
                st.info("No patient journal data available.")
            else:
                export_data = []
                for patient, entries in summaries.items():
                    for e in entries:
                        export_data.append({
                            "Patient": get_patient_name(patient),
                            "Date": e["timestamp"],
                            "AI Summary": e["summary"],
                        })
                if export_data:
                    df = pd.DataFrame(export_data)
                    st.dataframe(df, use_container_width=True)
                    csv = df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "⬇ Download Patient Summaries (CSV)",
                        csv,
                        "patient_summaries_export.csv",
                        "text/csv",
                        use_container_width=True,
                    )
        elif export_type == "My Clinical Notes":
            notes = get_clinical_notes(username)
            if not notes:
                st.info("No clinical notes yet.")
            else:
                notes_data = []
                for n in reversed(notes):
                    notes_data.append({
                        "Patient": get_patient_name(n["patient"]),
                        "Date": n["timestamp"],
                        "AI Synthesis": n["ai_synthesis"],
                    })
                df = pd.DataFrame(notes_data)
                st.dataframe(df, use_container_width=True)
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇ Download My Clinical Notes (CSV)",
                    csv,
                    f"{username}_clinical_notes_export.csv",
                    "text/csv",
                    use_container_width=True,
                )
        else:
            journal = get_patient_history(username)
            if not journal:
                st.info("No journal entries yet.")
            else:
                journal_data = []
                for e in reversed(journal):
                    journal_data.append({
                        "Date": e["timestamp"],
                        "Summary": e["summary"],
                    })
                df = pd.DataFrame(journal_data)
                st.dataframe(df, use_container_width=True)
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇ Download My Journal (CSV)",
                    csv,
                    f"{username}_journal_export.csv",
                    "text/csv",
                    use_container_width=True,
                )

    st.markdown("---")
    st.caption("Sentinel — Clinician Portal")
