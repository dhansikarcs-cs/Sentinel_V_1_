import { useEffect, useState, useRef } from 'react'

const BASE = '/api'

const params = new URLSearchParams(window.location.search)
const LINK_PARAMS = `patient=${encodeURIComponent(params.get('patient') || '')}&exp=${encodeURIComponent(params.get('exp') || '')}&sig=${encodeURIComponent(params.get('sig') || '')}`

async function publicGet(path: string) {
  const sep = path.includes('?') ? '&' : '?'
  const res = await fetch(`${BASE}${path}${sep}${LINK_PARAMS}`)
  if (!res.ok) return null
  return res.json()
}

async function publicPost(path: string) {
  const sep = path.includes('?') ? '&' : '?'
  const res = await fetch(`${BASE}${path}${sep}${LINK_PARAMS}`, { method: 'POST' })
  if (!res.ok) return null
  return res.json()
}

const ADDRESSES: Record<string, string> = {
  "test_patient_1": "42 Lakeview Drive, Apt 7B, Portland, OR 97201",
  "test_patient_2": "815 Maple Street, House #3, Portland, OR 97202",
  "test_patient_3": "1200 Pine Avenue, Unit 12, Portland, OR 97203",
  "alaya": "12 Rosewood Lane, Green Park, New Delhi 110016",
}

