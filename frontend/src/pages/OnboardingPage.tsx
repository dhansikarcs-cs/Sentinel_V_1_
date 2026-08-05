import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getUser } from '../stores/auth'
import { api } from '../api/client'

const STEPS = [
  { emoji: '\u{1F3E0}', label: 'About You' },
  { emoji: '\u{1F4DD}', label: 'First Entry' },
  { emoji: '\u{1F6E1}\uFE0F', label: 'Emergency' },
  { emoji: '\u{1F4F1}', label: 'Contact' },
]

export default function OnboardingPage() {
  const navigate = useNavigate()
  const user = getUser()
  const [step, setStep] = useState(0)
  const [journal, setJournal] = useState('')
  const [trustedContact, setTrustedContact] = useState('')
  const [contactInfo, setContactInfo] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api.getMe().then((d: any) => {
      if (d.onboarding_step >= 99) { navigate('/dashboard'); return }
      setStep(d.onboarding_step || 0)
      setTrustedContact(d.trusted_contact || '')
      setContactInfo(d.contact_info || '')
    }).catch(() => {})
  }, [])

  async function goTo(s: number) {
    if (s < 0 || s > 4) return
    if (s > step) {
      try { await api.updateOnboarding(s) } catch {}
    }
    setStep(s)
  }

  async function handleJournal() {
    if (!journal.trim()) return
    setSaving(true)
    try { await api.createJournal(journal.trim()) } catch {}
    setSaving(false)
    goTo(2)
  }

  async function handleContact() {
    try {
      await api.updateContact({ contact_info: contactInfo, trusted_contact: trustedContact })
    } catch {}
    goTo(4)
  }

  async function saveTrustedAndNext() {
    if (trustedContact.trim()) {
      try { await api.updateContact({ contact_info: contactInfo, trusted_contact: trustedContact }) } catch {}
    }
    goTo(3)
  }

  async function finish() {
    try { await api.updateOnboarding(99) } catch {}
    navigate('/dashboard')
  }

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ padding: '32px' }}>
      <div style={{ width: '100%', maxWidth: '560px' }}>
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div style={{ fontSize: '2rem', fontWeight: 700, background: 'linear-gradient(135deg,#8fcbb1,#a9e0c6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', letterSpacing: '-0.02em' }}>
            Welcome to Sentinel
          </div>
          <div style={{ color: '#7d877e', fontSize: '0.85rem', marginTop: '4px' }}>Let's get you set up in a few quick steps</div>
        </div>

        {/* Clickable step indicators */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', marginBottom: '24px' }}>
          {STEPS.map((s, i) => {
            const done = i < step
            const active = i === step
            const bg = done ? '#1a3a2a' : active ? '#2a2040' : '#1d2623'
            const border = done ? '#22c55e40' : active ? '#8fcbb160' : '#31423a'
            const color = done ? '#22c55e' : active ? '#8fcbb1' : '#6b766d'
            const icon = done ? '\u2705' : s.emoji
            return (
              <div
                key={i}
                onClick={() => i <= step && goTo(i)}
                style={{
                  background: bg, border: `1px solid ${border}`, borderRadius: '8px',
                  padding: '10px 6px', textAlign: 'center', transition: 'all 0.3s',
                  cursor: i <= step ? 'pointer' : 'default',
                  opacity: i > step ? 0.5 : 1,
                }}
              >
                <div style={{ fontSize: '1.2rem' }}>{icon}</div>
                <div style={{ color, fontSize: '0.65rem', fontWeight: active || done ? 600 : 400, marginTop: '2px' }}>{s.label}</div>
              </div>
            )
          })}
        </div>

        {/* Progress bar */}
        <div style={{ height: '3px', background: '#1d2623', borderRadius: '2px', marginBottom: '20px', overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${((step + 1) / 4) * 100}%`, background: 'linear-gradient(90deg, #22c55e, #8fcbb1)', borderRadius: '2px', transition: 'width 0.4s ease' }} />
        </div>

        {/* Step content */}
        <div className="card" style={{ padding: '28px', minHeight: '280px' }}>

          {/* Step 0: About You */}
          {step === 0 && (
            <div>
              <h3>🏠 About You</h3>
              <div style={{ background: 'linear-gradient(135deg,#1d2623,#1e2a45)', border: '1px solid #31423a', borderRadius: '12px', padding: '20px', margin: '12px 0' }}>
                <div style={{ color: '#7d877e', fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Your Account</div>
                <div style={{ color: '#e0e8f0', fontSize: '1.1rem', fontWeight: 600, marginTop: '4px' }}>{user?.name || user?.username}</div>
                <div style={{ color: '#7d877e', fontSize: '0.75rem', marginTop: '8px', lineHeight: 1.5 }}>
                  You're registered with Sentinel. Your psychologist will review your journals and vitals to support your well-being.
                </div>
              </div>
              <button className="btn-primary btn-full" onClick={() => goTo(1)}>Next Step →</button>
            </div>
          )}

          {/* Step 1: First Journal */}
          {step === 1 && (
            <div>
              <h3>📝 Your First Journal Entry</h3>
              <p style={{ color: '#7d877e', fontSize: '0.8rem', marginBottom: '12px' }}>
                Write a few lines about how you're feeling. Your psychologist will see an AI summary.
              </p>
              <textarea
                value={journal} onChange={e => setJournal(e.target.value)}
                placeholder="How are you feeling right now?"
                rows={5}
                style={{ width: '100%', padding: '12px', fontSize: '0.875rem', resize: 'none', marginBottom: '12px' }}
              />
              <div style={{ display: 'flex', gap: '8px' }}>
                <button className="btn-primary" onClick={handleJournal} disabled={saving || !journal.trim()} style={{ flex: 1 }}>
                  {saving ? 'Saving...' : 'Save & Continue'}
                </button>
                <button onClick={() => goTo(2)} style={{ flex: 1 }}>Skip for now</button>
              </div>
              <div style={{ marginTop: '8px' }}>
                <button onClick={() => goTo(0)} style={{ background: 'none', border: 'none', color: '#7d877e', cursor: 'pointer', fontSize: '0.75rem' }}>← Back</button>
              </div>
            </div>
          )}

          {/* Step 2: Emergency Contact */}
          {step === 2 && (
            <div>
              <h3>🛡️ Emergency Contact</h3>
              <p style={{ color: '#7d877e', fontSize: '0.8rem', marginBottom: '12px' }}>
                If you trigger a crisis alert, your trusted contact will be notified.
              </p>
              <input
                value={trustedContact} onChange={e => setTrustedContact(e.target.value)}
                placeholder="Trusted contact email or phone"
                style={{ width: '100%', padding: '10px 12px', fontSize: '0.875rem', marginBottom: '12px' }}
              />
              <div style={{ display: 'flex', gap: '8px' }}>
                <button className="btn-primary" onClick={saveTrustedAndNext} style={{ flex: 1 }}>Save →</button>
                <button onClick={() => goTo(3)} style={{ flex: 1 }}>Skip</button>
              </div>
              <div style={{ marginTop: '8px' }}>
                <button onClick={() => goTo(1)} style={{ background: 'none', border: 'none', color: '#7d877e', cursor: 'pointer', fontSize: '0.75rem' }}>← Back</button>
              </div>
            </div>
          )}

          {/* Step 3: Contact Preference */}
          {step === 3 && (
            <div>
              <h3>📱 Contact Preference</h3>
              <p style={{ color: '#7d877e', fontSize: '0.8rem', marginBottom: '12px' }}>
                How should your psychologist reach you?
              </p>
              <input
                value={contactInfo} onChange={e => setContactInfo(e.target.value)}
                placeholder="Mobile number or email"
                style={{ width: '100%', padding: '10px 12px', fontSize: '0.875rem', marginBottom: '12px' }}
              />
              <div style={{ display: 'flex', gap: '8px' }}>
                <button className="btn-primary" onClick={handleContact} style={{ flex: 1 }}>Save →</button>
                <button onClick={() => goTo(4)} style={{ flex: 1 }}>Skip</button>
              </div>
              <div style={{ marginTop: '8px' }}>
                <button onClick={() => goTo(2)} style={{ background: 'none', border: 'none', color: '#7d877e', cursor: 'pointer', fontSize: '0.75rem' }}>← Back</button>
              </div>
            </div>
          )}

          {/* Step 4: Done */}
          {step >= 4 && (
            <div style={{ background: 'linear-gradient(135deg,#19211e,#1a3a2a)', border: '1px solid rgba(34,197,94,0.25)', borderRadius: '16px', padding: '32px', textAlign: 'center' }}>
              <div style={{ fontSize: '3rem', marginBottom: '8px' }}>✅</div>
              <div style={{ color: '#22c55e', fontSize: '1.5rem', fontWeight: 700 }}>You're all set!</div>
              <div style={{ color: '#7d877e', fontSize: '0.85rem', marginTop: '8px', lineHeight: 1.6 }}>
                Your dashboard is ready. Track your wellness, write journal entries, manage bookings, and more.
              </div>
              <div style={{ display: 'flex', gap: '8px', marginTop: '20px' }}>
                <button onClick={() => goTo(3)} style={{ flex: 1, padding: '10px', background: '#1d2623', border: '1px solid #31423a', borderRadius: '8px', color: '#7d877e', cursor: 'pointer' }}>← Back</button>
                <button className="btn-primary" onClick={finish} style={{ flex: 2, padding: '12px', fontSize: '1rem' }}>🚀 Open Dashboard</button>
              </div>
            </div>
          )}
        </div>

        {/* Bottom nav hint */}
        <div style={{ textAlign: 'center', marginTop: '12px', color: '#6b766d', fontSize: '0.7rem' }}>
          Click any completed step above to go back
        </div>
      </div>
    </div>
  )
}
