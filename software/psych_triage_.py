import streamlit as st
import traceback
from datetime import datetime, timedelta

try:
    from ring_ import get_ring_data, get_seeded_history
except Exception:
    get_ring_data = get_seeded_history = None

try:
    from data_manager_ import get_patient_history, load_bookings
except Exception:
    get_patient_history = load_bookings = None

try:
    from crisis_ import trigger_crisis, resolve_crisis, get_crisis_status
except Exception:
    trigger_crisis = resolve_crisis = get_crisis_status = None

try:
    from patient_profiles_ import get_patient_name, get_contact_info, get_any_trusted_contact
except Exception:
    get_patient_name = get_contact_info = get_any_trusted_contact = None

try:
    from agent_ import ring_vitals_risk
except Exception:
    ring_vitals_risk = None

try:
    from psych_shared_ import safe
except Exception:
    safe = None

try:
    import plotly.graph_objects as go
except Exception:
    go = None

try:
    import pandas as pd
except Exception:
    pd = None


def _build_metric(label, value, unit, color):
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


def _build_mini_chart(patient, metric, color):
    values = safe(get_seeded_history, [], patient, metric, 24)
    if not values or go is None:
        return
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


def _compute_priority(patient: str, crisis_state: dict) -> dict:
    ring = safe(get_ring_data, {"bpm":72,"stress":35,"sleep":7,"spo2":98,"mood":"neutral"}, patient)
    vr = safe(ring_vitals_risk, {"risk":"low","flags":[]}, ring)
    crisis = crisis_state.get("active") and crisis_state.get("patient") == patient
    entries = safe(get_patient_history, [], patient)
    last_ts = entries[-1]["timestamp"] if entries else ""
    silent = False
    if last_ts:
        try:
            silent = datetime.now() - datetime.fromisoformat(last_ts) > timedelta(hours=48)
        except Exception:
            silent = True
    else:
        silent = True

    bookings = safe(load_bookings, [])
    my_bookings = [b for b in bookings if b["patient"] == patient]
    pending = sum(1 for b in my_bookings if b["status"] in ("Proposed", "Pending"))

    score = 0
    if crisis:
        score += 100
    if vr["risk"] == "high":
        score += 50
    elif vr["risk"] == "medium":
        score += 25
    if silent:
        score += 30
    if len(vr["flags"]) > 0:
        score += len(vr["flags"]) * 10
    if pending:
        score += 5

    if crisis:
        tier = "crisis"
    elif score >= 40:
        tier = "high"
    elif score >= 15:
        tier = "attention"
    else:
        tier = "stable"

    return {
        "patient": patient,
        "score": score,
        "tier": tier,
        "crisis": crisis,
        "silent": silent,
        "ring_risk": vr["risk"],
        "ring_flags": vr["flags"],
        "pending": pending,
        "last_journal": last_ts[:10] if last_ts else "",
        "mood": ring.get("mood", "neutral").title(),
        "bpm": ring.get("bpm", 0),
        "stress": ring.get("stress", 0),
        "sleep": ring.get("sleep", 7),
        "spo2": ring.get("spo2", 98),
    }


