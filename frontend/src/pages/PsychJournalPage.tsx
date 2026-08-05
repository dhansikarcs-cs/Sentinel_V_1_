import { useEffect, useState } from 'react'
import { AreaChart, Area, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api/client'
import { sourceColor, mockHistory } from '../constants'

export default function PsychJournalPage() {
  const [sensorLogs, setSensorLogs] = useState<any[]>([])
  const [wellness, setWellness] = useState<any>(null)

  useEffect(() => {
    api.getSensorData().then((d: any[]) => {
      if (Array.isArray(d) && d.length > 0) setSensorLogs([...d].reverse())
    }).catch(() => {})
    api.getWellness().then(setWellness).catch(() => {})
  }, [])

  const ring = wellness?.ring || { bpm: 72, stress: 35, sleep: 7, spo2: 98, hrv: 45 }

  const trends = [
    { key: 'bpm', label: 'Heart Rate', unit: 'bpm', color: '#ff6b6b', data: sensorLogs.length > 0 ? sensorLogs.map(s => ({ v: s.bpm || 0 })) : mockHistory(ring.bpm || 72, 12).map(v => ({ v })) },
    { key: 'stress', label: 'Stress', unit: '%', color: '#ffd93d', data: sensorLogs.length > 0 ? sensorLogs.map(s => ({ v: s.stress || 0 })) : mockHistory(ring.stress || 35, 10).map(v => ({ v })) },
    { key: 'sleep', label: 'Sleep', unit: 'hrs', color: '#6bcbff', data: sensorLogs.length > 0 ? sensorLogs.map(s => ({ v: s.sleep_hours || 0 })) : mockHistory(ring.sleep || 7, 1.5).map(v => ({ v })) },
    { key: 'spo2', label: 'SpO₂', unit: '%', color: '#6bffb8', data: sensorLogs.length > 0 ? sensorLogs.map(s => ({ v: s.spo2 || 0 })) : mockHistory(ring.spo2 || 98, 1).map(v => ({ v })) },
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      <h1>📓 Journal & Wellness</h1>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '8px' }}>
        {trends.map(t => (
          <div key={t.key} className="card" style={{ padding: '12px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: '#9ca99e', fontSize: '0.75rem' }}>{t.label}</span>
              <span style={{ color: t.color, fontSize: '1rem', fontWeight: 700 }}>{t.data[t.data.length - 1]?.v || '-'}{t.unit === '%' ? '%' : t.unit === 'hrs' ? 'h' : ''}</span>
            </div>
            <ResponsiveContainer width="100%" height={80}>
              <AreaChart data={t.data}>
                <defs>
                  <linearGradient id={`grad_${t.key}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={t.color} stopOpacity={0.25} />
                    <stop offset="100%" stopColor={t.color} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="name" hide />
                <YAxis hide domain={['dataMin - 2', 'dataMax + 2']} />
                <Tooltip
                  contentStyle={{ background: '#1d2623', border: '1px solid #31423a', borderRadius: '8px', fontSize: '0.75rem' }}
                  labelStyle={{ color: '#7d877e' }}
                  formatter={(val: any) => [`${val}${t.unit === '%' ? '%' : t.unit === 'hrs' ? 'h' : ''}`, t.label]}
                />
                <Area type="monotone" dataKey="v" stroke={t.color} strokeWidth={1.5} fill={`url(#grad_${t.key})`} dot={false} activeDot={{ r: 3, fill: t.color }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ))}
      </div>

      <div className="card" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
          {wellness?.mood && (
            <>
              <div>
                <div style={{ fontSize: '0.75rem', color: '#7d877e' }}>Today's Mood</div>
                <div style={{ fontSize: '2rem' }}>{wellness.mood.emoji}</div>
                <div style={{ fontSize: '0.8125rem', color: '#9ca99e' }}>{wellness.mood.label}</div>
              </div>
              <div style={{ width: '1px', height: '40px', background: '#31423a' }} />
            </>
          )}
          <div>
            <div style={{ fontSize: '0.75rem', color: '#7d877e' }}>Journal Entries Today</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#e7e9df' }}>{wellness?.journals_today || 0}</div>
            <div style={{ fontSize: '0.75rem', color: '#7d877e' }}>entries today</div>
          </div>
        </div>
      </div>

      <MyJournal />
    </div>
  )
}

function MyJournal() {
  const [subTab, setSubTab] = useState<'write' | 'history'>('write')
  const [text, setText] = useState('')
  const [saving, setSaving] = useState(false)
  const [entries, setEntries] = useState<any[]>([])
  const [expanded, setExpanded] = useState<Set<number>>(new Set())

  useEffect(() => {
    api.getPsychJournals().then(setEntries).catch(() => {})
  }, [])

  async function handleSave() {
    if (!text.trim()) return
    setSaving(true)
    try {
      await api.createPsychJournal(text.trim())
      setText('')
      const updated = await api.getPsychJournals()
      setEntries(updated)
    } catch {}
    setSaving(false)
  }

  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0
  const charCount = text.length

  return (
    <div>
      <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
        {(['write', 'history'] as const).map(st => (
          <button key={st} onClick={() => setSubTab(st)}
            style={{
              padding: '8px 20px', borderRadius: '6px', border: `1px solid ${subTab === st ? '#8fcbb1' : '#31423a'}`,
              background: subTab === st ? '#27322d' : 'transparent',
              color: subTab === st ? '#8fcbb1' : '#9ca99e', fontSize: '0.8125rem', cursor: 'pointer',
            }}>
            {st === 'write' ? '✍️ Write Entry' : '📖 History'}
          </button>
        ))}
      </div>

      {subTab === 'write' ? (
        <div className="card" style={{ padding: '20px' }}>
          <div style={{ position: 'relative' }}>
            <textarea value={text} onChange={e => setText(e.target.value)}
              placeholder="Write freely about your day, thoughts, or sessions..."
              style={{ width: '100%', minHeight: '220px', padding: '12px', fontSize: '0.875rem', resize: 'vertical' }} />
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px' }}>
              <span style={{ color: '#7d877e', fontSize: '0.75rem' }}>{wordCount} words · {charCount} characters</span>
              <button onClick={handleSave} disabled={saving || !text.trim()}
                className="btn-primary" style={{ padding: '8px 24px' }}>
                {saving ? 'Saving...' : '💾 Save Entry'}
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div>
          {entries.length === 0 ? (
            <p style={{ color: '#7d877e', fontSize: '0.875rem' }}>No journal entries yet.</p>
          ) : (
            entries.map((e: any) => {
              const id = e.id
              const open = expanded.has(id)
              const ts = e.timestamp ? new Date(e.timestamp).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : ''
              return (
                <div key={id} style={{ marginBottom: '8px' }}>
                  <button onClick={() => setExpanded(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n })}
                    style={{
                      width: '100%', padding: '8px 12px', background: open ? '#27322d' : '#1d2623',
                      border: `1px solid ${open ? '#8fcbb1' : '#31423a'}`, borderRadius: '8px',
                      color: '#d9ddd3', fontSize: '0.8125rem', cursor: 'pointer', textAlign: 'left',
                      display: 'flex', alignItems: 'center', gap: '8px',
                    }}>
                    <span>📄 {ts}</span>
                    <span style={{ marginLeft: 'auto', color: '#7d877e', fontSize: '0.7rem' }}>{open ? 'Collapse' : 'Expand'}</span>
                  </button>
                  {open && (
                    <div style={{ background: 'linear-gradient(135deg,#1a2238,#1e2a45)', border: '1px solid #1e3a5a', borderRadius: '10px', padding: '16px', margin: '2px 0 0 0' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px', flexWrap: 'wrap' }}>
                        {e.ai_source && (
                          <span style={{
                            background: `${sourceColor(e.ai_source)}22`, color: sourceColor(e.ai_source),
                            fontSize: '0.6rem', padding: '1px 6px', borderRadius: '3px', fontWeight: 600,
                            border: `1px solid ${sourceColor(e.ai_source)}44`,
                          }}>{e.ai_source.toUpperCase()}</span>
                        )}
                        {e.emotions && (
                          <span style={{ fontSize: '0.65rem', color: '#9ca99e' }}>Emotions: {e.emotions}</span>
                        )}
                      </div>
                      <div style={{ color: '#d9ddd3', fontSize: '0.8125rem', lineHeight: 1.6 }}>{e.summary}</div>
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}