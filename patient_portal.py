import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

from ring import get_ring_data, get_seeded_history
from ai_kernel import summarize_journal
from data_manager import save_journal_entry, get_patient_history
from crisis import trigger_crisis, get_crisis_status, handle_escalation
from data_manager import load_bookings
from smart_room import render_smart_room
from booking import render_booking_form


def _build_metric_card(label, value, unit, color, delta=None):
    delta_str = f" ({delta})" if delta else ""
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, {color}22, {color}11);
            padding: 16px;
            border-radius: 12px;
            border: 1px solid {color}44;
            text-align: center;
        ">
            <div style="color:#889;font-size:13px;margin-bottom:4px;">{label}</div>
            <div style="color:white;font-size:28px;font-weight:700;">{value}</div>
            <div style="color:#889;font-size:12px;">{unit}{delta_str}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _build_trend_chart(username, metric, label, color, hours=24):
    values = get_seeded_history(username, metric, hours)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=values,
        mode="lines+markers",
        name=label,
        marker=dict(size=3, color=color),
        line=dict(color=color, width=2, shape="linear"),
    ))
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=20),
        height=120,
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        hovermode="x unified",
        dragmode=False,
    )
    fig.update_xaxes(showspikes=True, spikecolor="#556", spikethickness=1)
    fig.update_yaxes(showspikes=True, spikecolor="#556", spikethickness=1)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "displaylogo": False})


from followup import render_patient_followup

