import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'

export default function Unlock() {
  const navigate = useNavigate()
  const [passphrase, setPassphrase] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await api.unlock(passphrase)
      navigate('/dashboard')
    } catch (err: any) {
      setError(err.message || 'Incorrect passphrase')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <form onSubmit={handleSubmit} className="card" style={{ padding: '32px', width: '100%', maxWidth: '420px', display: 'flex', flexDirection: 'column', gap: '16px', textAlign: 'center' }}>
        <div style={{ fontSize: '2.5rem' }}>🔐</div>
        <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#e8e4ec' }}>Security Passphrase Required</div>
        <div style={{ fontSize: '0.8125rem', color: '#6a6474', lineHeight: 1.6 }}>
          The clinic admin or lead psychologist must enter the master encryption passphrase.<br />
          This passphrase is <strong style={{ color: '#d8d4dc' }}>never stored on disk</strong> — it exists only in memory for this session.
        </div>
        <input type="password" placeholder="Enter the clinic's master passphrase..." value={passphrase} onChange={e => setPassphrase(e.target.value)} style={{ padding: '10px 12px', fontSize: '0.875rem' }} />
        <button type="submit" disabled={loading} className="btn-primary" style={{ justifyContent: 'center', padding: '10px' }}>
          {loading ? 'Unlocking...' : '🔓 Unlock Platform'}
        </button>
        {error && <div style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.3)', color: '#ef4444', fontSize: '0.8125rem', padding: '8px 12px', borderRadius: '8px' }}>{error}</div>}
        <div style={{ fontSize: '0.6875rem', color: '#4a5a6a' }}>One-time entry per session. Closing the app clears the key from memory.</div>
      </form>
    </div>
  )
}
