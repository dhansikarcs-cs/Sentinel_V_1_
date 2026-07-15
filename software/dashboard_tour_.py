import streamlit as st

try:
    from patient_profiles_ import get_onboarding_step, set_onboarding_step
except Exception:
    get_onboarding_step = set_onboarding_step = None

try:
    from psych_shared_ import safe
except Exception:
    safe = None


# Tour steps WITHOUT Smart Room
_PATIENT_STEPS = [
    {"icon": "\U0001f33f", "title": "Your Wellness Dashboard",
     "desc": "This is your personal health command center. Each tab is a tool to help you and your psychologist track how you're doing.",
     "tip": "Start with the Wellness tab each day to check your vitals and mood at a glance.",
     "color": "#c49ea4"},
    {"icon": "\U0001f4ca", "title": "Wellness Overview",
     "desc": "See your heart rate, stress levels, sleep, SpO\u2082, and mood from your ring. Charts show 7-day trends so you spot patterns early.",
     "tip": "Your ring syncs automatically. Check this tab daily \u2014 it gives your psychologist a window into your week.",
     "color": "#4ade80"},
    {"icon": "\U0001f4dd", "title": "Journal",
     "desc": "Write freely about your thoughts and feelings. An AI analyzes your entry and creates a brief summary for your psychologist to review.",
     "tip": "Your psychologist sees only the AI summary, not your raw text. Be honest \u2014 it helps them help you.",
     "color": "#fbbf24"},
    {"icon": "\U0001f4c5", "title": "Booking",
     "desc": "Request appointments with your assigned psychologist. See their available dates and submit a request.",
     "tip": "When your psych proposes a slot, check the Psych Suggested sub-tab to accept or decline.",
     "color": "#c49ea4"},
    {"icon": "\U0001f4cb", "title": "Follow-Up",
     "desc": "Your psychologist may assign tasks between sessions \u2014 like mindfulness exercises or mood tracking. Complete them here.",
     "tip": "Finishing tasks helps your psych see what's working. Even a quick check-in counts.",
     "color": "#d8b4ba"},
    {"icon": "\U0001f6ae", "title": "Emergency",
     "desc": "If you're in distress, this tab provides immediate crisis support. It triggers an alert to your psychologist and trusted contact.",
     "tip": "You can update your trusted contact details in your profile settings at any time.",
     "color": "#ef4444"},
    {"icon": "\U0001f4e1", "title": "Sidebar Tools",
     "desc": "The sidebar on the left gives you quick access to your status overview, profile settings, recent activity, and AI-powered insights from your psychologist.",
     "tip": "Click your username at the top of the sidebar to edit your profile, contact info, and trusted contact anytime.",
     "color": "#c49ea4"},
    {"icon": "\U0001f504", "title": "Booking Flow",
     "desc": "In the Booking tab, select your psychologist, then pick an available date highlighted in green. Fill in session details and submit your request.",
     "tip": "When your psych proposes a slot, it appears in the Psych Suggested sub-tab. You can accept or decline there.",
     "color": "#34d399"},
]

_PSYCH_STEPS = [
    {"icon": "\U0001f52e", "title": "Your Command Center",
     "desc": "This is your clinical cockpit. From here you monitor all your patients, review their wellness data, and manage care.",
     "tip": "The Patient Triage tab opens first \u2014 scan it daily to catch any high-priority patients.",
     "color": "#c49ea4"},
    {"icon": "\U0001f4ca", "title": "Patient Triage",
     "desc": "A priority-ranked list of all your patients. Scores are computed from crisis status, ring vitals, silent periods, and journal activity.",
     "tip": "Red/Crisis patients need immediate attention. Amber/High patients should be reviewed within the hour.",
     "color": "#ef4444"},
    {"icon": "\U0001f4dd", "title": "Clinical Notes",
     "desc": "Review AI-summarized journal entries from any patient, then write and save structured clinical notes. The AI can even draft a note for you.",
     "tip": "Use the Journal-to-Note panel: pick a patient, review their latest entry, and click 'Analyze & Draft Clinical Note'.",
     "color": "#4ade80"},
    {"icon": "\U0001f4d3", "title": "Journal & Wellness",
     "desc": "Your own personal journal space plus live vitals from your ring. Track your own stress, sleep, and heart rate trends over 7 days.",
     "tip": "This is your self-care space. Writing your own notes helps you reflect on your day, just like your patients do.",
     "color": "#fbbf24"},
    {"icon": "\U0001f4c5", "title": "Bookings",
     "desc": "Set your available dates in the Calendar view so patients know when to book. The Booking Queue shows incoming requests.",
     "tip": "Toggle dates on the calendar as available/unavailable. Respond to requests in the Queue tab quickly.",
     "color": "#c49ea4"},
    {"icon": "\U0001f4cb", "title": "Follow-Up",
     "desc": "Assign tasks to patients between sessions \u2014 mood logs, mindfulness exercises, or custom check-ins. Track completion and grade responses.",
     "tip": "Use the AI side panel to generate a follow-up plan based on the patient's latest journal entry.",
     "color": "#d8b4ba"},
    {"icon": "\U0001f4e6", "title": "Export Center",
     "desc": "Download patient data, journal summaries, and clinical notes as CSV for your records or external reporting.",
     "tip": "Exports include only AI summaries \u2014 no raw journal text leaves the system.",
     "color": "#6a6474"},
    {"icon": "\U0001f4e1", "title": "Sidebar Insights",
     "desc": "The sidebar on the left shows your status overview, a Recent Activity log, and AI Insights \u2014 briefs, patterns, and monitors for all your patients.",
     "tip": "AI Insights refresh every 2 minutes. Review Briefs before each session for a quick patient update.",
     "color": "#c49ea4"},
    {"icon": "\U0001f464", "title": "Profile & Availability",
     "desc": "Click your username at the top of the sidebar to edit your profile, contact info, and trusted contact. Manage your available dates in the Bookings tab.",
     "tip": "Setting your availability early helps patients book with confidence \u2014 and reduces back-and-forth messages.",
     "color": "#34d399"},
]

