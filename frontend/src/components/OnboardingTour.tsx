import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { api } from '../api/client'

interface TourStep {
  key: string
  to: string
  title: string
  desc: string
  tip: string
  icon: string
  color: string
}

const PATIENT_STEPS: TourStep[] = [
  { key: 'dashboard', to: '/dashboard', icon: '🌿', title: 'Your Wellness Dashboard', desc: 'Your daily check-in. Log your mood, see your weekly trend, and review AI insights — all in one place.', tip: 'Log your mood daily; even a quick tap on an emoji helps your psychologist.', color: 'var(--accent)' },
  { key: 'journal', to: '/journal', icon: '📝', title: 'Journal', desc: 'Write freely about your thoughts. An AI analyzes each entry and creates a short summary your psychologist can review.', tip: 'Your psychologist only sees the AI summary — never your raw text. Be honest.', color: '#A66E0C' },
  { key: 'bookings', to: '/bookings', icon: '📅', title: 'Booking', desc: 'Request appointments with your psychologist, or accept a slot they suggest for you. Use the tabs to switch between suggestions and new requests.', tip: 'When your psych proposes a slot, accept or decline it under "Psych Suggested".', color: 'var(--accent)' },
  { key: 'followups', to: '/followups', icon: '📋', title: 'Follow-Up', desc: 'Tasks your psychologist assigns between sessions — mindfulness exercises, mood logs, or custom check-ins.', tip: 'Completing tasks helps your psych see what is working for you.', color: 'var(--accent-hover)' },
  { key: 'timeline', to: '/timeline', icon: '🔍', title: 'Timeline', desc: 'A chronological view of your activity — journals, moods, bookings, and follow-ups — so you can spot your progress over time.', tip: 'Scroll back to reflect on how far you have come.', color: 'var(--accent)' },
  { key: 'crisis', to: '/crisis', icon: '🚨', title: 'Emergency', desc: 'If you are ever in distress, this tab connects you to immediate help — your psychologist, trusted contact, and helplines by email or phone.', tip: 'In immediate danger call your local emergency number first. These buttons also work offline.', color: 'var(--danger)' },
  { key: 'profile', to: '/profile', icon: '👤', title: 'My Profile', desc: 'Update your details, password, and — most importantly — who to contact in an emergency.', tip: 'Keep your trusted contact email current; it powers your crisis alerts.', color: 'var(--accent)' },
]

const PSYCH_STEPS: TourStep[] = [
  { key: 'triage', to: '/triage', icon: '📋', title: 'Patient Triage', desc: 'A priority-ranked list of every patient. Scores combine crisis status, journal activity, silent periods, and engagement.', tip: 'Review Crisis patients first, then High — daily.', color: 'var(--danger)' },
  { key: 'session', to: '/open-session', icon: '🧑‍⚕️', title: 'Open Session', desc: 'Your consultation workspace — patient overview, mood and risk snapshots, clinical brief, notes, and follow-up planning.', tip: 'Use "Generate AI Draft" to kick-start a session note.', color: 'var(--accent)' },
  { key: 'clinical-notes', to: '/clinical-notes', icon: '📝', title: 'Clinical Notes', desc: 'Review AI-summarized journal entries from any patient and write structured clinical notes for your records.', tip: 'The Journal-to-Note panel turns an entry into a draft in one click.', color: '#2FA05C' },
  { key: 'patient-insights', to: '/patient-insights', icon: '📊', title: 'Patient Insights', desc: 'A deep-dive per patient — risk snapshot, mood and engagement trends, emotions, and AI reasoning traces.', tip: 'The Current State card is your first look at a patient risk.', color: 'var(--accent)' },
  { key: 'psych-journal', to: '/psych-journal', icon: '📓', title: 'Journal & Wellness', desc: 'Your own private journal space for reflections and self-care check-ins.', tip: 'This space is for you — write freely about your day.', color: '#A66E0C' },
  { key: 'psych-bookings', to: '/bookings', icon: '📅', title: 'Bookings', desc: 'Set your available dates on the calendar and approve or decline incoming patient requests.', tip: 'Keep your calendar updated so patients can book you.', color: 'var(--accent)' },
  { key: 'psych-followups', to: '/followups', icon: '📋', title: 'Follow-Up', desc: 'Assign tasks to patients between sessions and grade their completion.', tip: 'Use the AI side panel to generate a follow-up plan from a journal entry.', color: 'var(--accent-hover)' },
  { key: 'export', to: '/export', icon: '📦', title: 'Export Center', desc: 'Download patient data, journal summaries, and clinical notes as CSV for your records or reporting.', tip: 'Exports include only AI summaries — raw journal text never leaves the system.', color: 'var(--muted)' },
]

