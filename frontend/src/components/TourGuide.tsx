import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'

interface TourStep {
  icon: string
  title: string
  desc: string
  tip: string
  color: string
}

const PATIENT_STEPS: TourStep[] = [
  { icon: '🌿', title: 'Your Wellness Dashboard', desc: 'This is your personal health command center. Each tab is a tool to help you and your psychologist track how you\'re doing.', tip: 'Start with the Wellness tab each day to check your vitals and mood at a glance.', color: 'var(--accent)' },
  { icon: '📝', title: 'Journal', desc: 'Write freely about your thoughts and feelings. An AI analyzes your entry and creates a brief summary for your psychologist to review.', tip: 'Your psychologist sees only the AI summary, not your raw text. Be honest — it helps them help you.', color: '#A66E0C' },
  { icon: '📅', title: 'Booking', desc: 'Request appointments with your assigned psychologist. See their available dates and submit a request.', tip: 'When your psych proposes a slot, check the Psych Suggested tab to accept or decline.', color: 'var(--accent)' },
  { icon: '📋', title: 'Follow-Up', desc: 'Your psychologist may assign tasks between sessions — like mindfulness exercises or mood tracking. Complete them here.', tip: 'Finishing tasks helps your psych see what\'s working. Even a quick check-in counts.', color: 'var(--accent-hover)' },
  { icon: '🚨', title: 'Emergency', desc: 'If you\'re in distress, this tab provides immediate crisis support. It triggers an alert to your psychologist and trusted contact.', tip: 'You can update your trusted contact details in your profile settings at any time.', color: 'var(--danger)' },
  { icon: '💡', title: 'Sidebar Tools', desc: 'The sidebar gives you quick access to your status overview, recent activity, and AI-powered insights.', tip: 'Click your username at the top of the sidebar to edit your profile anytime.', color: 'var(--accent)' },
]

const PSYCH_STEPS: TourStep[] = [
  { icon: '🔮', title: 'Your Command Center', desc: 'This is your clinical cockpit. From here you monitor all your patients, review their wellness data, and manage care.', tip: 'The Patient Triage tab opens first — scan it daily to catch any high-priority patients.', color: 'var(--accent)' },
  { icon: '📋', title: 'Patient Triage', desc: 'A priority-ranked list of all your patients. Scores are computed from crisis status, ring vitals, silent periods, and journal activity.', tip: 'Red/Crisis patients need immediate attention. Amber/High patients should be reviewed within the hour.', color: 'var(--danger)' },
  { icon: '📝', title: 'Clinical Notes', desc: 'Review AI-summarized journal entries from any patient, then write and save structured clinical notes.', tip: 'Use the Journal-to-Note panel: pick a patient, review their latest entry, and click Analyze & Draft.', color: '#2FA05C' },
  { icon: '📓', title: 'Journal & Wellness', desc: 'Your own personal journal space plus live vitals from your ring. Track your own stress, sleep, and heart rate trends.', tip: 'This is your self-care space. Writing your own notes helps you reflect on your day.', color: '#A66E0C' },
  { icon: '📅', title: 'Bookings', desc: 'Set your available dates in the Calendar view so patients know when to book. The Booking Queue shows incoming requests.', tip: 'Toggle dates on the calendar as available/unavailable. Respond to requests quickly.', color: 'var(--accent)' },
  { icon: '📋', title: 'Follow-Up', desc: 'Assign tasks to patients between sessions — mood logs, mindfulness exercises, or custom check-ins.', tip: 'Use the AI side panel to generate a follow-up plan based on the patient\'s latest journal entry.', color: 'var(--accent-hover)' },
  { icon: '📦', title: 'Export Center', desc: 'Download patient data, journal summaries, and clinical notes as CSV for your records or external reporting.', tip: 'Exports include only AI summaries — no raw journal text leaves the system.', color: 'var(--muted)' },
]

export default function TourGuide({ role }: { role: string }) {
  const [step, setStep] = useState(0)
  const [active, setActive] = useState(false)
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    const localDone = localStorage.getItem('sentinel_tour_done')
    if (localDone) { setChecking(false); return }
    api.get('/patients/me').then((d: any) => {
      if (d.onboarding_step >= 100) {
        localStorage.setItem('sentinel_tour_done', '1')
      } else {
        setActive(true)
      }
    }).catch(() => {
      setActive(true)
    }).finally(() => setChecking(false))
  }, [])

  async function completeTour() {
    localStorage.setItem('sentinel_tour_done', '1')
    try { await api.updateOnboarding(100) } catch {}
    setActive(false)
  }

  const steps = role === 'Psychologist' ? PSYCH_STEPS : PATIENT_STEPS
  const s = steps[step]
  if (checking || !active || !s) return null

  function next() {
    if (step >= steps.length - 1) {
      completeTour()
    } else {
      setStep(step + 1)
    }
  }

  function skip() {
    completeTour()
  }

  return (
    <div style={{
      position: 'fixed', bottom: '24px', right: '24px', zIndex: 9999,
      width: '380px', maxWidth: 'calc(100vw - 48px)',
      background: 'var(--surface)', border: `1px solid ${s.color}40`,
      borderRadius: '16px', padding: '24px',
      boxShadow: '0 8px 32px rgba(23,53,45,0.18)',
    }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px' }}>
        <div style={{ fontSize: '2.5rem', lineHeight: 1 }}>{s.icon}</div>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span style={{ color: s.color, fontSize: '0.6875rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Tour {step + 1} of {steps.length}
            </span>
          </div>
          <div style={{ color: 'var(--heading)', fontSize: '1rem', fontWeight: 600, margin: '4px 0 8px' }}>{s.title}</div>
          <div style={{ color: 'var(--text)', fontSize: '0.8125rem', lineHeight: 1.6 }}>{s.desc}</div>
          <div style={{ marginTop: '10px', padding: '8px 12px', background: `${s.color}10`, borderLeft: `3px solid ${s.color}`, borderRadius: '4px', color: 'var(--label)', fontSize: '0.75rem', lineHeight: 1.5 }}>
            💡 <strong>Pro Tip:</strong> {s.tip}
          </div>
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '16px' }}>
        <div style={{ display: 'flex', gap: '4px', flex: 1 }}>
          {steps.map((st, i) => (
            <div key={i} style={{
              height: '6px', borderRadius: '3px', flex: 1,
              background: i === step ? s.color : i < step ? 'var(--faint)' : 'var(--border)',
              transform: i === step ? 'scaleY(1.6)' : 'none',
              transition: 'all 0.3s ease',
            }} />
          ))}
        </div>
      </div>
      <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
        {step > 0 && (
          <button onClick={() => setStep(step - 1)}
            style={{ flex: 1, padding: '8px', fontSize: '0.8125rem', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--secondary)', cursor: 'pointer' }}>
            ← Back
          </button>
        )}
        <button onClick={next}
          style={{ flex: 1, padding: '8px', fontSize: '0.8125rem', background: 'var(--accent)', border: 'none', borderRadius: '8px', color: 'var(--on-accent)', fontWeight: 600, cursor: 'pointer' }}>
          {step === steps.length - 1 ? '✅ Got it!' : 'Next →'}
        </button>
        <button onClick={skip}
          style={{ padding: '8px 12px', fontSize: '0.75rem', background: 'transparent', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--faint)', cursor: 'pointer' }}>
          ✕
        </button>
      </div>
    </div>
  )
}
