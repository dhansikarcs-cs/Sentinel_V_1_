import streamlit as st
import traceback
from datetime import datetime, timedelta

try:
    from ring_ import get_ring_data
except Exception:
    get_ring_data = None

try:
    from data_manager_ import get_patient_history, load_bookings, get_activity_feed
except Exception:
    get_patient_history = load_bookings = get_activity_feed = None

try:
    from crisis_ import trigger_crisis, resolve_crisis, get_crisis_status
except Exception:
    trigger_crisis = resolve_crisis = get_crisis_status = None

try:
    from patient_profiles_ import get_patient_name
except Exception:
    get_patient_name = None

try:
    from agent_ import ring_vitals_risk
except Exception:
    ring_vitals_risk = None

try:
    from psych_shared_ import safe
except Exception:
    safe = None


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
    }


def render_psych_triage(username: str):
    st.markdown("### \U0001f4ca Priority Triage Dashboard")

    try:
        from data_manager_ import get_all_patients, get_crisis_state
    except Exception:
        get_all_patients = get_crisis_state = None

    pts = safe(get_all_patients, [])
    if not pts:
        st.info("No patients registered.")
        return

    crisis_state = safe(get_crisis_state, {})

    with st.spinner("Analyzing patient risk..."):
        priorities = sorted([_compute_priority(p, crisis_state) for p in pts], key=lambda x: (x["tier"] != "crisis", x["tier"] != "high", x["tier"] != "attention", -x["score"]))

    counts = {"crisis": 0, "high": 0, "attention": 0, "stable": 0}
    for p in priorities:
        counts[p["tier"]] = counts.get(p["tier"], 0) + 1

    summary_cols = st.columns(4)
    summary_data = [
        ("\U0001f6a8 Crisis", counts["crisis"], "#ef4444"),
        ("\U0001f7e1 High", counts["high"], "#f59e0b"),
        ("\U0001f7e0 Attention", counts["attention"], "#60a5fa"),
        ("\U0001f7e2 Stable", counts["stable"], "#22c55e"),
    ]
    for col, (label, count, color) in zip(summary_cols, summary_data):
        with col:
            st.markdown(
                f"<div style='background:#1a2238;border:1px solid {color}30;border-radius:10px;padding:10px;text-align:center;'>"
                f"<div style='color:{color};font-size:0.75rem;font-weight:600;'>{label}</div>"
                f"<div style='color:#f0f4ff;font-size:1.5rem;font-weight:700;'>{count}</div></div>",
                unsafe_allow_html=True,
            )

    st.markdown("---")

    for p in priorities:
        _render_priority_card(p, username, crisis_state)


def _render_priority_card(p: dict, username: str, crisis_state: dict):
    patient = p["patient"]
    pname = safe(get_patient_name, patient, patient)

    tier_colors = {
        "crisis": ("#ef4444", "rgba(239,68,68,0.1)", "1px solid rgba(239,68,68,0.4)"),
        "high": ("#f59e0b", "rgba(245,158,11,0.08)", "1px solid rgba(245,158,11,0.3)"),
        "attention": ("#60a5fa", "rgba(96,165,250,0.08)", "1px solid rgba(96,165,250,0.2)"),
        "stable": ("#22c55e", "rgba(34,197,94,0.06)", "1px solid rgba(34,197,94,0.15)"),
    }
    accent, bg, border = tier_colors.get(p["tier"], tier_colors["stable"])

    tier_badge = {"crisis": "\U0001f6a8 CRISIS", "high": "\U0001f7e1 HIGH", "attention": "\U0001f7e0 ATTENTION", "stable": "\U0001f7e2 STABLE"}

    flags = []
    if p["crisis"]:
        flags.append(f"<span style='background:#ef444422;color:#ef4444;border:1px solid #ef4444;border-radius:4px;padding:1px 6px;font-size:0.65rem;'>\U0001f6a8 Active Crisis</span>")
    if p["silent"]:
        flags.append(f"<span style='background:#f59e0b22;color:#f59e0b;border:1px solid #f59e0b;border-radius:4px;padding:1px 6px;font-size:0.65rem;'>\U0001f50a Silent >48h</span>")
    if p["ring_risk"] in ("high", "medium"):
        flags.append(f"<span style='background:#ef444422;color:#ef4444;border:1px solid #ef4444;border-radius:4px;padding:1px 6px;font-size:0.65rem;'>\U0001f493 Ring: {p['ring_risk'].title()}</span>")
    for f in p["ring_flags"]:
        flags.append(f"<span style='background:#f59e0b22;color:#f59e0b;border:1px solid #f59e0b;border-radius:4px;padding:1px 6px;font-size:0.65rem;'>\u26a0\ufe0f {f.replace('_',' ').title()}</span>")
    if p["pending"]:
        flags.append(f"<span style='background:#60a5fa22;color:#60a5fa;border:1px solid #60a5fa;border-radius:4px;padding:1px 6px;font-size:0.65rem;'>\U0001f4c5 {p['pending']} Pending</span>")

    flags_html = " ".join(flags) if flags else ""

    with st.expander(f"{pname} (@{patient})  \u2014  <span style='color:{accent};font-weight:600;'>{tier_badge[p['tier']]} ({p['score']}pts)</span>", expanded=p["tier"] in ("crisis", "high")):
        st.markdown(
            f"<div style='background:{bg};border:{border};border-radius:10px;padding:12px;'>"
            f"<div style='display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:8px;'>"
            f"<span style='color:#7a8aaa;font-size:0.75rem;'>&#x2764; {p['bpm']} bpm</span>"
            f"<span style='color:#7a8aaa;font-size:0.75rem;'>\u26a1 {p['stress']}%</span>"
            f"<span style='color:#7a8aaa;font-size:0.75rem;'>{p['mood']}</span>"
            f"<span style='color:#7a8aaa;font-size:0.75rem;'>Last journal: {p['last_journal'] or 'never'}</span>"
            f"</div>"
            f"<div style='margin-bottom:4px;'>{flags_html}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        actions_cols = st.columns(3)
        with actions_cols[0]:
            if p["crisis"]:
                if st.button("\u2705 Resolve Crisis", key=f"res_{patient}", use_container_width=True, type="primary"):
                    safe(resolve_crisis, None, username)
            else:
                if st.button("\U0001f6a8 Trigger Crisis", key=f"trig_{patient}", use_container_width=True):
                    safe(trigger_crisis, None, patient, "psychologist")
        with actions_cols[1]:
            st.markdown(
                f"<div style='text-align:center;font-size:0.75rem;color:#7a8aaa;padding:6px;'>"
                f"<span style='color:#60a5fa;'>{pname}</span></div>",
                unsafe_allow_html=True,
            )
        with actions_cols[2]:
            st.markdown(
                f"<div style='text-align:right;font-size:0.6875rem;color:#5a6a8a;padding:6px;'>"
                f"Score: {p['score']} | {tier_badge[p['tier']]}</div>",
                unsafe_allow_html=True,
            )