# Maps tour step index to tab name
_PATIENT_TAB_MAP = ["\U0001f4ca Wellness", "\U0001f4ca Wellness", "\U0001f4dd Journal", "\U0001f4c5 Booking", "\U0001f4cb Follow-Up", "\U0001f6ae Emergency", "", ""]
_PSYCH_TAB_MAP = ["\U0001f4cb Patient Triage", "\U0001f4cb Patient Triage", "\U0001f4dd Clinical Notes", "\U0001f4d3 Journal & Wellness", "\U0001f4c5 Bookings", "\U0001f4cb Follow-Up", "\U0001f4e6 Export Center", "", ""]

_PULSE_CSS = """
<style>
@keyframes tourSlideIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes tourGlow {
  0%, 100% { border-color: rgba(96,165,250,0.3); }
  50% { border-color: rgba(96,165,250,0.7); }
}
.tour-card {
  animation: tourSlideIn 0.4s ease-out, tourGlow 2s ease-in-out infinite;
  border-radius: 16px;
  padding: 24px;
  margin: 12px 0 20px 0;
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(96,165,250,0.3);
}
.tour-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: linear-gradient(135deg, rgba(96,165,250,0.06) 0%, transparent 50%);
  pointer-events: none;
}
.tour-dot {
  height: 6px; border-radius: 3px; flex: 1;
  transition: all 0.3s ease;
}
</style>
"""


def render_dashboard_tour(role: str) -> str:
    """Render the tour card and return the name of the tab to highlight, or empty string if no tour."""
    username = st.session_state.username
    db_step = safe(get_onboarding_step, 0, username)

    if db_step != 99:
        return ""

    if st.session_state.get("dashboard_tour_done", False):
        return ""

    # Check DB-persisted tour state (onboarding_step = 100 means tour done)
    if db_step >= 100:
        st.session_state.dashboard_tour_done = True
        return ""

    steps = _PATIENT_STEPS if role == "Patient" else _PSYCH_STEPS
    tab_map = _PATIENT_TAB_MAP if role == "Patient" else _PSYCH_TAB_MAP
    step = st.session_state.get("dashboard_tour_step", 0)

    if step >= len(steps):
        st.session_state.dashboard_tour_done = True
        safe(set_onboarding_step, None, username, 100)
        return ""

    st.markdown(_PULSE_CSS, unsafe_allow_html=True)

    s = steps[step]

    dot_html = "".join(
        f"<div class='tour-dot' style='background:{s['color'] if i == step else ('#3a4a5a' if i < step else '#2d2d44')};"
        f"{'transform:scaleY(1.6);' if i == step else ''}'></div>"
        for i in range(len(steps))
    )

    st.markdown(
        f"<div class='tour-card' style='border-color:{s['color']}40;background:#0f1729;'>"
        f"<div style='display:flex;align-items:flex-start;gap:16px;'>"
        f"<div style='font-size:2.5rem;line-height:1;'>{s['icon']}</div>"
        f"<div style='flex:1;'>"
        f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:4px;'>"
        f"<span style='color:{s['color']};font-size:0.6875rem;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;'>"
        f"Tour {step + 1} of {len(steps)}</span>"
        f"<span style='color:#3a4a5a;font-size:0.6875rem;'>\u2014</span>"
        f"<span style='color:#6a6474;font-size:0.6875rem;'>{s['title']}</span>"
        f"</div>"
        f"<div style='color:#e8f0ff;font-size:1rem;font-weight:600;line-height:1.4;margin:4px 0 8px;'>{s['title']}</div>"
        f"<div style='color:#9a92a2;font-size:0.8125rem;line-height:1.6;'>{s['desc']}</div>"
        f"<div style='margin-top:10px;padding:8px 12px;background:{s['color']}10;border-left:3px solid {s['color']};"
        f"border-radius:4px;color:#b0c0d8;font-size:0.75rem;line-height:1.5;'>"
        f"\U0001f4a1 <strong>Pro Tip:</strong> {s['tip']}</div>"
        f"</div></div>"
        f"<div style='display:flex;align-items:center;justify-content:space-between;margin-top:16px;'>"
        f"<div class='tour-progress' style='flex:1;margin-right:16px;'>{dot_html}</div>"
        f"</div></div>",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns([1, 1, 4])
    with c1:
        if step > 0:
            if st.button("\u2190 Back", key="tour_back", use_container_width=True):
                st.session_state.dashboard_tour_step = step - 1
                st.rerun()
    with c2:
        lbl = "\u2705 Got it!" if step == len(steps) - 1 else "Next \u2192"
        if st.button(lbl, key="tour_next", type="primary", use_container_width=True):
            if step == len(steps) - 1:
                st.session_state.dashboard_tour_done = True
                safe(set_onboarding_step, None, username, 100)
            else:
                st.session_state.dashboard_tour_step = step + 1
            st.rerun()
    with c3:
        if st.button("Skip tour", key="tour_skip", help="Dismiss this tour"):
            st.session_state.dashboard_tour_done = True
            safe(set_onboarding_step, None, username, 100)
            st.rerun()

    # Return the tab name to highlight
    return tab_map[step]