export default function TrusteePortalPage() {
  const [state, setState] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [acknowledged, setAcknowledged] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const clickedRef = useRef(false)

  async function load() {
    const s = await publicGet('/crisis/public-state')
    setState(s)
    setLoading(false)
    if (s?.triggered_at) {
      const secs = Math.floor((Date.now() - new Date(s.triggered_at).getTime()) / 1000)
      setElapsed(secs)
    }
    if (s?.active && !s.trustee_clicked && !s.trustee_acknowledged && !clickedRef.current) {
      clickedRef.current = true
      publicPost('/crisis/public-trustee-clicked').catch(() => {})
    }
    if (s?.trustee_acknowledged) setAcknowledged(true)
  }

  useEffect(() => { load(); const iv = setInterval(load, 5000); return () => clearInterval(iv) }, [])

  useEffect(() => {
    if (!state?.active) return
    const iv = setInterval(() => setElapsed(e => e + 1), 1000)
    return () => clearInterval(iv)
  }, [state?.active])

  async function handleAcknowledge() {
    const res = await publicPost('/crisis/public-trustee-acknowledge')
    if (res) setAcknowledged(true)
  }

  if (loading) return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(160deg, var(--bg), var(--bg-2))' }}>
      <div style={{ color: 'var(--muted)', fontSize: '1rem' }}>Loading...</div>
    </div>
  )

  const linkInvalid = !params.get('sig') || !params.get('patient') || state === null

  if (linkInvalid) return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(160deg, var(--bg), var(--bg-2))', padding: '32px' }}>
      <div style={{ textAlign: 'center', maxWidth: '480px' }}>
        <div style={{ fontSize: '3rem', marginBottom: '12px' }}>🔒</div>
        <h1 style={{ color: 'var(--strong)', fontSize: '1.5rem', marginBottom: '8px' }}>Invalid or Expired Link</h1>
        <p style={{ color: 'var(--muted)', fontSize: '0.9375rem' }}>This safety link is invalid or has expired. Please request a fresh link from your loved one's care team.</p>
        <p style={{ color: 'var(--faint)', fontSize: '0.8125rem', marginTop: '16px' }}>Sentinel — Crisis Response System</p>
      </div>
    </div>
  )

  if (!state?.active) return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(160deg, var(--bg), var(--bg-2))', padding: '32px' }}>
      <div style={{ textAlign: 'center', maxWidth: '480px' }}>
        <div style={{ fontSize: '3rem', marginBottom: '12px' }}>🟢</div>
        <h1 style={{ color: 'var(--ok)', fontSize: '1.5rem', marginBottom: '8px' }}>Trusted Contact Portal</h1>
        <p style={{ color: 'var(--muted)', fontSize: '1rem' }}>No active crisis at this time.</p>
        <p style={{ color: 'var(--faint)', fontSize: '0.8125rem', marginTop: '16px' }}>Sentinel — Crisis Response System</p>
      </div>
    </div>
  )

  if (state?.acknowledged) return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(160deg, var(--bg), var(--bg-2))', padding: '32px' }}>
      <div style={{ textAlign: 'center', maxWidth: '480px' }}>
        <div style={{ fontSize: '3rem', marginBottom: '12px' }}>✅</div>
        <h1 style={{ color: 'var(--ok)', fontSize: '1.5rem', marginBottom: '8px' }}>Crisis Resolved</h1>
        <p style={{ color: 'var(--muted)', fontSize: '0.9375rem' }}>This crisis has been acknowledged by the clinical team. No further action needed.</p>
        <p style={{ color: 'var(--faint)', fontSize: '0.8125rem', marginTop: '16px' }}>Sentinel — Crisis Response System</p>
      </div>
    </div>
  )

  if (state?.trustee_acknowledged) return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(160deg, var(--bg), var(--bg-2))', padding: '32px' }}>
      <div style={{ textAlign: 'center', maxWidth: '480px' }}>
        <div style={{ fontSize: '3rem', marginBottom: '12px' }}>✅</div>
        <h1 style={{ color: 'var(--ok)', fontSize: '1.5rem', marginBottom: '8px' }}>You've Already Responded</h1>
        <p style={{ color: 'var(--muted)', fontSize: '0.9375rem' }}>Thank you! Your status has been recorded. Please proceed to check on your loved one.</p>
        <p style={{ color: 'var(--faint)', fontSize: '0.8125rem', marginTop: '16px' }}>Sentinel — Crisis Response System</p>
      </div>
    </div>
  )

  const patient = state.patient || 'your loved one'
  const address = ADDRESSES[patient] || 'Address on file'
  const displayTime = elapsed >= 60 ? '60+' : String(elapsed)

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(160deg, var(--bg), var(--bg-2))', padding: '32px' }}>
      <div style={{ width: '100%', maxWidth: '520px' }}>
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '8px' }}>👤</div>
          <h1 style={{ fontSize: '1.5rem', color: 'var(--strong)', margin: '0 0 4px 0' }}>Trusted Contact Portal</h1>
          <p style={{ color: 'var(--text)', fontSize: '1.125rem', margin: '8px 0' }}>
            <strong>{patient}</strong> triggered a crisis alert <strong>{displayTime}s ago</strong>.
          </p>
        </div>

        <div style={{ background: 'var(--surface)', border: '1px solid var(--border-soft)', borderRadius: '10px', padding: '16px', marginBottom: '16px' }}>
          <div style={{ color: 'var(--soft)', fontSize: '0.8125rem', marginBottom: '4px' }}>📍 Last known location</div>
          <div style={{ color: 'var(--strong)', fontSize: '1rem', fontWeight: 600 }}>{address}</div>
        </div>

        {!acknowledged ? (
          <button
            onClick={handleAcknowledge}
            style={{
              width: '100%', padding: '16px', fontSize: '1.1rem', fontWeight: 700,
              background: 'linear-gradient(135deg, var(--ok), #16a34a)',
              border: 'none', borderRadius: '12px', color: 'white', cursor: 'pointer',
              boxShadow: '0 4px 16px rgba(46,139,87,0.3)',
            }}
          >
            ✅ Yes, I'm on my way!
          </button>
        ) : (
          <div style={{ background: 'var(--ok-alpha)', border: '1px solid rgba(46,139,87,0.3)', borderRadius: '12px', padding: '20px', textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', marginBottom: '8px' }}>🚀</div>
            <div style={{ color: 'var(--ok)', fontSize: '1.25rem', fontWeight: 700, marginBottom: '4px' }}>Thank you!</div>
            <div style={{ color: 'var(--muted)', fontSize: '0.875rem' }}>You are marked as <strong style={{ color: 'var(--ok)' }}>'On the Way'</strong>.</div>
            <div style={{ color: 'var(--faint)', fontSize: '0.75rem', marginTop: '8px' }}>Please proceed to check on {patient} as soon as possible.</div>
          </div>
        )}

        <p style={{ textAlign: 'center', color: 'var(--faint)', fontSize: '0.75rem', marginTop: '24px' }}>
          Sentinel — Crisis Response System
        </p>
      </div>
    </div>
  )
}
