import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { MOODS } from '../constants'

export default function MoodPage() {
  const [logs, setLogs] = useState<any[]>([])
  const [todayDone, setTodayDone] = useState(false)

  async function load() {
    try {
      const data = await api.getMoods()
      setLogs(data || [])
    } catch {}
    try {
      const t = await api.checkTodayMood()
      setTodayDone(t.logged ?? false)
    } catch {}
  }

  useEffect(() => { load() }, [])

  async function handleMood(m: typeof MOODS[0]) {
    const date = new Date().toISOString().split('T')[0]
    try {
      await api.logMood(date, m.emoji, m.label)
      setTodayDone(true)
      await load()
    } catch (err: any) {
      alert(err.message)
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <h1>Mood Log</h1>
      {!todayDone ? (
        <div className="card">
          <p style={{ fontSize: '0.875rem', color: '#9a92a2', marginBottom: '16px' }}>How are you feeling right now?</p>
          <div className="flex gap-3 flex-wrap">
            {MOODS.map(m => (
              <button key={m.label} onClick={() => handleMood(m)}
                style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px', padding: '12px 16px', background: '#1e2336', border: '1px solid #2d2d44', borderRadius: '8px', cursor: 'pointer', transition: 'all 0.2s', minWidth: '80px' }}
                onMouseEnter={e => { e.currentTarget.style.background = '#232840'; e.currentTarget.style.borderColor = '#c49ea4' }}
                onMouseLeave={e => { e.currentTarget.style.background = '#1e2336'; e.currentTarget.style.borderColor = '#2d2d44' }}>
                <span style={{ fontSize: '1.75rem' }}>{m.emoji}</span>
                <span style={{ fontSize: '0.75rem', color: '#6a6474' }}>{m.label}</span>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="card" style={{ borderColor: 'rgba(34,197,94,0.3)' }}>
          <div className="flex items-center gap-2">
            <span>✅</span>
            <span style={{ fontSize: '0.875rem', color: '#22c55e' }}>Mood logged for today. Check back tomorrow!</span>
          </div>
        </div>
      )}
      <div>
        <h2>Recent Moods</h2>
        <div className="space-y-2 mt-3">
          {logs.slice(-14).reverse().map((l: any) => (
            <div key={l.id} className="card-stage" style={{ justifyContent: 'space-between' }}>
              <div className="flex items-center gap-3">
                <span style={{ fontSize: '1.25rem' }}>{l.emoji}</span>
                <span style={{ fontSize: '0.8125rem', color: '#d8d4dc' }}>{l.label}</span>
              </div>
              <span style={{ fontSize: '0.75rem', color: '#6a6474' }}>{l.date}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
