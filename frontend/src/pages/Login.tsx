import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { login, getUser } from '../stores/auth'

export default function Login() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function redirectAfterLogin() {
    const u = getUser()
    if (!u) { navigate('/dashboard'); return }
    const step = u.onboarding_step ?? 0
    if (step >= 99) {
      navigate(u.role === 'psychologist' ? '/triage' : '/dashboard')
      return
    }
    if (u.role === 'psychologist') { navigate('/psych-onboarding'); return }
    navigate('/onboarding')
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      redirectAfterLogin()
    } catch (err: any) {
      setError(err.message || 'Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  async function quickLogin(u: string, p: string) {
    setUsername(u)
    setPassword(p)
    setError('')
    setLoading(true)
    try {
      await login(u, p)
      redirectAfterLogin()
    } catch (err: any) {
      setError(err.message || 'Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ padding: '20px' }}>
      <form onSubmit={handleSubmit} className="card" style={{ padding: '32px', width: '100%', maxWidth: '400px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', fontWeight: 700, background: 'linear-gradient(135deg, #8fcbb1, #a9e0c6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', letterSpacing: '-0.02em' }}>
            🧠 Brain Sentinel
          </div>
          <div style={{ fontSize: '0.8125rem', color: '#7d877e', marginTop: '4px' }}>AI-Assisted Mental Health Ecosystem</div>
        </div>

        <hr style={{ borderColor: '#31423a', opacity: 0.4 }} />

        {error && <div style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.3)', color: '#ef4444', fontSize: '0.8125rem', padding: '8px 12px', borderRadius: '8px' }}>{error}</div>}

        <input placeholder="Username" value={username} onChange={e => setUsername(e.target.value)} style={{ padding: '10px 12px', fontSize: '0.875rem', width: '100%' }} />
        <div style={{ position: 'relative' }}>
          <input type={showPw ? 'text' : 'password'} placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} style={{ padding: '10px 12px', fontSize: '0.875rem', width: '100%', paddingRight: '36px' }} />
          <button type="button" onClick={() => setShowPw(!showPw)} style={{ position: 'absolute', right: '6px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: '#7d877e', cursor: 'pointer', fontSize: '0.75rem', padding: '4px' }}>
            {showPw ? 'Hide' : 'Show'}
          </button>
        </div>

        <button type="submit" disabled={loading} className="btn-primary" style={{ justifyContent: 'center', width: '100%', padding: '10px' }}>
          {loading ? 'Signing in...' : 'Authenticate'}
        </button>

        <hr style={{ borderColor: '#31423a', opacity: 0.4 }} />

        <div style={{ fontSize: '0.75rem', color: '#7d877e', textAlign: 'center', fontWeight: 600 }}>Demo Accounts</div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button type="button" onClick={() => quickLogin('demopatient', 'Demo@1234')} style={{ flex: 1, padding: '8px', fontSize: '0.7rem', background: '#1d2623', border: '1px solid #31423a', borderRadius: '8px', color: '#8fcbb1', cursor: 'pointer' }}>
            Patient<br /><span style={{ color: '#7d877e', fontSize: '0.6rem' }}>demopatient</span>
          </button>
          <button type="button" onClick={() => quickLogin('psychdemo', 'Psych@1234')} style={{ flex: 1, padding: '8px', fontSize: '0.7rem', background: '#1d2623', border: '1px solid #31423a', borderRadius: '8px', color: '#f59e0b', cursor: 'pointer' }}>
            Psychologist<br /><span style={{ color: '#7d877e', fontSize: '0.6rem' }}>psychdemo</span>
          </button>
        </div>

        <div style={{ fontSize: '0.75rem', color: '#7d877e', textAlign: 'center' }}>
          Don't have an account? <Link to="/register">Register</Link>
        </div>
      </form>
    </div>
  )
}
