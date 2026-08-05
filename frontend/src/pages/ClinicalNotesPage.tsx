import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import PatientSelector from '../components/PatientSelector'

interface J2NDraft {
  status: 'draft' | 'empty' | 'error'
  patient: string
  note?: string
  themes?: string[]
  journalDate?: string
  journalPreview?: string
}

export default function ClinicalNotesPage() {
  const [patients, setPatients] = useState<any[]>([])
  const [notes, setNotes] = useState<any[]>([])
  const [selectedPatient, setSelectedPatient] = useState('')
  const [rawNotes, setRawNotes] = useState('')
  const [saving, setSaving] = useState(false)
  const [aiDraft, setAiDraft] = useState<any>(null)
  const [j2n, setJ2n] = useState<J2NDraft | null>(null)
  const [j2nLoading, setJ2nLoading] = useState<string | null>(null)
  const [acceptedMsg, setAcceptedMsg] = useState('')
  const editorRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    api.getPsychPatients().then(setPatients).catch(() => {})
    api.getPsychNotes().then(setNotes).catch(() => {})
  }, [])

  function showAccepted(msg: string) {
    setAcceptedMsg(msg)
    window.setTimeout(() => setAcceptedMsg(''), 6000)
  }

  async function saveNote() {
    if (!selectedPatient || !rawNotes.trim()) return
    setSaving(true)
    try {
      await api.createPsychNote({ patient_username: selectedPatient, raw_notes: rawNotes })
      setRawNotes('')
      setAiDraft(null)
      showAccepted('Note saved.')
      const updated = await api.getPsychNotes()
      setNotes(updated || [])
    } catch (err: any) { alert(err.message) }
    setSaving(false)
  }

  function acceptIntoEditor(text: string) {
    setRawNotes(text)
    setAiDraft(null)
    setJ2n(null)
    showAccepted('Draft accepted into the editor — review, then Save Note.')
    editorRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    editorRef.current?.focus()
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

  async function journalToNote(p: any) {
    setSelectedPatient(p.username)
    setJ2nLoading(p.username)
    setJ2n(null)
    try {
      const journals = await api.getPatientJournals(p.username)
      if (!journals || journals.length === 0) {
        setJ2n({ status: 'empty', patient: p.username })
        return
      }
      const latest = journals[0]
      const j2n = await api.journalToNote(p.username, latest.raw_content || '', latest.summary || '')
      setJ2n({
        status: 'draft',
        patient: p.username,
        note: j2n.note || j2n.suggestion || '',
        themes: j2n.themes || [],
        journalDate: (latest.timestamp || latest.created_at || '').slice(0, 10),
        journalPreview: (latest.summary || latest.raw_content || '').slice(0, 90),
      })
    } catch {
      setJ2n({ status: 'error', patient: p.username })
    } finally {
      setJ2nLoading(null)
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <h1>📝 Clinical Documentation</h1>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px', alignItems: 'start' }}>
        <div className="space-y-4">
          <div className="card" style={{ padding: '20px' }}>
            <h2 style={{ fontSize: '0.9rem', margin: '0 0 12px 0' }}>✍️ New Session Note</h2>
            <PatientSelector
              patients={patients}
              value={selectedPatient}
              onChange={setSelectedPatient}
              placeholder="Select patient..."
              style={{ width: '100%', marginBottom: '12px' }}
            />
            <textarea
              ref={editorRef}
              value={rawNotes}
              onChange={e => setRawNotes(e.target.value)}
              placeholder="Enter your session observations..."
              rows={8}
              style={{ width: '100%', padding: '12px', fontSize: '0.875rem', resize: 'none', marginBottom: '12px' }}
            />
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <button onClick={saveNote} disabled={saving || !selectedPatient || !rawNotes.trim()} className="btn-primary">
                {saving ? 'Saving...' : '💾 Save Note'}
              </button>
              <button onClick={generateAiDraft} disabled={!selectedPatient || !rawNotes.trim()} className="btn-secondary">
                🤖 AI Draft
              </button>
            </div>

            {acceptedMsg && (
              <div style={{
                marginTop: '12px', padding: '8px 12px', borderRadius: '8px', fontSize: '0.75rem',
                background: '#12201a', border: '1px solid #22c55e44', color: '#86efac',
              }}>
                ✅ {acceptedMsg}
              </div>
            )}

            {aiDraft && (
              <div className="ai-box" style={{ marginTop: '12px' }}>
                <div className="ai-header">🤖 AI Clinical Draft</div>
                <div className="ai-body" style={{ fontSize: '0.8125rem', whiteSpace: 'pre-wrap' }}>{aiDraft.note || aiDraft.suggestion}</div>
                {aiDraft.themes && (
                  <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', marginTop: '8px' }}>
                    {aiDraft.themes.map((t: string) => (
                      <span key={t} style={{ background: '#31423a', color: '#9ca99e', fontSize: '0.6875rem', padding: '2px 8px', borderRadius: '4px' }}>{t}</span>
                    ))}
                  </div>
                )}
                <div style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
                  <button
                    onClick={() => acceptIntoEditor(aiDraft.note || aiDraft.suggestion)}
                    className="btn-primary" style={{ padding: '6px 12px', fontSize: '0.75rem' }}
                  >
                    ✓ Accept to editor
                  </button>
                  <button onClick={() => setAiDraft(null)} className="btn-secondary" style={{ padding: '6px 12px', fontSize: '0.75rem' }}>
                    ✕ Cancel
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="card" style={{ padding: '20px' }}>
            <h2 style={{ fontSize: '0.9rem', margin: '0 0 12px 0' }}>📋 Saved Notes</h2>
            {notes.length === 0 ? (
              <p style={{ color: '#7d877e', fontSize: '0.875rem' }}>No notes yet.</p>
            ) : (
              <div className="space-y-2">
                {notes.slice(0, 10).map((n: any) => (
                  <div key={n.id} className="card-stage" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <span style={{ fontSize: '0.8125rem', color: '#8fcbb1', fontWeight: 600 }}>{n.patient}</span>
                      <span style={{ fontSize: '0.6875rem', color: '#7d877e' }}>{n.timestamp?.slice(0, 10)}</span>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#9ca99e', lineHeight: 1.5 }}>{n.ai_synthesis?.slice(0, 200)}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="card" style={{ padding: '20px' }}>
          <h2 style={{ fontSize: '0.9rem', margin: '0 0 12px 0' }}>🤖 Journal → Note</h2>
          <p style={{ fontSize: '0.75rem', color: '#7d877e', marginBottom: '12px', lineHeight: 1.6 }}>
            Pick a patient. We'll draft a clinical note from their latest journal entry — then you choose to accept it into the editor or cancel.
          </p>

          {!j2n && (
            <div className="space-y-2">
              {patients.length === 0 && <p style={{ color: '#7d877e', fontSize: '0.8125rem' }}>No patients available.</p>}
              {patients.slice(0, 5).map((p: any) => (
                <button
                  key={p.username}
                  onClick={() => journalToNote(p)}
                  disabled={j2nLoading !== null}
                  style={{
                    width: '100%', textAlign: 'left', padding: '10px 12px', borderRadius: '8px',
                    background: '#1d2623', border: '1px solid #31423a', color: '#d9ddd3', fontSize: '0.8125rem',
                    cursor: j2nLoading === p.username ? 'progress' : 'pointer', transition: 'all 0.2s',
                  }}
                >
                  {j2nLoading === p.username ? '⏳ Generating draft...' : `👤 ${p.name}`}
                </button>
              ))}
            </div>
          )}

          {j2n && j2n.status === 'empty' && (
            <div>
              <div style={{ color: '#9ca99e', fontSize: '0.8125rem', marginBottom: '12px' }}>
                No journal entries for <strong style={{ color: '#8fcbb1' }}>{j2n.patient}</strong> yet.
              </div>
              <button onClick={() => setJ2n(null)} className="btn-secondary" style={{ padding: '6px 12px', fontSize: '0.75rem' }}>← Back to patients</button>
            </div>
          )}

          {j2n && j2n.status === 'error' && (
            <div>
              <div style={{ color: '#fca5a5', fontSize: '0.8125rem', marginBottom: '12px' }}>
                Could not draft a note for {j2n.patient}. Please try again.
              </div>
              <button onClick={() => setJ2n(null)} className="btn-secondary" style={{ padding: '6px 12px', fontSize: '0.75rem' }}>← Back to patients</button>
            </div>
          )}

          {j2n && j2n.status === 'draft' && (
            <div>
              <div style={{ fontSize: '0.6875rem', color: '#7d877e', marginBottom: '8px' }}>
                From {j2n.patient}'s journal{j2n.journalDate ? ` · ${j2n.journalDate}` : ''}
              </div>
              <div style={{
                padding: '12px', borderRadius: '8px', fontSize: '0.8125rem', lineHeight: 1.6, whiteSpace: 'pre-wrap',
                background: '#121715', border: '1px solid #31423a', color: '#d9ddd3', maxHeight: '240px', overflow: 'auto',
              }}>
                {j2n.note || '(empty draft)'}
              </div>
              {j2n.themes && j2n.themes.length > 0 && (
                <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', marginTop: '8px' }}>
                  {j2n.themes.map((t: string) => (
                    <span key={t} style={{ background: '#31423a', color: '#9ca99e', fontSize: '0.6875rem', padding: '2px 8px', borderRadius: '4px' }}>{t}</span>
                  ))}
                </div>
              )}
              <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
                <button onClick={() => acceptIntoEditor(j2n.note || '')} className="btn-primary" style={{ padding: '8px 12px', fontSize: '0.75rem' }}>
                  ✓ Accept to editor
                </button>
                <button onClick={() => setJ2n(null)} className="btn-secondary" style={{ padding: '8px 12px', fontSize: '0.75rem' }}>
                  ✕ Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
