import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { getUser } from '../stores/auth'

export default function ClinicalNotesPage() {
  const [patients, setPatients] = useState<any[]>([])
  const [notes, setNotes] = useState<any[]>([])
  const [selectedPatient, setSelectedPatient] = useState('')
  const [rawNotes, setRawNotes] = useState('')
  const [saving, setSaving] = useState(false)
  const [aiDraft, setAiDraft] = useState<any>(null)

  useEffect(() => {
    api.getPsychPatients().then(setPatients).catch(() => {})
    api.get('/psychologists/notes').then(setNotes).catch(() => {})
  }, [])

  async function saveNote() {
    if (!selectedPatient || !rawNotes.trim()) return
    setSaving(true)
    try {
      await api.post('/psychologists/notes', { patient_username: selectedPatient, raw_notes: rawNotes })
      setRawNotes('')
      setAiDraft(null)
      const updated = await api.get('/psychologists/notes')
      setNotes(updated || [])
    } catch (err: any) { alert(err.message) }
    setSaving(false)
  }

  async function generateAiDraft() {
    if (!selectedPatient || !rawNotes.trim()) return
    try {
      const note = await api.synthesizeNote(rawNotes)
      setAiDraft(note)
    } catch {
      try {
        const fallback = await api.journalToNote(selectedPatient, rawNotes)
        setAiDraft(fallback)
      } catch {}
    }
  }

  const sourceColors: Record<string, string> = { ollama: '#c49ea4', groq: '#22c55e', rule: '#f59e0b', ai: '#60a5fa' }

  return (
    <div className="space-y-6 animate-fade-in">
      <h1>📝 Clinical Documentation</h1>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px' }}>
        <div className="space-y-4">
          <div className="card" style={{ padding: '20px' }}>
            <h2 style={{ fontSize: '0.9rem', margin: '0 0 12px 0' }}>✍️ New Session Note</h2>
            <select value={selectedPatient} onChange={e => setSelectedPatient(e.target.value)}
              style={{ width: '100%', padding: '10px 12px', fontSize: '0.875rem', marginBottom: '12px' }}>
              <option value="">Select patient...</option>
              {patients.map((p: any) => (
                <option key={p.username} value={p.username}>{p.name} (@{p.username})</option>
              ))}
            </select>
            <textarea
              value={rawNotes}
              onChange={e => setRawNotes(e.target.value)}
              placeholder="Enter your session observations..."
              rows={8}
              style={{ width: '100%', padding: '12px', fontSize: '0.875rem', resize: 'none', marginBottom: '12px' }}
            />
            <div style={{ display: 'flex', gap: '8px' }}>
              <button onClick={saveNote} disabled={saving || !selectedPatient || !rawNotes.trim()} className="btn-primary">
                {saving ? 'Saving...' : '💾 Save Note'}
              </button>
              <button onClick={generateAiDraft} disabled={!selectedPatient || !rawNotes.trim()} style={{
                background: '#1e2336', border: '1px solid #2d2d44', color: '#c49ea4',
                padding: '8px 16px', borderRadius: '8px', fontSize: '0.8125rem', cursor: 'pointer', fontWeight: 600,
              }}>
                🤖 AI Draft
              </button>
            </div>
            {aiDraft && (
              <div className="ai-box" style={{ marginTop: '12px' }}>
                <div className="ai-header">🤖 AI Clinical Draft</div>
                <div className="ai-body" style={{ fontSize: '0.8125rem', whiteSpace: 'pre-wrap' }}>{aiDraft.note || aiDraft.suggestion}</div>
                {aiDraft.themes && (
                  <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', marginTop: '8px' }}>
                    {aiDraft.themes.map((t: string) => (
                      <span key={t} style={{ background: '#2d2d44', color: '#9a92a2', fontSize: '0.6875rem', padding: '2px 8px', borderRadius: '4px' }}>{t}</span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="card" style={{ padding: '20px' }}>
            <h2 style={{ fontSize: '0.9rem', margin: '0 0 12px 0' }}>📋 Saved Notes</h2>
            {notes.length === 0 ? (
              <p style={{ color: '#6a6474', fontSize: '0.875rem' }}>No notes yet.</p>
            ) : (
              <div className="space-y-2">
                {notes.slice(0, 10).map((n: any) => (
                  <div key={n.id} className="card-stage" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <span style={{ fontSize: '0.8125rem', color: '#c49ea4', fontWeight: 600 }}>{n.patient}</span>
                      <span style={{ fontSize: '0.6875rem', color: '#6a6474' }}>{n.timestamp?.slice(0, 10)}</span>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#9a92a2', lineHeight: 1.5 }}>{n.ai_synthesis?.slice(0, 200)}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="card" style={{ padding: '20px' }}>
          <h2 style={{ fontSize: '0.9rem', margin: '0 0 12px 0' }}>🤖 Journal → Note</h2>
          {patients.length === 0 ? (
            <p style={{ color: '#6a6474', fontSize: '0.8125rem' }}>No patients available.</p>
          ) : (
            <>
              <p style={{ fontSize: '0.75rem', color: '#6a6474', marginBottom: '12px' }}>
                Select a patient to generate a clinical note from their recent journal entries.
              </p>
              <div className="space-y-2">
                {patients.slice(0, 5).map((p: any) => (
                  <div key={p.username} onClick={async () => {
                    setSelectedPatient(p.username)
                    try {
                      const journals = await api.getPatientJournals(p.username)
                      if (journals?.length > 0) {
                        const j2n = await api.journalToNote(p.username, journals[0].raw_content || '', journals[0].summary || '')
                        setAiDraft(j2n)
                      }
                    } catch {}
                  }}
                    style={{ padding: '10px', background: '#1e2336', borderRadius: '8px', cursor: 'pointer', fontSize: '0.8125rem', color: '#d8d4dc', border: '1px solid #2d2d44' }}>
                    {p.name}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
