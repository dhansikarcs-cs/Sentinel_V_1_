import { useEffect, useState } from 'react'
import { api } from '../api/client'

const moods = [
  { emoji: '😁', label: 'Great', score: 5, color: '#16a34a' },
  { emoji: '🙂', label: 'Good', score: 4, color: '#22c55e' },
  { emoji: '😐', label: 'Okay', score: 3, color: '#eab308' },
  { emoji: '🙁', label: 'Down', score: 2, color: '#f59e0b' },
  { emoji: '😢', label: 'Sad', score: 1, color: '#ef4444' },
]

const MOOD_COLORS: Record<string, string> = { Great: '#16a34a', Good: '#22c55e', Okay: '#eab308', Down: '#f59e0b', Sad: '#ef4444' }

export default function JournalPage() {
  const [text, setText] = useState('')
  const [entries, setEntries] = useState<any[]>([])
  const [saving, setSaving] = useState(false)
  const [lastSummary, setLastSummary] = useState('')
  const [lastSource, setLastSource] = useState('')
  const [lastEmotions, setLastEmotions] = useState('')
  const [todayMood, setTodayMood] = useState<any>(null)
  const [moodLocked, setMoodLocked] = useState(false)
  const [moodHistory, setMoodHistory] = useState<any[]>([])
  const [expandedEntries, setExpandedEntries] = useState<Set<number>>(new Set())
  const [tab, setTab] = useState<'write' | 'history'>('write')

  async function load() {
    try {
      const data = await api.getJournals()
      setEntries(data?.items || data || [])
    } catch {}
    try {
      const t = await api.checkTodayMood()
      setMoodLocked(t.logged ?? false)
    } catch {}
    try {
      const mh = await api.getMoods()
      if (Array.isArray(mh)) {
        setMoodHistory(mh)
        const today = new Date().toISOString().slice(0, 10)
        const tm = mh.find((m: any) => (m.date || '').slice(0, 10) === today)
        if (tm) setTodayMood(tm)
      }
    } catch {}
  }

  useEffect(() => { load() }, [])

  async function handleMood(m: typeof moods[0]) {
    if (moodLocked) return
    const date = new Date().toISOString().split('T')[0]
    try {
      await api.logMood(date, m.emoji, m.label)
      setTodayMood(m)
      setMoodLocked(true)
    } catch {}
  }

  async function handleSave() {
    if (!text.trim()) return
    setSaving(true)
    try {
      const res = await api.createJournal(text.trim())
      setLastSummary(res.summary || '')
      setLastSource(res.ai_source || '')
      setLastEmotions(res.emotions || '')
      setText('')
      await load()
    } catch (err: any) {
      alert(err.message)
    } finally {
      setSaving(false)
    }
  }

  function toggleExpanded(id: number) {
    setExpandedEntries(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id); else next.add(id)
      return next
    })
  }

  const sourceColors: Record<string, string> = { ollama: '#c49ea4', groq: '#22c55e', rule: '#f59e0b', ai: '#60a5fa' }

  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0
  const charCount = text.length

  const recentMoods = moodHistory
    .filter(m => m.date && m.label)
    .sort((a, b) => (a.date || '').localeCompare(b.date || ''))
    .slice(-14)

  return (
    <div className="space-y-4 animate-fade-in">
      <h1>📝 Wellness Journal</h1>

      <div className="card" style={{ padding: '20px' }}>
        {todayMood ? (
          <div style={{ textAlign: 'center', background: 'linear-gradient(135deg,#1a2844,#1e2a45)', border: `2px solid ${(MOOD_COLORS[todayMood.label] || '#888')}44`, borderRadius: '16px', padding: '16px' }}>
            <div style={{ fontSize: '3rem', lineHeight: 1.2 }}>{todayMood.emoji}</div>
            <div style={{ color: MOOD_COLORS[todayMood.label] || '#888', fontSize: '1.1rem', fontWeight: 700, marginTop: '4px' }}>{todayMood.label}</div>
            <div style={{ color: '#5a6a8a', fontSize: '0.7rem', marginTop: '4px' }}>Today's mood</div>
          </div>
        ) : (
          <div>
            <div style={{ textAlign: 'center', border: '2px dashed #2a3a5a', borderRadius: '16px', padding: '16px', marginBottom: '12px' }}>
              <div style={{ fontSize: '2rem', opacity: 0.6 }}>Tap an emoji to log your mood</div>
            </div>
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
              {moods.map(m => {
                const selected = todayMood?.label === m.label
                return (
                  <button key={m.label} onClick={() => handleMood(m)} disabled={moodLocked}
                    style={{
                      display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px', padding: '8px 10px',
                      background: selected ? 'rgba(196,158,164,0.15)' : '#1e2336',
                      border: selected ? '1px solid #c49ea4' : '1px solid #2d2d44',
                      borderRadius: '8px', cursor: moodLocked ? 'default' : 'pointer', minWidth: '60px',
                    }}>
                    <span style={{ fontSize: '1.3rem' }}>{m.emoji}</span>
                    <span style={{ fontSize: '0.6rem', color: selected ? '#c49ea4' : '#6a6474' }}>{m.label}</span>
                  </button>
                )
              })}
            </div>
          </div>
        )}
      </div>

      <div className="segmented-control" style={{ marginBottom: '12px' }}>
        <button className={`segmented-btn${tab === 'write' ? ' active' : ''}`} onClick={() => setTab('write')}>✍️ Write Entry</button>
        <button className={`segmented-btn${tab === 'history' ? ' active' : ''}`} onClick={() => setTab('history')}>📖 Past Entries</button>
      </div>

      {tab === 'write' && (
        <div className="card" style={{ padding: '20px' }}>
          {recentMoods.length >= 3 && (
            <div style={{ marginBottom: '16px' }}>
              <div style={{ color: '#5a6a8a', fontSize: '0.7rem', marginBottom: '4px' }}>Mood trend — last 14 days</div>
              <svg viewBox="0 0 280 50" style={{ width: '100%', height: '50px', overflow: 'visible' }}>
                <defs>
                  <linearGradient id="moodFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="rgba(192,106,139,0.15)" />
                    <stop offset="100%" stopColor="rgba(192,106,139,0)" />
                  </linearGradient>
                </defs>
                {(() => {
                  const pts = recentMoods.map((m, i) => {
                    const x = 20 + (i / Math.max(recentMoods.length - 1, 1)) * 240
                    const y = 45 - ((MOOD_COLORS[m.label] ? moods.find(mm => mm.label === m.label)?.score || 3 : 3) / 5) * 35
                    return { x, y, label: m.label, date: m.date }
                  })
                  const linePath = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
                  const fillPath = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ') + `L${pts[pts.length - 1].x},45 L${pts[0].x},45 Z`
                  return (
                    <>
                      <path d={fillPath} fill="url(#moodFill)" />
                      <path d={linePath} fill="none" stroke="#c06a8b88" strokeWidth="2" />
                      {pts.map((p, i) => (
                        <circle key={i} cx={p.x} cy={p.y} r="3.5" fill={MOOD_COLORS[p.label] || '#888'} stroke="#fff" strokeWidth="1.2" />
                      ))}
                    </>
                  )
                })()}
              </svg>
            </div>
          )}

          <textarea
            value={text}
            onChange={e => setText(e.target.value)}
            placeholder="What's on your mind? Write freely..."
            rows={6}
            style={{ width: '100%', padding: '12px', fontSize: '0.875rem', resize: 'none' }}
          />
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginTop: '8px' }}>
            <span style={{ color: '#5a6a8a', fontSize: '0.7rem' }}>{wordCount} words</span>
            <span style={{ color: '#5a6a8a', fontSize: '0.7rem' }}>{charCount} characters</span>
            <button onClick={handleSave} disabled={saving || !text.trim()} className="btn-primary" style={{ marginLeft: 'auto', padding: '8px 16px' }}>
              {saving ? 'Saving...' : '💾 Save Entry'}
            </button>
          </div>
          {lastSummary && (
            <div className="ai-box" style={{ marginTop: '12px' }}>
              <div className="ai-header">
                AI Summary
                {lastSource && (
                  <span style={{
                    background: `${sourceColors[lastSource] || '#888'}22`, color: sourceColors[lastSource] || '#888',
                    fontSize: '0.6rem', padding: '1px 6px', borderRadius: '3px', fontWeight: 600,
                    border: `1px solid ${sourceColors[lastSource] || '#888'}44`, marginLeft: '6px',
                  }}>{lastSource.charAt(0).toUpperCase() + lastSource.slice(1)}</span>
                )}
              </div>
              <div className="ai-body">{lastSummary}</div>
              {lastEmotions && <div style={{ fontSize: '0.6875rem', color: '#6a6474', marginTop: '6px' }}>Emotions: {lastEmotions}</div>}
            </div>
          )}
        </div>
      )}

      {tab === 'history' && (
        <div>
          {entries.length > 0 && (
            <div style={{ color: '#7a8aaa', fontSize: '0.75rem', marginBottom: '8px' }}>Showing last {Math.min(20, entries.length)} entries</div>
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {entries.slice(-20).reverse().map((e: any, i: number) => {
              const id = e.id || i
              const open = expandedEntries.has(id)
              const ts = new Date(e.timestamp || e.created_at || Date.now()).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
              return (
                <div key={id}>
                  <button onClick={() => toggleExpanded(id)}
                    style={{ width: '100%', padding: '8px 12px', background: open ? '#232840' : '#1e2336', border: `1px solid ${open ? '#c49ea4' : '#2d2d44'}`, borderRadius: '8px', color: '#d8d4dc', fontSize: '0.8125rem', cursor: 'pointer', textAlign: 'left', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span>📄 {ts}</span>
                    <span style={{ marginLeft: 'auto', color: '#6a6474', fontSize: '0.7rem' }}>{open ? 'Collapse' : 'Expand'}</span>
                  </button>
                  {open && (
                    <div style={{ background: 'linear-gradient(135deg,#1a2238,#1e2a45)', border: '1px solid #1e3a5a', borderRadius: '10px', padding: '16px', margin: '2px 0 8px 0' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px', flexWrap: 'wrap' }}>
                        {e.ai_source && (
                          <span style={{
                            background: `${sourceColors[e.ai_source] || '#888'}22`, color: sourceColors[e.ai_source] || '#888',
                            fontSize: '0.6rem', padding: '1px 6px', borderRadius: '3px', fontWeight: 600,
                            border: `1px solid ${sourceColors[e.ai_source] || '#888'}44`,
                          }}>{e.ai_source.toUpperCase()}</span>
                        )}
                        {e.emotions && (
                          <span style={{ fontSize: '0.65rem', color: '#9a92a2' }}>Emotions: {e.emotions}</span>
                        )}
                        <button onClick={async (ev) => { ev.stopPropagation(); try { await api.resummarizeJournal(id); await load() } catch {} }}
                          style={{ marginLeft: 'auto', fontSize: '0.65rem', padding: '2px 8px', background: '#1e2336', border: '1px solid #2d2d44', borderRadius: '4px', color: '#c49ea4', cursor: 'pointer' }}>
                          🔄 Re-summarize
                        </button>
                      </div>
                      <div style={{ color: '#9aa8c0', fontSize: '0.8125rem', lineHeight: 1.5 }}>{e.summary || e.raw_content}</div>
                    </div>
                  )}
                </div>
              )
            })}
            {entries.length === 0 && <p style={{ color: '#6a6474', fontSize: '0.875rem' }}>💬 No entries yet. Start writing above.</p>}
          </div>
        </div>
      )}
    </div>
  )
}
