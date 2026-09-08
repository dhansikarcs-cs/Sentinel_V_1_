import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '../api/client'
import { COUNTRIES } from '../constants'

const CLINIC_CODES = ['SENTINEL-01', 'SENTINEL-02', 'SENTINEL-03', 'SENTINEL-04', 'SENTINEL-05']
const PROFESSIONAL_CODE_CLINICS: Record<string, string> = {
  'PSY-0001': 'SENTINEL-01',
  'PSY-0002': 'SENTINEL-02',
  'PSY-0003': 'SENTINEL-03',
  'PSY-0004': 'SENTINEL-04',
  'PSY-0005': 'SENTINEL-05',
}
const PROFESSIONAL_CODES = Object.keys(PROFESSIONAL_CODE_CLINICS)

const PASSWORD_RULES: { label: string; test: (pw: string) => boolean }[] = [
  { label: 'At least 6 characters', test: pw => pw.length >= 6 },
  { label: 'An uppercase letter', test: pw => /[A-Z]/.test(pw) },
  { label: 'A lowercase letter', test: pw => /[a-z]/.test(pw) },
  { label: 'A number', test: pw => /\d/.test(pw) },
  { label: 'A special character', test: pw => /[!@#$%^&*(),.?":{}|<>]/.test(pw) },
]
const COMMON_PASSWORDS = ['password', '123456', '654321', 'qwerty', 'abc123', 'letmein', 'admin1', 'welcome', 'monkey', 'dragon', 'login1', 'pass123', 'iloveyou']

function todayLocalISO(): string {
  const d = new Date()
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
}

export default function Register() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', password: '', confirmPassword: '', name: '', dob: '', occupation: '', role: 'patient', clinic_code: '', professional_code: '', assigned_psych: '', country: '' })
  const [psychologists, setPsychologists] = useState<any[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [showPw, setShowPw] = useState(false)
  const [showConfirmPw, setShowConfirmPw] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  useEffect(() => {
    api.getAvailablePsychs().then(d => setPsychologists(d || [])).catch(() => {})
  }, [])

  const psychsForClinic = form.clinic_code
    ? psychologists.filter((p: any) => p.clinic === form.clinic_code)
    : psychologists

  function passwordErrors(pw: string): string[] {
    const errs: string[] = []
    for (const r of PASSWORD_RULES) if (!r.test(pw)) errs.push(r.label.toLowerCase())
    if (COMMON_PASSWORDS.includes(pw.toLowerCase().trim())) errs.push('not a common/easy password')
    if (pw && /^(.)\1+$/.test(pw)) errs.push('not a single repeated character')
    return errs
  }

  function fieldErrors(): Record<string, string> {
    const errs: Record<string, string> = {}
    const u = form.username.trim()
    if (!u) errs.username = 'Username is required'
    else if (u.length < 3) errs.username = 'Username must be at least 3 characters'
    else if (!/^[a-zA-Z0-9_]+$/.test(u)) errs.username = 'Only letters, numbers and underscores allowed'
    const n = form.name.trim()
    if (!n) errs.name = 'Full name is required'
    else if (n.length < 2) errs.name = 'Name must be at least 2 characters'
    else if (!/[A-Za-z]/.test(n)) errs.name = 'That is not a real name — it contains no letters'
    const dob = form.dob || ''
    if (!dob) errs.dob = 'Date of birth is required'
    else {
      const d = new Date(dob + 'T00:00:00')
      const today = new Date()
      const min = new Date('1900-01-01T00:00:00')
      if (isNaN(d.getTime()) || d.getTime() > today.getTime()) errs.dob = 'Date of birth cannot be in the future'
      else if (d.getTime() < min.getTime()) errs.dob = 'Date of birth seems too far in the past'
    }
    if (!form.occupation.trim()) errs.occupation = form.role === 'psychologist' ? 'Specialisation is required' : 'Occupation is required'
    if (!form.country) errs.country = 'Select your country (birthday reminders use it)'
    if (form.role === 'psychologist' && (!form.professional_code || !PROFESSIONAL_CODE_CLINICS[form.professional_code.toUpperCase()])) errs.professional_code = 'Enter the professional code we gave you'
    if (form.role === 'patient' && !form.clinic_code) errs.clinic = 'Select your clinic'
    if (form.role === 'patient' && form.clinic_code && !form.assigned_psych) errs.psych = 'Choose your psychologist'
    return errs
  }

  function InlineError({ msg }: { msg?: string }) {
    if (!msg) return null
    return <div style={{ fontSize: '0.72rem', color: 'var(--danger)', marginTop: '4px' }}>⚠ {msg}</div>
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitted(true)
    setError('')
    const pwErrs = passwordErrors(form.password)
    if (pwErrs.length) { setError(`Password must contain ${pwErrs.join(', ')}`); return }
    if (form.password !== form.confirmPassword) { setError('Passwords do not match'); return }
    const errs = fieldErrors()
    const firstKey = Object.keys(errs)[0]
    if (firstKey) { setError(`Please fix: ${errs[firstKey]}`); return }
    setLoading(true)
    try {
      const derivedClinic = form.role === 'psychologist' ? PROFESSIONAL_CODE_CLINICS[form.professional_code.toUpperCase()] : form.clinic_code
      await api.register({ username: form.username, password: form.password, name: form.name, role: form.role, clinic_code: derivedClinic, dob: form.dob, country: form.country, occupation: form.occupation, professional_code: form.professional_code, assigned_psych: form.assigned_psych || undefined })
      navigate('/login')
    } catch (err: any) {
      setError(err.message || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ padding: '20px' }}>
      <form onSubmit={handleSubmit} className="card" style={{ padding: '32px', width: '100%', maxWidth: '400px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--accent)', letterSpacing: '-0.01em' }}>Register</div>
        </div>
        {error && <div style={{ background: 'rgba(199,70,59,0.15)', border: '1px solid rgba(199,70,59,0.3)', color: 'var(--danger)', fontSize: '0.8125rem', padding: '8px 12px', borderRadius: '8px' }}>{error}</div>}

        <input placeholder="Username (letters, numbers, _)" value={form.username} onChange={e => setForm(f => ({ ...f, username: e.target.value }))} style={{ borderColor: submitted && fieldErrors().username ? 'var(--danger)' : undefined }} />
        <InlineError msg={(submitted || form.username.trim().length > 0) ? fieldErrors().username : undefined} />
        <div style={{ position: 'relative' }}>
          <input type={showPw ? 'text' : 'password'} placeholder="Password (min 6, upper, lower, number, special)" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} style={{ paddingRight: '44px' }} />
          <button type="button" onClick={() => setShowPw(!showPw)} aria-label={showPw ? 'Hide password' : 'Show password'} style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', padding: '2px', opacity: 0.5, lineHeight: 1, display: 'flex' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              {showPw ? (
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
              ) : (
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
              )}
              {showPw && <line x1="1" y1="1" x2="23" y2="23" />}
            </svg>
          </button>
        </div>
        {form.password.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', fontSize: '0.72rem', marginTop: '-4px' }}>
            {PASSWORD_RULES.map(r => {
              const ok = r.test(form.password)
              return (
                <div key={r.label} style={{ color: ok ? '#2e7d32' : 'var(--danger)' }}>
                  {ok ? '✓' : '✗'} {r.label}
                </div>
              )
            })}
            {(() => {
              const common = COMMON_PASSWORDS.includes(form.password.toLowerCase().trim())
              const repeated = form.password.length > 0 && /^(.)\1+$/.test(form.password)
              const bad = common || repeated
              return (
                <div style={{ color: bad ? 'var(--danger)' : '#2e7d32' }}>
                  {!bad ? '✓' : '✗'} Not a common or repeated password
                </div>
              )
            })()}
          </div>
        )}
        <div style={{ position: 'relative' }}>
          <input type={showConfirmPw ? 'text' : 'password'} placeholder="Confirm Password" value={form.confirmPassword} onChange={e => setForm(f => ({ ...f, confirmPassword: e.target.value }))} style={{ paddingRight: '44px', borderColor: submitted && form.confirmPassword.length > 0 && form.password !== form.confirmPassword ? 'var(--danger)' : undefined }} />
          <button type="button" onClick={() => setShowConfirmPw(!showConfirmPw)} aria-label={showConfirmPw ? 'Hide password' : 'Show password'} style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', padding: '2px', opacity: 0.5, lineHeight: 1, display: 'flex' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              {showConfirmPw ? (
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
              ) : (
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
              )}
              {showConfirmPw && <line x1="1" y1="1" x2="23" y2="23" />}
            </svg>
          </button>
        </div>
        {form.confirmPassword.length > 0 && form.password !== form.confirmPassword && (
          <div style={{ fontSize: '0.72rem', color: 'var(--danger)', marginTop: '4px' }}>⚠ Passwords do not match</div>
        )}
        <input placeholder="Full Name" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} style={{ borderColor: submitted && fieldErrors().name ? 'var(--danger)' : undefined }} />
        <InlineError msg={(submitted || form.name.trim().length > 0) ? fieldErrors().name : undefined} />

        <div style={{ display: 'grid', gap: '8px', gridTemplateColumns: '1fr 1fr' }}>
          <div>
            <label>Date of Birth</label>
            <input type="date" max={todayLocalISO()} min="1900-01-01" value={form.dob} onChange={e => setForm(f => ({ ...f, dob: e.target.value }))} style={{ borderColor: (submitted || form.dob.length > 0) && fieldErrors().dob ? 'var(--danger)' : undefined }} />
            <InlineError msg={(submitted || form.dob.length > 0) ? fieldErrors().dob : undefined} />
          </div>
          <div>
            <label>{form.role === 'psychologist' ? 'Specialisation' : 'Occupation'}</label>
            <input placeholder={form.role === 'psychologist' ? 'e.g. Trauma, Anxiety, Child therapy' : 'e.g. Engineer'} value={form.occupation} onChange={e => setForm(f => ({ ...f, occupation: e.target.value }))} style={{ borderColor: submitted && fieldErrors().occupation ? 'var(--danger)' : undefined }} />
            <InlineError msg={(submitted || form.occupation.trim().length > 0) ? fieldErrors().occupation : undefined} />
          </div>
        </div>

        <div>
          <label>Country</label>
          <select value={form.country} onChange={e => setForm(f => ({ ...f, country: e.target.value }))} style={{ width: '100%', borderColor: (submitted || form.country.length > 0) && fieldErrors().country ? 'var(--danger)' : undefined }}>
            <option value="">Select your country…</option>
            {COUNTRIES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <div style={{ fontSize: '0.68rem', color: 'var(--muted)', marginTop: '4px' }}>Used for birthday wishes and quick check-in timing. You can adjust the exact timezone anytime in Edit Profile.</div>
          <InlineError msg={(submitted || form.country.length > 0) ? fieldErrors().country : undefined} />
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button type="button" onClick={() => setForm(f => ({ ...f, role: 'patient' }))} style={{ flex: 1, padding: '10px', fontSize: '0.8125rem', background: form.role === 'patient' ? 'var(--accent-soft)' : 'var(--surface)', border: `1px solid ${form.role === 'patient' ? 'var(--accent)' : 'var(--border)'}`, borderRadius: '8px', color: form.role === 'patient' ? 'var(--heading)' : 'var(--secondary)', cursor: 'pointer' }}>
            🧑 Patient
          </button>
          <button type="button" onClick={() => setForm(f => ({ ...f, role: 'psychologist' }))} style={{ flex: 1, padding: '10px', fontSize: '0.8125rem', background: form.role === 'psychologist' ? 'var(--accent-soft)' : 'var(--surface)', border: `1px solid ${form.role === 'psychologist' ? 'var(--warn)' : 'var(--border)'}`, borderRadius: '8px', color: form.role === 'psychologist' ? 'var(--heading)' : 'var(--secondary)', cursor: 'pointer' }}>
            🧑‍⚕️ Psychologist
          </button>
        </div>

        {form.role === 'psychologist' && (
          <div className="psych-box" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div className="psych-box-title">🧬 Psychologist Verification</div>
            <div className="psych-box-desc">Type the professional code we gave you — your clinic is filled in automatically</div>
            <div>
              <label>Professional Code</label>
              <input
                placeholder="e.g. PSY-0001"
                value={form.professional_code}
                onChange={e => setForm(f => ({ ...f, professional_code: e.target.value.trim().toUpperCase() }))}
              />
            </div>
            {PROFESSIONAL_CODE_CLINICS[form.professional_code] ? (
              <div style={{ fontSize: '0.8rem', color: '#2e7d32', fontWeight: 600 }}>✓ Clinic: {PROFESSIONAL_CODE_CLINICS[form.professional_code]}</div>
            ) : (
              form.professional_code.length > 0 && (
                <div style={{ fontSize: '0.72rem', color: 'var(--danger)' }}>⚠ Invalid code — check the code you were issued.</div>
              )
            )}
            <InlineError msg={submitted && fieldErrors().professional_code ? fieldErrors().professional_code : undefined} />
            <div style={{ fontSize: '0.7rem', color: 'var(--muted)' }}>Your professional code is unique to you and can only be registered once.</div>
          </div>
        )}

        {form.role === 'patient' && (
          <div className="card" style={{ padding: '16px' }}>
            <div className="psych-box-title">🏥 Select Your Clinic</div>
            <div className="psych-box-desc" style={{ marginBottom: '8px' }}>Choose the clinic where you'll receive care</div>
            <select value={form.clinic_code} onChange={e => setForm(f => ({ ...f, clinic_code: e.target.value, assigned_psych: '' }))} style={{ width: '100%', padding: '10px 12px', fontSize: '0.875rem', borderColor: submitted && fieldErrors().clinic ? 'var(--danger)' : undefined }}>
              <option value="">Select clinic...</option>
              {CLINIC_CODES.map(code => (
                <option key={code} value={code}>{code}</option>
              ))}
            </select>
            <InlineError msg={submitted ? fieldErrors().clinic : undefined} />
          </div>
        )}

        {form.role === 'patient' && (
          <div className="card" style={{ padding: '16px' }}>
            <div className="psych-box-title">👥 Select Your Psychologist</div>
            <div className="psych-box-desc" style={{ marginBottom: '8px' }}>
              {!form.clinic_code
                ? 'Choose your clinic first, then pick a psychologist'
                : `Psychologists at ${form.clinic_code}:`}
            </div>
            <select value={form.assigned_psych} onChange={e => setForm(f => ({ ...f, assigned_psych: e.target.value }))} disabled={!form.clinic_code || psychsForClinic.length === 0} style={{ width: '100%', padding: '10px 12px', fontSize: '0.875rem', borderColor: submitted && fieldErrors().psych ? 'var(--danger)' : undefined }}>
              <option value="">{!form.clinic_code ? 'Select clinic first...' : psychsForClinic.length === 0 ? 'No psychologists available yet at this clinic' : 'Select a psychologist...'}</option>
              {psychsForClinic.map((p: any) => (
                <option key={p.username || p} value={p.username || p}>{p.name || p}{p.professional_code ? ` (${p.professional_code})` : ''}{p.specialisation ? ` — ${p.specialisation}` : ''}</option>
              ))}
            </select>
            <InlineError msg={submitted ? fieldErrors().psych : undefined} />
            {form.clinic_code && psychsForClinic.length === 0 && (
              <div style={{ fontSize: '0.72rem', color: 'var(--muted)', marginTop: '8px' }}>
                No psychologists registered at this clinic yet. Ask your clinic to add their team first.
              </div>
            )}
          </div>
        )}

        <button type="submit" disabled={loading} className="btn-primary" style={{ justifyContent: 'center', padding: '10px' }}>
          {loading ? 'Registering...' : 'Register'}
        </button>

        <div style={{ fontSize: '0.75rem', color: 'var(--muted)', textAlign: 'center' }}>
          Already have an account? <Link to="/login">Sign in</Link>
        </div>
      </form>
    </div>
  )
}
