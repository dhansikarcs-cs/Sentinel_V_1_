import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { MOODS, moodColor, moodScore, sourceColor, todayStr, formatDateTime } from '../constants'
import MoodPicker from '../components/MoodPicker'

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
        const tm = mh.find((m: any) => (m.date || '').slice(0, 10) === todayStr())
        if (tm) setTodayMood(tm)
      }
    } catch {}
  }

  useEffect(() => { load() }, [])

  async function handleMood(label: string) {
    if (moodLocked) return
    const m = MOODS.find(x => x.label === label)
    if (!m) return
    try {
      await api.logMood(todayStr(), m.emoji, m.label)
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
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: '14px' }}>
          <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#9ca99e', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Daily check-in</div>
          <div style={{ fontSize: '0.6875rem', color: todayMood ? moodColor(todayMood.label) : '#5a6a8a' }}>
            {todayMood ? `Logged · ${todayMood.label}` : 'One entry per day'}
          </div>
        </div>
        {todayMood ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 14px', borderRadius: '10px', background: `${moodColor(todayMood.label)}0d`, border: `1px solid ${moodColor(todayMood.label)}33` }}>
            <span style={{ fontSize: '1.4rem', lineHeight: 1 }}>{todayMood.emoji}</span>
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.9rem', textTransform: 'capitalize', color: moodColor(todayMood.label) }}>{todayMood.label}</div>
              <div style={{ fontSize: '0.6875rem', color: '#7d877e' }}>Next check-in unlocks tomorrow</div>
            </div>
          </div>
        ) : (
          <div>
            <div style={{ color: '#8aa198', fontSize: '0.8125rem', marginBottom: '12px' }}>How are you feeling right now?</div>
            <MoodPicker locked={moodLocked} onSelect={handleMood} />
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
                    const y = 45 - (moodScore(m.label) / 5) * 35
                    return { x, y, label: m.label, date: m.date }
                  })
                  const linePath = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
                  const fillPath = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ') + `L${pts[pts.length - 1].x},45 L${pts[0].x},45 Z`
                  return (
                    <>
                      <path d={fillPath} fill="url(#moodFill)" />
                      <path d={linePath} fill="none" stroke="#c06a8b88" strokeWidth="2" />
                      {pts.map((p, i) => (
                        <circle key={i} cx={p.x} cy={p.y} r="3.5" fill={moodColor(p.label)} stroke="#fff" strokeWidth="1.2" />
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
                    background: `${sourceColor(lastSource)}22`, color: sourceColor(lastSource),
                    fontSize: '0.6rem', padding: '1px 6px', borderRadius: '3px', fontWeight: 600,
                    border: `1px solid ${sourceColor(lastSource)}44`, marginLeft: '6px',
                  }}>{lastSource.charAt(0).toUpperCase() + lastSource.slice(1)}</span>
                )}
              </div>
              <div className="ai-body">{lastSummary}</div>
              {lastEmotions && <div style={{ fontSize: '0.6875rem', color: '#7d877e', marginTop: '6px' }}>Emotions: {lastEmotions}</div>}
            </div>
          )}
        </div>
      )}

      {tab === 'history' && (
        <div>
          {entries.length > 0 && (
            <div style={{ color: '#8aa198', fontSize: '0.75rem', marginBottom: '8px' }}>Showing last {Math.min(20, entries.length)} entries</div>
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {entries.slice(-20).reverse().map((e: any, i: number) => {
              const id = e.id || i
              const open = expandedEntries.has(id)
              const ts = formatDateTime(e.timestamp || e.created_at || Date.now())
              return (
                <div key={id}>
                  <button onClick={() => toggleExpanded(id)}
                    style={{ width: '100%', padding: '8px 12px', background: open ? '#27322d' : '#1d2623', border: `1px solid ${open ? '#8fcbb1' : '#31423a'}`, borderRadius: '8px', color: '#d9ddd3', fontSize: '0.8125rem', cursor: 'pointer', textAlign: 'left', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span>📄 {ts}</span>
                    <span style={{ marginLeft: 'auto', color: '#7d877e', fontSize: '0.7rem' }}>{open ? 'Collapse' : 'Expand'}</span>
                  </button>
                  {open && (
                    <div style={{ background: 'linear-gradient(135deg,#1a2238,#1e2a45)', border: '1px solid #1e3a5a', borderRadius: '10px', padding: '16px', margin: '2px 0 8px 0' }}>
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
                        <button onClick={async (ev) => { ev.stopPropagation(); try { await api.resummarizeJournal(id); await load() } catch {} }}
                          style={{ marginLeft: 'auto', fontSize: '0.65rem', padding: '2px 8px', background: '#1d2623', border: '1px solid #31423a', borderRadius: '4px', color: '#8fcbb1', cursor: 'pointer' }}>
                          🔄 Re-summarize
                        </button>
                      </div>
                      <div style={{ color: '#9dada4', fontSize: '0.8125rem', lineHeight: 1.5 }}>{e.summary || e.raw_content}</div>
                      {e.summary && e.summary !== e.raw_content && (
                        <div style={{ marginTop: '8px', padding: '6px 10px', borderRadius: '6px', background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.25)', color: '#fbbf24', fontSize: '0.68rem', lineHeight: 1.5 }}>
                          This summary was generated by AI and has not been reviewed by a clinician. Sentinel assists monitoring — it never determines whether you are safe. If you feel unsafe, seek help immediately regardless of this summary.
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
            {entries.length === 0 && <p style={{ color: '#7d877e', fontSize: '0.875rem' }}>💬 No entries yet. Start writing above.</p>}
          </div>
        </div>
      )}
    </div>
  )
}
