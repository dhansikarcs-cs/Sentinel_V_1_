import streamlit as st

try:
    from data_manager_ import get_activity_feed
except Exception:
    get_activity_feed = None

try:
    from patient_shared_ import safe
except Exception:
    safe = None


def render_activity_feed(actor: str = "", limit: int = 20):
    rows = safe(get_activity_feed, [], actor, limit)
    if not rows:
        st.caption("No recent activity.")
        return

    for r in rows:
        action = r["action"]
        target = r["target"] or ""
        detail = r["detail"] or ""
        ts = r["timestamp"][:16] if len(r["timestamp"]) > 16 else r["timestamp"]

        icons = {
            "journal_entry": "\U0001f4dd",
            "clinical_note": "\U0001f4cb",
            "booking_created": "\U0001f4c5",
            "booking_status": "\U0001f504",
            "followup_created": "\U0001f4cb",
            "crisis": "\U0001f6a8",
            "crisis_resolved": "\u2705",
        }
        icon = icons.get(action, "\U0001f4ac")

        label = action.replace("_", " ").title()
        extra = f" \u2192 {detail}" if detail else ""
        target_tag = f'<span style="color:#60a5fa;font-size:0.6875rem;">{target}</span>' if target else ""

        st.markdown(
            f"<div style='display:flex;align-items:center;gap:8px;padding:4px 0;border-bottom:1px solid #1e2940;'>"
            f"<span style='font-size:0.875rem;'>{icon}</span>"
            f"<span style='color:#7a8aaa;font-size:0.6875rem;'>{ts}</span>"
            f"<span style='color:#c0d0e0;font-size:0.75rem;font-weight:500;'>{label}</span>"
            f"{target_tag}"
            f"<span style='color:#5a6a8a;font-size:0.6875rem;margin-left:auto;'>{extra}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
