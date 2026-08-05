import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getUser, fetchMe } from '../stores/auth'
import { api } from '../api/client'

const STEPS = [
  { emoji: '\u{1F3E0}', label: 'Your Profile' },
  { emoji: '\u{1F4DE}', label: 'Contact' },
  { emoji: '\u{1F465}', label: 'Trusted Contact' },
  { emoji: '\u{1F52E}', label: 'Quick Tips' },
  { emoji: '\u{2705}', label: 'Complete' },
]

export default function PsychOnboardingPage() {
  const navigate = useNavigate()
  const user = getUser()
  const [step, setStep] = useState(0)
  const [contactInfo, setContactInfo] = useState('')
  const [trustedContact, setTrustedContact] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api.getMe().then((d: any) => {
      if (d.onboarding_step >= 99) navigate('/triage')
      setStep(d.onboarding_step || 0)
      setContactInfo(d.contact_info || '')
      setTrustedContact(d.psych_trusted_contact || '')
    }).catch(() => {})
  }, [])

  async function advance(s: number) {
    try { await api.updateOnboarding(s) } catch {}
    setStep(s)
  }

  async function handleSaveContact() {
    setSaving(true)
    try {
      await api.updateContact({ contact_info: contactInfo, trusted_contact: '' })
    } catch {}
    setSaving(false)
    advance(2)
  }

  async function handleSaveTrusted() {
    setSaving(true)
    try {
      await api.updateContact({ contact_info: contactInfo, trusted_contact: trustedContact })
    } catch {}
    setSaving(false)
    advance(3)
  }

  async function finish() {
    try { await api.updateOnboarding(99) } catch {}
    await fetchMe()
    navigate('/triage')
  }

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ padding: '32px' }}>
      <div style={{ width: '100%', maxWidth: '560px' }}>
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div style={{ fontSize: '2rem', fontWeight: 700, background: 'linear-gradient(135deg,#8fcbb1,#a9e0c6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', letterSpacing: '-0.02em' }}>
            Welcome to Sentinel
          </div>
          <div style={{ color: '#7d877e', fontSize: '0.85rem', marginTop: '4px' }}>Set up your psychologist workspace</div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '8px', marginBottom: '24px' }}>
          {STEPS.map((s, i) => {
            const done = i < step
            const active = i === step
            const bg = done ? '#1a3a2a' : active ? '#2a2040' : '#1d2623'
            const border = done ? '#22c55e40' : active ? '#8fcbb160' : '#31423a'
            const color = done ? '#22c55e' : active ? '#8fcbb1' : '#6b766d'
            const icon = done ? '\u2705' : s.emoji
            return (
              <div key={i} style={{ background: bg, border: `1px solid ${border}`, borderRadius: '8px', padding: '10px 4px', textAlign: 'center', transition: 'all 0.3s' }}>
                <div style={{ fontSize: '1.2rem' }}>{icon}</div>
                <div style={{ color, fontSize: '0.6rem', fontWeight: active || done ? 600 : 400, marginTop: '2px' }}>{s.label}</div>
              </div>
            )
          })}
        </div>

        <div className="card" style={{ padding: '28px' }}>
          {step === 0 && (
            <div>
              <h3>🏠 Your Profile</h3>
              <div style={{ background: 'linear-gradient(135deg,#1d2623,#1e2a45)', border: '1px solid #31423a', borderRadius: '12px', padding: '20px', margin: '12px 0' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  {[
                    { label: 'Name', value: user?.name || user?.username },
                    { label: 'Clinic', value: user?.clinic || 'Not assigned' },
                    { label: 'Username', value: user?.username },
                    { label: 'Role', value: 'Psychologist' },
                  ].map(f => (
                    <div key={f.label}>
                      <div style={{ color: '#7d877e', fontSize: '0.75rem' }}>{f.label}</div>
                      <div style={{ color: '#bac9bf', fontSize: '1rem', fontWeight: 600, marginTop: '2px' }}>{f.value}</div>
                    </div>
                  ))}
                </div>
              </div>
              <p style={{ color: '#7d877e', fontSize: '0.8rem', marginBottom: '12px' }}>
                Monitor your patients' wellness, review AI-powered journal insights, manage bookings, and receive instant crisis alerts.
              </p>
              <button className="btn-primary btn-full" onClick={() => advance(1)}>Next Step →</button>
            </div>
          )}

          {step === 1 && (
            <div>
              <h3>📞 Your Contact Details</h3>
              <p style={{ color: '#7d877e', fontSize: '0.8rem', marginBottom: '12px' }}>
                Provide a contact method so patients can reach you for appointments, follow-ups, or questions.
              </p>
              <input
                value={contactInfo} onChange={e => setContactInfo(e.target.value)}
                placeholder="Mobile number or email"
                style={{ width: '100%', padding: '10px 12px', fontSize: '0.875rem', marginBottom: '12px' }}
              />
              <div style={{ display: 'flex', gap: '8px' }}>
                <button className="btn-primary" onClick={handleSaveContact} disabled={saving} style={{ flex: 1 }}>
                  {saving ? 'Saving...' : 'Save & Continue'}
                </button>
                <button onClick={() => advance(2)} style={{ flex: 1 }}>Skip</button>
              </div>
            </div>
          )}

          {step === 2 && (
            <div>
              <h3>👥 Trusted Contact (Crisis Alerts)</h3>
              <p style={{ color: '#7d877e', fontSize: '0.8rem', marginBottom: '12px' }}>
                If you trigger a self-crisis alert and cannot be reached, who should we notify?
              </p>
              <input
                value={trustedContact} onChange={e => setTrustedContact(e.target.value)}
                placeholder="Trusted contact email or phone"
                style={{ width: '100%', padding: '10px 12px', fontSize: '0.875rem', marginBottom: '12px' }}
              />
              <div style={{ display: 'flex', gap: '8px' }}>
                <button className="btn-primary" onClick={handleSaveTrusted} disabled={saving} style={{ flex: 1 }}>
                  {saving ? 'Saving...' : 'Save & Continue'}
                </button>
                <button onClick={() => advance(3)} style={{ flex: 1 }}>Skip</button>
              </div>
            </div>
          )}

          {step === 3 && (
            <div>
              <h3>🔮 Quick Tips</h3>
              <div style={{ background: '#1d2623', border: '1px solid #31423a', borderRadius: '10px', padding: '16px', margin: '12px 0' }}>
                {[
                  { emoji: '💬', title: 'AI Journal Summaries', desc: 'Your patients\' journal entries are summarized by AI. Review them in the Journal & Wellness tab.' },
                  { emoji: '⚠️', title: 'Crisis Alerts', desc: 'Elevated vitals or high-risk journal entries trigger instant alerts. Acknowledge and escalate from the dashboard.' },
                  { emoji: '📅', title: 'Availability & Bookings', desc: 'Set your available dates in the Bookings tab. Patients will book based on their assigned psychologist.' },
                ].map((tip, i) => (
                  <div key={i} style={{ display: 'flex', gap: '12px', marginBottom: i < 2 ? '10px' : 0 }}>
                    <span style={{ color: '#8fcbb1', fontSize: '1.2rem' }}>{tip.emoji}</span>
                    <div>
                      <div style={{ color: '#bac9bf', fontWeight: 600, fontSize: '0.875rem' }}>{tip.title}</div>
                      <div style={{ color: '#7d877e', fontSize: '0.75rem' }}>{tip.desc}</div>
                    </div>
                  </div>
                ))}
              </div>
              <button className="btn-primary btn-full" onClick={() => advance(4)}>Finish →</button>
            </div>
          )}

          {step >= 4 && (
            <div style={{ background: 'linear-gradient(135deg,#19211e,#1a3a2a)', border: '1px solid rgba(34,197,94,0.25)', borderRadius: '16px', padding: '32px', textAlign: 'center' }}>
              <div style={{ fontSize: '3rem', marginBottom: '8px' }}>✅</div>
              <div style={{ color: '#22c55e', fontSize: '1.5rem', fontWeight: 700 }}>You're all set!</div>
              <div style={{ color: '#7d877e', fontSize: '0.85rem', marginTop: '8px', lineHeight: 1.6 }}>
                Your dashboard is ready. Use the sidebar to manage patients, view journals, set availability, and more.
              </div>
              <ConsentUpload user={user} />
              <button className="btn-primary btn-full" onClick={finish} style={{ marginTop: '20px', padding: '12px', fontSize: '1rem' }}>
                🚀 Open Dashboard
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function ConsentUpload({ user }: { user: any }) {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploaded, setUploaded] = useState('')

  async function handleUpload() {
    if (!file) return
    setUploading(true)
    try {
      const data = await api.uploadConsentForm(file)
      setUploaded(data?.file_path || 'Uploaded')
      setFile(null)
    } catch {}
    setUploading(false)
  }

  return (
    <div style={{ marginTop: '16px', padding: '12px', background: '#1a2238', border: '1px solid #223028', borderRadius: '8px', textAlign: 'left' }}>
      <div style={{ color: '#9ca99e', fontSize: '0.8rem', fontWeight: 600, marginBottom: '8px' }}>📄 Consent Form</div>
      {uploaded ? (
        <div style={{ color: '#22c55e', fontSize: '0.8125rem' }}>✅ Consent form uploaded. <button onClick={() => setUploaded('')} style={{ background: 'none', border: 'none', color: '#8fcbb1', cursor: 'pointer', fontSize: '0.75rem', textDecoration: 'underline' }}>Re-upload</button></div>
      ) : (
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <input type="file" onChange={e => setFile(e.target.files?.[0] || null)} accept=".pdf,.jpg,.png"
            style={{ fontSize: '0.75rem', color: '#9ca99e', flex: 1 }} />
          <button onClick={handleUpload} disabled={!file || uploading}
            style={{ padding: '6px 14px', fontSize: '0.75rem', background: file ? '#8fcbb1' : '#31423a', border: 'none', borderRadius: '6px', color: file ? '#121715' : '#6b766d', cursor: file ? 'pointer' : 'default' }}>
            {uploading ? 'Uploading...' : 'Upload'}
          </button>
        </div>
      )}
    </div>
  )
}