const CARD_W = 360

export default function OnboardingTour({ role }: { role: string }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [active, setActive] = useState(false)
  const [stepIdx, setStepIdx] = useState(0)

  const steps = role === 'Psychologist' ? PSYCH_STEPS : PATIENT_STEPS
  const step = steps[stepIdx]

  useEffect(() => {
    if (localStorage.getItem('sentinel_tour_done')) return
    let cancelled = false
    api.get('/patients/me').then((d: any) => {
      if (cancelled) return
      if (d && d.onboarding_step >= 100) {
        localStorage.setItem('sentinel_tour_done', '1')
        return
      }
      setActive(true)
    }).catch(() => { setActive(true) })
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    if (!active || !step) return
    if (location.pathname !== step.to) navigate(step.to)
  }, [active, stepIdx, location.pathname, navigate, step])

  if (!active || !step) return null

  function complete() {
    localStorage.setItem('sentinel_tour_done', '1')
    try { api.updateOnboarding(100) } catch {}
    setActive(false)
  }
  function next() {
    if (stepIdx >= steps.length - 1) { complete(); return }
    setStepIdx(stepIdx + 1)
  }
  function back() {
    if (stepIdx === 0) return
    setStepIdx(stepIdx - 1)
  }

  const maxW = Math.min(CARD_W, window.innerWidth - 32)

  return (
    <div aria-hidden="false" role="dialog" aria-label="Guided tour">
      <div
        style={{
          position: 'fixed', zIndex: 9992, width: maxW,
          top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
          background: 'var(--surface)', border: `1px solid ${step.color}55`,
          borderRadius: '16px', padding: '20px', boxSizing: 'border-box',
          boxShadow: '0 12px 40px rgba(0,0,0,0.35)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
          <div style={{ fontSize: '2rem', lineHeight: 1 }}>{step.icon}</div>
          <div style={{ flex: 1 }}>
            <div style={{ color: step.color, fontSize: '0.6875rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              {stepIdx + 1} of {steps.length}
            </div>
            <div style={{ color: 'var(--heading)', fontSize: '1rem', fontWeight: 600, margin: '4px 0 8px' }}>{step.title}</div>
          </div>
        </div>
        <div style={{ color: 'var(--text)', fontSize: '0.8125rem', lineHeight: 1.6 }}>{step.desc}</div>
        <div style={{ marginTop: '10px', padding: '8px 12px', background: `${step.color}10`, borderLeft: `3px solid ${step.color}`, borderRadius: '4px', color: 'var(--label)', fontSize: '0.75rem', lineHeight: 1.5 }}>
          💡 <strong>Pro Tip:</strong> {step.tip}
        </div>
        <div style={{ display: 'flex', gap: '8px', marginTop: '14px' }}>
          {stepIdx > 0 && (
            <button onClick={back}
              style={{ padding: '8px 14px', fontSize: '0.8125rem', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--secondary)', cursor: 'pointer' }}>
              ← Back
            </button>
          )}
          <button onClick={next}
            style={{ marginLeft: 'auto', padding: '8px 18px', fontSize: '0.8125rem', background: 'var(--accent)', border: 'none', borderRadius: '8px', color: 'var(--on-accent)', fontWeight: 600, cursor: 'pointer' }}>
            {stepIdx === steps.length - 1 ? '✅ Got it!' : 'Next →'}
          </button>
          <button onClick={complete}
            style={{ padding: '8px 12px', fontSize: '0.75rem', background: 'transparent', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--faint)', cursor: 'pointer' }}>
            ✕
          </button>
        </div>
      </div>
    </div>
  )
}