def render_patient_portal():
    username = st.session_state.username
    patient_name = st.session_state.get("patient_name", username)

    st.markdown(f"# 🌿 Welcome, {patient_name}")
    st.markdown("---")

    crisis = get_crisis_status()
    if crisis["active"] and crisis["patient"] == username:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=5000, key="crisis_patient_poll")
        handle_escalation()
        if crisis.get("acknowledged"):
            st.success(f"Crisis acknowledged. Support is active. {crisis['message']}")
        elif crisis.get("trustee_coming"):
            st.info("🟢 **Trusted contact is on the way.**")
        elif crisis.get("trustee_clicked"):
            st.info("👤 **Trusted contact has been notified.** They will confirm shortly.")
        else:
            st.error("🚨 **Emergency siren is active.** A psychologist has been alerted.")
            st.markdown(
                "<div style='background:#5a0000;padding:12px;border-radius:8px;"
                "color:#ff9999;text-align:center;font-weight:bold;'>"
                "Help is on the way. You are not alone.</div>",
                unsafe_allow_html=True,
            )

        elapsed = min(crisis.get("elapsed", 0), 60)
        stage = crisis.get("stage", "triggered")
        is_terminal = stage in ("acknowledged", "trustee_coming", "trustee_clicked", "helpline_escalated")
        stages = [
            ("triggered", "🚨 Triggered", 0),
            ("trustee_notified", "👤 Trusted Contact", 30),
            ("helpline_escalated", "🏥 Helpline", 60),
        ]
        bars_html = ""
        for key, label, sec in stages:
            active = key == stage or (is_terminal and stage == "trustee_coming" and key == "trustee_notified")
            passed = elapsed >= sec
            if not active:
                active = is_terminal and stage in ("helpline_escalated", "acknowledged") and key == "helpline_escalated"
            color = "#ff4444" if active else ("#44ff44" if passed else "#333")
            bg = "#4a0000" if active else ("#1a3a1a" if passed else "#1a1a2e")
            border = "2px solid #ff6666" if active else ("1px solid #44ff44" if passed else "1px solid #333")
            bars_html += f"<div style='flex:1;text-align:center;padding:8px;margin:0 4px;border-radius:8px;background:{bg};border:{border};color:{color};font-size:13px;font-weight:bold;'>{label}<br><span style='font-size:11px;font-weight:normal;'>{sec}s</span></div>"
        display_time = "60+" if crisis.get("elapsed", 0) >= 60 else str(elapsed)
        status_tag = ""
        if stage == "helpline_escalated":
            status_tag = "<span style='color:#ff4444;font-weight:bold;'>🏥 Helpline contacted</span>"
        elif stage == "trustee_coming":
            status_tag = "<span style='color:#44ff44;font-weight:bold;'>👤 Trusted contact on the way</span>"
        elif stage == "trustee_clicked":
            status_tag = "<span style='color:#88ff88;font-weight:bold;'>👤 Trusted contact notified</span>"
        elif stage == "acknowledged":
            status_tag = "<span style='color:#44ff44;font-weight:bold;'>✅ Psychologist acknowledged</span>"
        st.markdown(
            f"<div style='background:#0d1117;border:1px solid #2a3050;border-radius:10px;padding:12px;margin-top:8px;'>"
            f"<div style='display:flex;align-items:center;gap:12px;margin-bottom:8px;'>"
            f"<span style='color:#ff9999;font-size:18px;'>⏱️</span>"
            f"<span style='color:white;font-size:20px;font-weight:700;'>{display_time}s</span>"
            f"<span style='color:#889;font-size:13px;'>elapsed</span>"
            f"<div style='margin-left:auto;'>{status_tag}</div>"
            f"</div>"
            f"<div style='display:flex;'>{bars_html}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ── Booking notification ──
    if "booking_notified" not in st.session_state:
        st.session_state.booking_notified = {}
    bookings = load_bookings()
    my_bookings = [b for b in bookings if b['patient'] == username]
    if my_bookings:
        latest = my_bookings[-1]
        idx = len(bookings) - 1 - bookings[::-1].index(latest)
        prev_status = st.session_state.booking_notified.get(str(idx))
        if latest['status'] in ("Accepted", "Waitlisted") and prev_status != latest['status']:
            if latest['status'] == "Accepted":
                st.success("✅ **Booking Accepted!** Your session has been confirmed. Check the Booking tab for details.")
            else:
                st.warning("⏳ **Booking Waitlisted.** You've been placed on the waitlist. Check the Booking tab for updates.")
            st.session_state.booking_notified[str(idx)] = latest['status']

    tabs = st.tabs([
        "📊 Wellness",
        "📝 Journal",
        "📅 Booking",
        "📋 Follow-Up",
        "🧠 Smart Room",
        "🆘 Emergency",
    ])

    # ─────────────────────────────────────────────
    # TAB 0: Wellness Dashboard
    # ─────────────────────────────────────────────
    with tabs[0]:
        st.markdown("### 📊 Wellness Dashboard")
        ring = get_ring_data(username, 1.0)

        cols = st.columns(5)
        metrics = [
            ("Heart Rate", f"{ring['bpm']}", "bpm", "#ff6b6b"),
            ("Stress", f"{ring['stress']}", "%", "#ffd93d"),
            ("Sleep", f"{ring['sleep']}", "hrs", "#6bcbff"),
            ("SpO₂", f"{ring['spo2']}", "%", "#6bffb8"),
            ("Mood", ring["mood"].title(), "", "#c97bff"),
        ]
        for col, (label, val, unit, color) in zip(cols, metrics):
            with col:
                _build_metric_card(label, val, unit, color)

        view_toggle = st.toggle("Show as table", key="wellness_view")

        if view_toggle:
            st.markdown("#### 24h Trends — Table View")
            all_data = {}
            for metric, label, _ in [
                ("bpm", "Heart Rate", "#ff6b6b"),
                ("stress", "Stress", "#ffd93d"),
                ("sleep", "Sleep", "#6bcbff"),
                ("spo2", "SpO₂", "#6bffb8"),
            ]:
                all_data[label] = get_seeded_history(username, metric, 24)
            df = pd.DataFrame(all_data)
            st.dataframe(df, height=180, use_container_width=True)
        else:
            hcols = st.columns([10, 1])
            with hcols[0]:
                st.markdown("#### 24h Trends")
            with hcols[1]:
                if st.button("↺", key="reset_trends_patient", help="Reset chart zoom"):
                    st.rerun()
            trend_cols = st.columns(4)
            trends = [
                ("bpm", "Heart Rate", "#ff6b6b"),
                ("stress", "Stress", "#ffd93d"),
                ("sleep", "Sleep", "#6bcbff"),
                ("spo2", "SpO₂", "#6bffb8"),
            ]
            for col, (metric, label, color) in zip(trend_cols, trends):
                with col:
                    st.markdown(f"**{label}**")
                    _build_trend_chart(username, metric, label, color)

    # ─────────────────────────────────────────────
    # TAB 1: Journal
    # ─────────────────────────────────────────────
    with tabs[1]:
        st.markdown("### 📝 Wellness Journal")

        tab_journal, tab_history = st.tabs(["Write Entry", "Past Entries"])

        with tab_journal:
            with st.form("journal_form"):
                raw_text = st.text_area(
                    "How are you feeling right now?",
                    placeholder="Write freely. This content is private and only AI summaries are shared with your psychologist...",
                    height=150,
                )
                col1, col2 = st.columns([3, 1])
                with col2:
                    submitted = st.form_submit_button("Save Entry", type="primary", use_container_width=True)

                if submitted and raw_text.strip():
                    with st.spinner("Analyzing your entry..."):
                        summary = summarize_journal(raw_text)
                    save_journal_entry(username, raw_text, summary)
                    st.success("Entry saved. Your psychologist can see the summarized insights.")
                    st.rerun()

        with tab_history:
            entries = get_patient_history(username)
            if entries:
                for e in reversed(entries[-10:]):
                    with st.expander(f"{e['timestamp']}"):
                        st.markdown(f"**Summary**: {e['summary']}")
                        st.caption("Raw content is private and not shared.")
                df_journal = pd.DataFrame([
                    {"Date": e["timestamp"], "Summary": e["summary"]}
                    for e in reversed(entries)
                ])
                csv_journal = df_journal.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇ Download My Journal (CSV)",
                    csv_journal,
                    f"{username}_journal_export.csv",
                    "text/csv",
                    use_container_width=True,
                )
            else:
                st.info("No journal entries yet.")

    # ─────────────────────────────────────────────
    # TAB 2: Booking
    # ─────────────────────────────────────────────
    with tabs[2]:
        render_booking_form(username)

    # ─────────────────────────────────────────────
    # TAB 3: Follow-Up
    # ─────────────────────────────────────────────
    with tabs[3]:
        render_patient_followup(username)

    # ─────────────────────────────────────────────
    # TAB 4: Smart Room
    # ─────────────────────────────────────────────
    with tabs[4]:
        head_col1, head_col2 = st.columns([3, 1])
        with head_col1:
            st.markdown("### 🧠 Smart Room")
        with head_col2:
            intense = st.button(
                "⚡ Intense" if st.session_state.get("patient_room_intense", False) else "🌙 Calm",
                key="patient_room_toggle",
                use_container_width=True,
            )
            if intense:
                st.session_state.patient_room_intense = not st.session_state.patient_room_intense
                st.rerun()

        room_mode = "intense" if st.session_state.get("patient_room_intense", False) else "calm"
        render_smart_room(room_mode, 2.0 if room_mode == "intense" else 1.0)

    # ─────────────────────────────────────────────
    # TAB 5: Emergency
    # ─────────────────────────────────────────────
    with tabs[5]:
        st.markdown("### 🆘 Emergency")

        crisis_active = st.session_state.get("crisis_active", False)
        if crisis_active:
            st.error("🔴 **Siren Active** — Help is on the way.")
            if st.button("Cancel Emergency (False Alarm)", use_container_width=True):
                from data_manager import set_crisis_state
                set_crisis_state({
                    "active": False, "patient": "", "triggered_at": "",
                    "acknowledged": False, "acknowledged_by": "",
                    "helpline_escalated": False, "trusted_contact_notified": False,
                    "trustee_acknowledged": False, "trustee_clicked": False,
                })
                st.session_state.crisis_active = False
                st.session_state.crisis_acknowledged = False
                st.rerun()
        else:
            st.warning("If you are in crisis, help is available.")
            if st.button("🚨 TRIGGER EMERGENCY SIREN", type="primary", use_container_width=True):
                trigger_crisis(username)
                st.rerun()

    st.markdown("---")
    st.caption("Sentinel — Your wellness, monitored with care.")
