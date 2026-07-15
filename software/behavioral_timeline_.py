from datetime import datetime, timedelta, date
from typing import Optional

try:
    from database import get_db
except Exception:
    get_db = None


def _safe(func, default=None, *args, **kwargs):
    try:
        if func:
            return func(*args, **kwargs)
    except Exception:
        pass
    return default


def get_mood_history(patient_username: str, days: int = 30) -> list[dict]:
    try:
        with get_db() as db:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            rows = db.execute(
                "SELECT date, emoji, label, timestamp FROM mood_log WHERE patient_username = ? AND timestamp >= ? ORDER BY timestamp",
                (patient_username, cutoff),
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def get_journal_history(patient_username: str, days: int = 30) -> list[dict]:
    try:
        with get_db() as db:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            rows = db.execute(
                "SELECT id, title, summary, emotions, timestamp FROM journal_entries WHERE patient_username = ? AND timestamp >= ? ORDER BY timestamp",
                (patient_username, cutoff),
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def get_followup_history(patient_username: str, days: int = 30) -> list[dict]:
    try:
        with get_db() as db:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            rows = db.execute(
                "SELECT id, title, description, status, assigned_at, completed_at FROM followup_tasks WHERE patient_username = ? AND (assigned_at >= ? OR completed_at >= ?) ORDER BY assigned_at",
                (patient_username, cutoff, cutoff),
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def get_crisis_history(patient_username: str, days: int = 30) -> list[dict]:
    try:
        with get_db() as db:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            rows = db.execute(
                "SELECT id, event, patient, timestamp FROM crisis_log WHERE patient = ? AND timestamp >= ? ORDER BY timestamp",
                (patient_username, cutoff),
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def compute_change_metrics(patient_username: str) -> dict:
    now = datetime.now()
    current = [now - timedelta(days=i) for i in range(7, 14)]
    previous = [now - timedelta(days=i) for i in range(0, 7)]

    moods = get_mood_history(patient_username, 14)
    journals = get_journal_history(patient_username, 14)

    _mood_val = {"great": 5, "good": 4, "okay": 3, "bad": 2, "awful": 1, "terrible": 0}
    _reversed = {v: k for k, v in _mood_val.items()}

    def _avg_mood(moods_subset):
        vals = [m["label"] for m in moods_subset if m.get("label") in _mood_val]
        return sum(_mood_val[v] for v in vals) / len(vals) if vals else None

    current_moods = [m for m in moods if datetime.fromisoformat(m.get("timestamp", "2000")) >= (now - timedelta(days=7))]
    previous_moods = [m for m in moods if datetime.fromisoformat(m.get("timestamp", "2000")) < (now - timedelta(days=7)) and datetime.fromisoformat(m.get("timestamp", "2000")) >= (now - timedelta(days=14))]

    current_avg = _avg_mood(current_moods)
    previous_avg = _avg_mood(previous_moods)

    latest_mood = moods[-1] if moods else None
    latest_label = latest_mood.get("label", "unknown") if latest_mood else "none"

    journal_count_7 = len([j for j in journals if datetime.fromisoformat(j.get("timestamp", "2000")) >= (now - timedelta(days=7))])
    journal_count_14 = len(journals)

    return {
        "current_mood_avg": current_avg,
        "previous_mood_avg": previous_avg,
        "mood_trend": "improving" if (current_avg is not None and previous_avg is not None and current_avg > previous_avg + 0.25) else
                      "declining" if (current_avg is not None and previous_avg is not None and current_avg < previous_avg - 0.25) else
                      "stable" if (current_avg is not None and previous_avg is not None) else "insufficient_data",
        "mood_change_pct": round((current_avg - previous_avg) / previous_avg * 100, 1) if (current_avg is not None and previous_avg and previous_avg > 0) else None,
        "mood_current_label": _reversed.get(round(current_avg)) if current_avg is not None else latest_label,
        "latest_mood": latest_mood,
        "journal_count_7": journal_count_7,
        "journal_count_14": journal_count_14,
        "engagement_trend": "increasing" if journal_count_7 > max(1, journal_count_14 / 2) else
                           "declining" if journal_count_7 < journal_count_14 / 4 else
                           "stable" if journal_count_14 > 0 else "none",
    }


def get_behavioral_timeline(patient_username: str, days: int = 30) -> list[dict]:
    events = []

    for m in get_mood_history(patient_username, days):
        events.append({
            "type": "mood",
            "timestamp": m.get("timestamp", ""),
            "date": m.get("date", ""),
            "data": m,
        })

    for j in get_journal_history(patient_username, days):
        events.append({
            "type": "journal",
            "timestamp": j.get("timestamp", ""),
            "title": j.get("title", "Journal Entry"),
            "data": j,
        })

    for f in get_followup_history(patient_username, days):
        events.append({
            "type": "followup",
            "timestamp": f.get("assigned_at", "") or f.get("completed_at", ""),
            "title": f.get("title", "Task"),
            "data": f,
        })

    for c in get_crisis_history(patient_username, days):
        events.append({
            "type": "crisis",
            "timestamp": c.get("timestamp", ""),
            "title": c.get("event", "Crisis event"),
            "data": c,
        })

    events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return events


import streamlit as st


def color_for_mood(label: str) -> str:
    colors = {"great": "#22c55e", "good": "#86efac", "okay": "#fbbf24", "bad": "#fb923c", "awful": "#ef4444", "terrible": "#7f1d1d"}
    return colors.get(label.lower(), "#6a6474")


def icon_for_mood(label: str) -> str:
    icons = {"great": "\U0001f929", "good": "\U0001f60a", "okay": "\U0001f610", "bad": "\U0001f61e", "awful": "\U0001f630", "terrible": "\U0001f4a9"}
    return icons.get(label.lower(), "\u2753")


def format_time(ts_str: str) -> str:
    try:
        dt = datetime.fromisoformat(ts_str)
        return dt.strftime("%b %d, %I:%M %p")
    except Exception:
        return ts_str


def timeline_card_style(event_type: str) -> str:
    borders = {
        "mood": "border-left:3px solid #22c55e;",
        "journal": "border-left:3px solid #6366f1;",
        "followup": "border-left:3px solid #f59e0b;",
        "crisis": "border-left:3px solid #ef4444;",
    }
    return borders.get(event_type, "border-left:3px solid #6a6474;")


def render_timeline(patient: str, days: int = 30):
    st.markdown("### \U0001f4cb Behavioral Timeline")
    st.markdown(
        "<div style='color:#6a6474;font-size:0.8rem;margin-bottom:12px;'>"
        "A unified chronological view of everything affecting this patient — journals, mood, tasks, and crisis events."
        "</div>",
        unsafe_allow_html=True,
    )

    metrics = compute_change_metrics(patient)
    events = get_behavioral_timeline(patient, days)

    col_metrics, col_timeline = st.columns([1, 2])

    with col_metrics:
        _render_metrics_panel(metrics)

    with col_timeline:
        _render_event_feed(events)


def _render_metrics_panel(metrics: dict):
    st.markdown("#### \U0001f4ca Change Metrics")
    st.markdown(
        "<div style='background:#1a1f30;border:1px solid #2a2f40;border-radius:10px;padding:14px;margin-bottom:12px;'>",
        unsafe_allow_html=True,
    )

    trend = metrics.get("mood_trend", "insufficient_data")
    trend_icon = "\u2197\ufe0f improving" if trend == "improving" else "\u2198\ufe0f declining" if trend == "declining" else "\u2192\ufe0f stable" if trend == "stable" else "\u2014"
    trend_color = "#22c55e" if trend == "improving" else "#ef4444" if trend == "declining" else "#fbbf24" if trend == "stable" else "#6a6474"

    st.markdown(
        f"<div style='margin-bottom:10px;'>"
        f"<div style='color:#6a6474;font-size:0.7rem;'>MOOD TREND (7d vs 7-14d ago)</div>"
        f"<div style='color:{trend_color};font-size:1.3rem;font-weight:700;'>{trend_icon}</div>"
        f"<div style='color:#7a8aaa;font-size:0.75rem;'>"
        f"Current avg: {metrics.get('current_mood_avg', 'N/A') and f'{metrics[\"current_mood_avg\"]:.1f}/5'} | "
        f"Previous: {metrics.get('previous_mood_avg', 'N/A') and f'{metrics[\"previous_mood_avg\"]:.1f}/5'}"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    eng = metrics.get("engagement_trend", "none")
    eng_icon = "\u2197\ufe0f" if eng == "increasing" else "\u2198\ufe0f" if eng == "declining" else "\u2192\ufe0f" if eng == "stable" else "\u2014"
    eng_color = "#22c55e" if eng == "increasing" else "#ef4444" if eng == "declining" else "#fbbf24" if eng == "stable" else "#6a6474"

    st.markdown(
        f"<div style='margin-bottom:10px;'>"
        f"<div style='color:#6a6474;font-size:0.7rem;'>ENGAGEMENT (journal entries)</div>"
        f"<div style='color:{eng_color};font-size:1.3rem;font-weight:700;'>{eng_icon}</div>"
        f"<div style='color:#7a8aaa;font-size:0.75rem;'>"
        f"Last 7d: {metrics.get('journal_count_7', 0)} | Last 14d: {metrics.get('journal_count_14', 0)}"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    latest = metrics.get("latest_mood")
    if latest:
        st.markdown(
            f"<div style='margin-bottom:4px;'>"
            f"<div style='color:#6a6474;font-size:0.7rem;'>LATEST MOOD</div>"
            f"<div style='font-size:1.5rem;'>{icon_for_mood(latest.get('label', ''))}</div>"
            f"<div style='color:#7a8aaa;font-size:0.75rem;'>{latest.get('label', '')} — {format_time(latest.get('timestamp', ''))}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


def _render_event_feed(events: list):
    st.markdown("#### \U0001f4c5 Event Feed")

    if not events:
        st.info("No events in the selected time period.")
        return

    container_style = "max-height:500px;overflow-y:auto;padding-right:6px;"
    st.markdown(f"<div style='{container_style}'>", unsafe_allow_html=True)

    for ev in events:
        etype = ev["type"]
        ts = ev.get("timestamp", "")
        border = timeline_card_style(etype)

        if etype == "mood":
            d = ev["data"]
            label = d.get("label", "unknown")
            _render_event_card(
                border,
                f"{icon_for_mood(label)} [{label.upper()}]",
                format_time(ts),
                "",
                f"Mood logged: {label} on {d.get('date', '')}",
            )
        elif etype == "journal":
            d = ev["data"]
            title = d.get("title", "Journal Entry")
            emotions = d.get("emotions", "")
            emo_str = f" \U0001f3f7 {emotions}" if emotions else ""
            _render_event_card(
                border,
                f"\U0001f4dd {title}",
                format_time(ts),
                "AI Summary" if d.get("summary") else "",
                f"{d.get('summary', '')[:200]}{'...' if d.get('summary') and len(d['summary']) > 200 else ''}{emo_str}",
            )
        elif etype == "followup":
            d = ev["data"]
            status = d.get("status", "pending")
            status_icon = "\u2705" if status == "completed" else "\u23f3" if status == "in_progress" else "\u25cb"
            _render_event_card(
                border,
                f"{status_icon} {d.get('title', 'Task')}",
                format_time(d.get("completed_at", "") or d.get("assigned_at", "")),
                status.upper(),
                d.get("description", ""),
            )
        elif etype == "crisis":
            d = ev["data"]
            event_name = d.get("event", "Crisis")
            detail = d.get("details", "")
            _render_event_card(
                border,
                f"\U0001f6a8 {event_name.upper()}",
                format_time(ts),
                "CRISIS",
                detail,
            )

    st.markdown("</div>", unsafe_allow_html=True)


def _render_event_card(border_style: str, title: str, timestamp: str, badge: str, description: str):
    bg = "#111827"
    badge_html = f"<span style='background:#374151;color:#9ca3af;font-size:0.65rem;padding:1px 6px;border-radius:4px;margin-left:6px;'>{badge}</span>" if badge else ""
    st.markdown(
        f"<div style='background:{bg};{border_style}border-radius:6px;padding:8px 12px;margin:4px 0;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
        f"<div><span style='color:#e0e8f0;font-weight:600;font-size:0.85rem;'>{title}</span>{badge_html}</div>"
        f"<span style='color:#6a6474;font-size:0.7rem;'>{timestamp}</span>"
        f"</div>"
        f"<div style='color:#7a8aaa;font-size:0.75rem;margin-top:2px;'>{description[:300]}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_psych_timeline_tab(username: str):
    """Top-level tab for the psychologist view: patient selector + timeline."""
    st.markdown("## \U0001f50d Behavioral Timeline")
    st.markdown(
        "<div style='color:#6a6474;font-size:0.85rem;margin-bottom:16px;'>"
        "Track behavioral evolution across time — not isolated symptoms. "
        "Select a patient to see their unified event feed and change metrics."
        "</div>",
        unsafe_allow_html=True,
    )

    try:
        from psych_triage_ import get_patient_list
        patients = get_patient_list(username) or []
    except Exception:
        patients = []

    if not patients:
        st.info("No patients assigned yet.")
        return

    patient_options = {p.get("patient_username", p.get("username", "")): p for p in patients}
    selected = st.selectbox(
        "Select Patient",
        list(patient_options.keys()),
        format_func=lambda x: patient_options[x].get("patient_name", x) if x in patient_options else x,
        key="timeline_patient_selector",
    )

    if selected:
        days = st.slider("Time range", 7, 90, 30, key="timeline_days")
        render_timeline(selected, days)
