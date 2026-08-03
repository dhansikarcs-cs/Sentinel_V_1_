import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '../api/client'

export default function Register() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', password: '', confirmPassword: '', name: '', age: 25, occupation: '', role: 'patient', clinic_code: '', assigned_psych: '' })
  const [psychologists, setPsychologists] = useState<any[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    api.getAvailablePsychs().then(d => setPsychologists(d || [])).catch(() => {})
  }, [])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    if (form.password.length < 8) { setError('Password must be at least 8 characters'); return }
    if (form.password !== form.confirmPassword) { setError('Passwords do not match'); return }
    if (!form.name.trim()) { setError('Full name is required'); return }
    setLoading(true)
    try {
      await api.register({ username: form.username, password: form.password, name: form.name, role: form.role, clinic_code: form.clinic_code, age: form.age, occupation: form.occupation, assigned_psych: form.assigned_psych || undefined })
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
          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#c49ea4', letterSpacing: '-0.01em' }}>Register</div>
        </div>
        {error && <div style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.3)', color: '#ef4444', fontSize: '0.8125rem', padding: '8px 12px', borderRadius: '8px' }}>{error}</div>}

        <input placeholder="Username" value={form.username} onChange={e => setForm(f => ({ ...f, username: e.target.value }))} />
        <input type="password" placeholder="Password (min 8 chars)" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} />
        <input type="password" placeholder="Confirm Password" value={form.confirmPassword} onChange={e => setForm(f => ({ ...f, confirmPassword: e.target.value }))} />
        <input placeholder="Full Name" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
          <div>
            <label>Age</label>
            <input type="number" min={1} max={120} value={form.age} onChange={e => setForm(f => ({ ...f, age: parseInt(e.target.value) || 0 }))} />
          </div>
          <div>
            <label>Occupation</label>
            <input placeholder="e.g. Engineer" value={form.occupation} onChange={e => setForm(f => ({ ...f, occupation: e.target.value }))} />
          </div>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button type="button" onClick={() => setForm(f => ({ ...f, role: 'patient' }))} style={{ flex: 1, padding: '10px', fontSize: '0.8125rem', background: form.role === 'patient' ? '#232840' : '#1e2336', border: `1px solid ${form.role === 'patient' ? '#c49ea4' : '#2d2d44'}`, borderRadius: '8px', color: form.role === 'patient' ? '#e8e4ec' : '#9a92a2', cursor: 'pointer' }}>
            🧑 Patient
          </button>
          <button type="button" onClick={() => setForm(f => ({ ...f, role: 'psychologist' }))} style={{ flex: 1, padding: '10px', fontSize: '0.8125rem', background: form.role === 'psychologist' ? '#232840' : '#1e2336', border: `1px solid ${form.role === 'psychologist' ? '#f59e0b' : '#2d2d44'}`, borderRadius: '8px', color: form.role === 'psychologist' ? '#e8e4ec' : '#9a92a2', cursor: 'pointer' }}>
            🧑‍⚕️ Psychologist
          </button>
        </div>

        {form.role === 'psychologist' && (
          <div className="psych-box">
            <div className="psych-box-title">🧬 Psychologist Verification</div>
            <div className="psych-box-desc">Enter your institution code to verify your credentials</div>
            <input placeholder="Clinic / Institution Code" value={form.clinic_code} onChange={e => setForm(f => ({ ...f, clinic_code: e.target.value }))} />
          </div>
        )}

        {form.role === 'patient' && psychologists.length > 0 && (
          <div className="card" style={{ padding: '16px' }}>
            <div className="psych-box-title">👥 Select Your Psychologist</div>
            <div className="psych-box-desc" style={{ marginBottom: '8px' }}>Choose a psychologist to assign as your primary care provider</div>
            <select value={form.assigned_psych} onChange={e => setForm(f => ({ ...f, assigned_psych: e.target.value }))} style={{ width: '100%', padding: '10px 12px', fontSize: '0.875rem' }}>
              <option value="">Select a psychologist...</option>
              {psychologists.map((p: any) => (
                <option key={p.username || p} value={p.username || p}>{p.name || p}</option>
              ))}
            </select>
          </div>
        )}

        <button type="submit" disabled={loading} className="btn-primary" style={{ justifyContent: 'center', padding: '10px' }}>
          {loading ? 'Registering...' : 'Register'}
        </button>

        <div style={{ fontSize: '0.75rem', color: '#6a6474', textAlign: 'center' }}>
          Already have an account? <Link to="/login">Sign in</Link>
        </div>
      </form>
    </div>
  )
}