def render_psych_triage(username: str):
    st.markdown("### \U0001f4ca Priority Triage Dashboard")

    try:
        from patient_profiles_ import get_assigned_patients
        from data_manager_ import get_crisis_state, get_all_patient_summaries
    except Exception:
        get_assigned_patients = get_crisis_state = get_all_patient_summaries = None

    pts = safe(get_assigned_patients, [], username)
    if not pts:
        st.info("No patients registered.")
        return

    crisis_state = safe(get_crisis_state, {})
    summaries = safe(get_all_patient_summaries, {})

    with st.spinner("Analyzing patient risk..."):
        priorities = sorted(
            [_compute_priority(p, crisis_state) for p in pts],
            key=lambda x: (x["tier"] != "crisis", x["tier"] != "high", x["tier"] != "attention", -x["score"]),
        )

    counts = {"crisis": 0, "high": 0, "attention": 0, "stable": 0}
    for p in priorities:
        counts[p["tier"]] = counts.get(p["tier"], 0) + 1

    summary_cols = st.columns(4)
    summary_data = [
        ("\U0001f6a8 Crisis", counts["crisis"], "#ef4444"),
        ("\U0001f7e1 High", counts["high"], "#f59e0b"),
        ("\U0001f7e0 Attention", counts["attention"], "#c49ea4"),
        ("\U0001f7e2 Stable", counts["stable"], "#22c55e"),
    ]
    for col, (label, count, color) in zip(summary_cols, summary_data):
        with col:
            st.markdown(
                f"<div style='background:#1e2336;border:1px solid {color}30;border-radius:10px;padding:10px;text-align:center;'>"
                f"<div style='color:{color};font-size:0.75rem;font-weight:600;'>{label}</div>"
                f"<div style='color:#f0f4ff;font-size:1.5rem;font-weight:700;'>{count}</div></div>",
                unsafe_allow_html=True,
            )

    st.markdown("---")

    for p in priorities:
        patient = p["patient"]
        pname = safe(get_patient_name, patient, patient)
        ring = {"bpm": p["bpm"], "stress": p["stress"], "sleep": p["sleep"], "spo2": p["spo2"], "mood": p["mood"].lower()}
        is_crisis = p["crisis"]
        border = "2px solid #ff4444" if is_crisis else "1px solid rgba(255,255,255,0.1)"

        _crisis_icon = "\U0001f6a8 "
        with st.expander(f"{_crisis_icon if is_crisis else ''}{pname} (@{patient})", expanded=is_crisis):
            st.markdown(f"<div style='border:{border};border-radius:10px;padding:10px;'>", unsafe_allow_html=True)
            cols = st.columns(5)
            bio_metrics = [
                ("BPM", f"{ring['bpm']}", "#ff6b6b"),
                ("Stress", f"{ring['stress']}%", "#ffd93d"),
                ("Sleep", f"{ring['sleep']}h", "#d8b4ba"),
                ("SpO\u2082", f"{ring['spo2']}%", "#6bffb8"),
                ("Mood", ring["mood"].title(), "#c49ea4"),
            ]
            for col, (label, val, color) in zip(cols, bio_metrics):
                with col:
                    _build_metric(label, val, "", color)

            _chart_toggle_key = f"triage_tab_{patient}"
            if st.toggle("Show as table", key=_chart_toggle_key):
                if pd is not None:
                    chart_data = {}
                    for m, lbl in [("bpm","HR"),("stress","Stress"),("sleep","Sleep"),("spo2","SpO\u2082")]:
                        chart_data[lbl] = safe(get_seeded_history, [], patient, m, 24)
                    df = pd.DataFrame(chart_data)
                    st.dataframe(df, height=140, use_container_width=True)
            else:
                chart_cols = st.columns(4)
                trends = [("bpm","HR","#ff6b6b"),("stress","Stress","#ffd93d"),("sleep","Sleep","#d8b4ba"),("spo2","SpO\u2082","#6bffb8")]
                for col, (m, lbl, c) in zip(chart_cols, trends):
                    with col:
                        st.caption(lbl)
                        _build_mini_chart(patient, m, c)

            ps = summaries.get(patient, [])
            if ps:
                st.markdown(f"**AI Clinical Insight**: {ps[-1]['summary']}")
            else:
                st.caption("No journal data yet.")

            _pt_email = safe(get_contact_info, "", patient)
            _pt_tc = safe(get_any_trusted_contact, "", patient)
            if _pt_email or _pt_tc:
                _email_icon = "\U0001f4e7"
                _tc_icon = "\U0001f464"
                _email_part = f"{_email_icon} Patient: {_pt_email}" if _pt_email else ""
                _tc_part = f" &nbsp;|&nbsp; {_tc_icon} TC: {_pt_tc}" if _pt_tc else ""
                st.markdown(
                    f"<div style='font-size:0.6875rem;color:#6a6474;margin-top:6px;'>"
                    f"{_email_part}{_tc_part}</div>",
                    unsafe_allow_html=True,
                )

            st.markdown("</div>", unsafe_allow_html=True)

            actions_cols = st.columns(3)
            with actions_cols[0]:
                if is_crisis:
                    if st.button("\u2705 Resolve Crisis", key=f"res_{patient}", use_container_width=True, type="primary"):
                        safe(resolve_crisis, None, username)
                else:
                    if st.button("\U0001f6a8 Trigger Crisis", key=f"trig_{patient}", use_container_width=True):
                        safe(trigger_crisis, None, patient, "psychologist")
            with actions_cols[1]:
                st.markdown(
                    f"<div style='text-align:center;font-size:0.75rem;color:#6a6474;padding:6px;'>"
                    f"<span style='color:#c49ea4;'>{pname}</span></div>",
                    unsafe_allow_html=True,
                )
            with actions_cols[2]:
                _tier_label = "\U0001f6a8 CRISIS" if is_crisis else "HIGH" if p['tier']=='high' else "ATTENTION" if p['tier']=='attention' else "STABLE"
                st.markdown(
                    f"<div style='text-align:right;font-size:0.6875rem;color:#5a4a5a;padding:6px;'>"
                    f"Score: {p['score']} | {_tier_label}</div>",
                    unsafe_allow_html=True,
                )
