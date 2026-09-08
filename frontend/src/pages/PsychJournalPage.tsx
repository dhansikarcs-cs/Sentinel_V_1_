import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { sourceColor } from '../constants'

export default function PsychJournalPage() {
  const [wellness, setWellness] = useState<any>(null)

  useEffect(() => {
    api.getWellness().then(setWellness).catch(() => {})
  }, [])

  return (
    <div className="space-y-6 animate-fade-in">
      <h1>📓 Journal & Wellness</h1>

      <div className="card" style={{ padding: '20px' }} data-tour="psych-journal">
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
          {wellness?.mood && (
            <>
              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Today's Mood</div>
                <div style={{ fontSize: '2rem' }}>{wellness.mood.emoji}</div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--secondary)' }}>{wellness.mood.label}</div>
              </div>
              <div style={{ width: '1px', height: '40px', background: 'var(--border)' }} />
            </>
          )}
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Journal Entries Today</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--heading)' }}>{wellness?.journals_today || 0}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>entries today</div>
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
              padding: '8px 20px', borderRadius: '6px', border: `1px solid ${subTab === st ? 'var(--accent)' : 'var(--border)'}`,
              background: subTab === st ? 'var(--accent-soft)' : 'transparent',
              color: subTab === st ? 'var(--accent)' : 'var(--secondary)', fontSize: '0.8125rem', cursor: 'pointer',
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
              <span style={{ color: 'var(--muted)', fontSize: '0.75rem' }}>{wordCount} words · {charCount} characters</span>
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
            <p style={{ color: 'var(--muted)', fontSize: '0.875rem' }}>No journal entries yet.</p>
          ) : (
            entries.map((e: any) => {
              const id = e.id
              const open = expanded.has(id)
              const ts = e.timestamp ? new Date(e.timestamp).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : ''
              return (
                <div key={id} style={{ marginBottom: '8px' }}>
                  <button onClick={() => setExpanded(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n })}
                    style={{
                      width: '100%', padding: '8px 12px', background: open ? 'var(--accent-soft)' : 'var(--surface)',
                      border: `1px solid ${open ? 'var(--accent)' : 'var(--border)'}`, borderRadius: '8px',
                      color: 'var(--text)', fontSize: '0.8125rem', cursor: 'pointer', textAlign: 'left',
                      display: 'flex', alignItems: 'center', gap: '8px',
                    }}>
                    <span>📄 {ts}</span>
                    <span style={{ marginLeft: 'auto', color: 'var(--muted)', fontSize: '0.7rem' }}>{open ? 'Collapse' : 'Expand'}</span>
                  </button>
                  {open && (
                    <div style={{ background: 'linear-gradient(135deg,var(--surface),var(--surface-soft))', border: '1px solid var(--border)', borderRadius: '10px', padding: '16px', margin: '2px 0 0 0' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px', flexWrap: 'wrap' }}>
                        {e.ai_source && (
                          <span style={{
                            background: `${sourceColor(e.ai_source)}22`, color: sourceColor(e.ai_source),
                            fontSize: '0.6rem', padding: '1px 6px', borderRadius: '3px', fontWeight: 600,
                            border: `1px solid ${sourceColor(e.ai_source)}44`,
                          }}>{e.ai_source.toUpperCase()}</span>
                        )}
                        {e.emotions && (
                          <span style={{ fontSize: '0.65rem', color: 'var(--secondary)' }}>Emotions: {e.emotions}</span>
                        )}
                      </div>
                      <div style={{ color: 'var(--text)', fontSize: '0.8125rem', lineHeight: 1.6 }}>{e.summary}</div>
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