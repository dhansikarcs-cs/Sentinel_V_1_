import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { MOODS } from '../constants'
import MoodPicker from '../components/MoodPicker'

export default function MoodPage() {
  const [logs, setLogs] = useState<any[]>([])
  const [todayDone, setTodayDone] = useState(false)
  const [todayLabel, setTodayLabel] = useState('')

  async function load() {
    try {
      const data = await api.getMoods()
      setLogs(data || [])
      const today = (data || []).find((m: any) => (m.date || '').slice(0, 10) === new Date().toISOString().split('T')[0])
      if (today) setTodayLabel(today.label)
    } catch {}
    try {
      const t = await api.checkTodayMood()
      setTodayDone(t.logged ?? false)
    } catch {}
  }

  useEffect(() => { load() }, [])

  async function handleMood(label: string) {
    const m = MOODS.find(x => x.label === label)
    if (!m) return
    const date = new Date().toISOString().split('T')[0]
    try {
      await api.logMood(date, m.emoji, m.label)
      setTodayDone(true)
      setTodayLabel(m.label)
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
          <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#9a92a2', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '8px' }}>Daily check-in</div>
          <p style={{ fontSize: '0.875rem', color: '#7a8aaa', marginBottom: '16px' }}>How are you feeling right now?</p>
          <MoodPicker onSelect={handleMood} />
        </div>
      ) : (
        <div className="card" style={{ borderColor: 'rgba(34,197,94,0.3)' }}>
          <div className="flex items-center gap-2">
            <span>✅</span>
            <span style={{ fontSize: '0.875rem', color: '#22c55e' }}>Mood logged for today{todayLabel ? ` (${todayLabel})` : ''}. Check back tomorrow!</span>
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
                <span style={{ fontSize: '0.8125rem', color: '#d8d4dc', textTransform: 'capitalize' }}>{l.label}</span>
              </div>
              <span style={{ fontSize: '0.75rem', color: '#6a6474' }}>{l.date}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
