import { useEffect, useState } from 'react'
import { api } from '../api/client'
import PatientSelector, { usePatientContext } from '../components/PatientSelector'
import PrioritiesPanel from '../components/PrioritiesPanel'
import { moodIcon, formatTime, formatDate } from '../constants'

export default function ConsultationPage() {
  const { patients } = usePatientContext()
  const [selected, setSelected] = useState('')
  const [overview, setOverview] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const [rawNotes, setRawNotes] = useState('')
  const [saving, setSaving] = useState(false)
  const [aiDraft, setAiDraft] = useState<any>(null)
  const [updating, setUpdating] = useState<string | null>(null)

  useEffect(() => {
    if (!selected) { setOverview(null); return }
    setLoading(true)
    api.getPatientOverview(selected)
      .then(d => setOverview(d))
      .catch(() => setOverview(null))
      .finally(() => setLoading(false))
  }, [selected])

  async function saveNote() {
    if (!selected || !rawNotes.trim()) return
    setSaving(true)
    try {
      await api.createPsychNote({ patient_username: selected, raw_notes: rawNotes })
      setRawNotes('')
      setAiDraft(null)
    } catch (err: any) { alert(err.message) }
    setSaving(false)
  }

  async function generateAiDraft() {
    if (!selected || !rawNotes.trim()) return
    try {
      setAiDraft(await api.synthesizeNote(rawNotes))
    } catch {
      try { setAiDraft(await api.journalToNote(selected, rawNotes)) } catch {}
    }
  }

  async function completeFollowup(id: string) {
    setUpdating(id)
    try {
      await api.updateFollowup(id, { status: 'completed' })
      const updated = await api.getPatientOverview(selected)
      setOverview(updated)
    } catch (err: any) { alert(err.message) }
    setUpdating(null)
  }

  return (
    <div className="animate-fade-in">
      <h2>{'\u{1F9D1}\u200D\u2695\uFE0F'} Open Session</h2>
      <p style={{ color: '#6a6474', fontSize: '0.75rem', marginBottom: '12px' }}>
        One screen for the session — what to attend to, the patient's current state, your note, and their follow-up actions.
      </p>

      <PatientSelector
        patients={patients}
        value={selected}
        onChange={setSelected}
        placeholder="-- Select patient to open session --"
        style={{ marginBottom: '16px' }}
      />

      {!selected && (
        <div className="card" style={{ color: '#6a6474', textAlign: 'center', padding: '32px' }}>
          Select a patient to compose the consultation workspace.
        </div>
      )}

      {selected && loading && (
        <div className="card" style={{ color: '#6a6474', textAlign: 'center', padding: '20px' }}>Preparing session...</div>
      )}

      {selected && !loading && !overview && (
        <div className="card" style={{ color: '#ef4444', textAlign: 'center', padding: '20px' }}>Failed to load patient state.</div>
      )}

      {selected && !loading && overview && (
        <Workspace overview={overview} selected={selected} rawNotes={rawNotes} setRawNotes={setRawNotes}
          saving={saving} saveNote={saveNote} generateAiDraft={generateAiDraft} aiDraft={aiDraft}
          updating={updating} completeFollowup={completeFollowup} />
      )}
    </div>
  )
}

function Workspace({ overview, selected, rawNotes, setRawNotes, saving, saveNote, generateAiDraft, aiDraft, updating, completeFollowup }: any) {
  const identity = overview.patient || {}
  const changes = overview.changes_since_last_visit || {}
  const followups = overview.followups || {}
  const sensor = overview.sensor_trends || []
  const latestSensor = sensor[0]
  const risk = overview.risk
  const crisis = overview.crisis
  const brief = overview.clinical_brief
  const followupList: any[] = followups.list || []

  return (
    <>
      <div className="card" style={{ padding: '14px', marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ color: '#c49ea4', fontWeight: 600, fontSize: '0.75rem', marginBottom: '4px' }}>SESSION FOR</div>
          <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f0f4ff' }}>{identity.name || identity.username}</div>
          <div style={{ color: '#7a8aaa', fontSize: '0.7rem', marginTop: '2px' }}>
            @{identity.username} &middot; {identity.age || '?'} yrs &middot; {identity.clinic || '—'}
          </div>
        </div>
        <div style={{ textAlign: 'right', fontSize: '0.7rem', color: '#7a8aaa' }}>
          {overview.last_appointment ? (
            <>
              <div style={{ color: '#f0f4ff', fontWeight: 600, fontSize: '0.8125rem' }}>
                {formatDate(overview.last_appointment.date)} {overview.last_appointment.time}
              </div>
              <div>{overview.last_appointment.session_type || 'Session'} &middot; {overview.last_appointment.status}</div>
            </>
          ) : (
            <div>No appointments yet</div>
          )}
          {crisis && (
            <div style={{ marginTop: '6px', color: '#ef4444', fontWeight: 700, fontSize: '0.7rem' }}>
              {'\u{1F6A8}'} CRISIS ACTIVE &middot; {crisis.acknowledged ? 'acknowledged' : 'NOT acknowledged'}
            </div>
          )}
        </div>
      </div>

      {(overview.alerts || []).length > 0 && (
        <div style={{ marginBottom: '16px' }}>
          {overview.alerts.map((a: string, i: number) => (
            <div key={i} style={{ background: '#2a0f1c', border: '1px solid #ef444455', color: '#fca5a5', borderRadius: '8px', padding: '8px 12px', fontSize: '0.75rem', marginBottom: '6px' }}>
              {'\u26A0\uFE0F'} {a}
            </div>
          ))}
        </div>
      )}

      <PrioritiesPanel priorities={overview.priorities} />

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '10px', marginBottom: '16px' }}>
        <Snapshot label="MOOD TREND" value={changes.mood_trend === 'declining' ? '\u2198 declining' : changes.mood_trend === 'improving' ? '\u2197 improving' : changes.mood_trend === 'stable' ? '\u2192 stable' : '\u2014'}
          sub={`Now ${changes.current_mood_avg ? Number(changes.current_mood_avg).toFixed(1) : 'N/A'} / Prev ${changes.previous_mood_avg ? Number(changes.previous_mood_avg).toFixed(1) : 'N/A'}`}
          color={changes.mood_trend === 'declining' ? '#ef4444' : changes.mood_trend === 'improving' ? '#22c55e' : '#fbbf24'} />
        <Snapshot label="ENGAGEMENT" value={`${changes.journal_count_7 || 0} journals`} sub={`${changes.journal_count_14 || 0} in 14d`}
          color={changes.engagement_trend === 'declining' ? '#ef4444' : '#22c55e'} />
        <Snapshot label="RISK" value={risk ? `${risk.risk_score}/10` : 'N/A'} sub={risk ? `${formatDate(risk.created_at)} · v${risk.algorithm_version || '?'}` : 'no assessments'}
          color={risk?.triggered ? '#ef4444' : risk && risk.risk_score >= 7 ? '#f59e0b' : '#22c55e'} />
        <Snapshot label="LATEST RING" value={latestSensor ? `${latestSensor.bpm || '—'} bpm` : '\u2014'}
          sub={latestSensor ? `${latestSensor.stress || '—'} stress · ${latestSensor.sleep_hours || '—'}h sleep` : 'no ring data'}
          color={latestSensor?.bpm >= 100 || (latestSensor?.spo2 && latestSensor.spo2 < 94) ? '#ef4444' : latestSensor?.stress >= 70 ? '#f59e0b' : '#22c55e'} />
        <Snapshot label="FOLLOW-UPS" value={`${followups.pending || 0} pending`} sub={`${followups.completed || 0} completed`}
          color={followups.pending > 0 ? '#f59e0b' : '#22c55e'} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
        <div className="card" style={{ padding: '14px' }}>
          <div style={{ color: '#c49ea4', fontWeight: 600, fontSize: '0.75rem', marginBottom: '6px' }}>CLINICAL BRIEF</div>
          {brief ? (
            <>
              <div style={{ color: '#6a6474', fontSize: '0.62rem', marginBottom: '4px' }}>{formatTime(brief.timestamp)}</div>
              <div style={{ color: '#9aa8c0', fontSize: '0.72rem', lineHeight: 1.6 }}>
                {(brief.clinical_summary || brief.summary || '').slice(0, 320)}
              </div>
              {(brief.emotions || '').length > 0 && (
                <div style={{ color: '#6a6474', fontSize: '0.65rem', marginTop: '6px' }}>Emotions: {brief.emotions}</div>
              )}
            </>
          ) : (
            <div style={{ color: '#6a6474', fontSize: '0.7rem' }}>No recent journals.</div>
          )}
        </div>

        <div className="card" style={{ padding: '14px' }}>
          <div style={{ color: '#c49ea4', fontWeight: 600, fontSize: '0.75rem', marginBottom: '8px' }}>JOURNAL SUMMARY</div>
          {brief?.ai_analysis?.explanation ? (
            <div style={{ color: '#9aa8c0', fontSize: '0.72rem', lineHeight: 1.6 }}>{brief.ai_analysis.explanation.slice(0, 300)}</div>
          ) : (
            <div style={{ color: '#6a6474', fontSize: '0.7rem' }}>No summary available.</div>
          )}
          {brief?.ai_analysis && (
            <div style={{ color: '#5a5464', fontSize: '0.58rem', marginTop: '8px', lineHeight: 1.6 }}>
              AI: {brief.ai_analysis.provider || 'rule'} &middot; prompt {brief.ai_analysis.prompt_version || 'rule'}
              {brief.ai_analysis.model_version ? ` · model v${brief.ai_analysis.model_version}` : ''}
              {brief.ai_analysis.confidence ? ` · confidence ${(brief.ai_analysis.confidence * 100).toFixed(0)}%` : ''}
            </div>
          )}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        <div className="card" style={{ padding: '14px' }}>
          <div style={{ color: '#c49ea4', fontWeight: 600, fontSize: '0.75rem', marginBottom: '8px' }}>{'\u270D\uFE0F'} SESSION NOTE</div>
          <textarea
            value={rawNotes}
            onChange={e => setRawNotes(e.target.value)}
            placeholder="Enter session observations..."
            rows={6}
            style={{ width: '100%', padding: '12px', fontSize: '0.875rem', resize: 'none', marginBottom: '10px' }}
          />
          <div style={{ display: 'flex', gap: '8px' }}>
            <button onClick={saveNote} disabled={saving || !selected || !rawNotes.trim()} className="btn-primary">
              {saving ? 'Saving...' : '💾 Save Note'}
            </button>
            <button onClick={generateAiDraft} disabled={!selected || !rawNotes.trim()} style={{
              background: '#1e2336', border: '1px solid #2d2d44', color: '#c49ea4',
              padding: '8px 16px', borderRadius: '8px', fontSize: '0.8125rem', cursor: 'pointer', fontWeight: 600,
            }}>
              🤖 AI Draft
            </button>
          </div>
          {aiDraft && (
            <div className="ai-box" style={{ marginTop: '10px' }}>
              <div className="ai-header">🤖 AI Clinical Draft</div>
              <div className="ai-body" style={{ fontSize: '0.75rem', whiteSpace: 'pre-wrap' }}>{aiDraft.note || aiDraft.suggestion}</div>
            </div>
          )}
        </div>

        <div className="card" style={{ padding: '14px' }}>
          <div style={{ color: '#c49ea4', fontWeight: 600, fontSize: '0.75rem', marginBottom: '8px' }}>{'\u2705'} FOLLOW-UP ACTIONS</div>
          {followupList.filter((f: any) => f.status === 'pending').length === 0 ? (
            <div style={{ color: '#6a6474', fontSize: '0.7rem' }}>No pending follow-ups. All caught up!</div>
          ) : (
            followupList.filter((f: any) => f.status === 'pending').map((f: any) => (
              <div key={f.id} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 0', borderBottom: '1px solid #2d2d44' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ color: '#e0e8f0', fontSize: '0.75rem', fontWeight: 600 }}>{f.title}</div>
                  <div style={{ color: '#6a6474', fontSize: '0.62rem' }}>
                    assigned {f.assigned_at ? formatDate(f.assigned_at) : '—'}{f.grade ? ` · ${f.grade}` : ''}
                  </div>
                </div>
                <button
                  onClick={() => completeFollowup(f.id)}
                  disabled={updating === f.id}
                  style={{ background: '#1e2336', border: '1px solid #2d2d44', color: '#22c55e', padding: '5px 10px', borderRadius: '6px', fontSize: '0.65rem', cursor: 'pointer', fontWeight: 600, whiteSpace: 'nowrap' }}
                >
                  {updating === f.id ? '...' : '\u2705 Complete'}
                </button>
              </div>
            ))
          )}
          {followupList.filter((f: any) => f.status === 'completed').length > 0 && (
            <div style={{ marginTop: '8px', fontSize: '0.62rem', color: '#6a6474' }}>
              {followupList.filter((f: any) => f.status === 'completed').length} completed
            </div>
          )}
        </div>
      </div>

      {(overview.mood_trend || []).length > 0 && (
        <div className="card" style={{ padding: '10px', marginTop: '16px' }}>
          <div style={{ color: '#6a6474', fontSize: '0.6rem', marginBottom: '4px' }}>MOOD TREND (14d)</div>
          <div style={{ display: 'flex', gap: '3px' }}>
            {(overview.mood_trend || []).map((m: any, i: number) => (
              <span key={i} style={{ fontSize: '0.9rem' }} title={`${m.label} ${formatDate(m.timestamp)}`}>{moodIcon(m.label)}</span>
            ))}
          </div>
        </div>
      )}
    </>
  )
}

function Snapshot({ label, value, sub, color }: { label: string; value: string; sub: string; color: string }) {
  return (
    <div className="card" style={{ padding: '10px', minWidth: 0 }}>
      <div style={{ color: '#6a6474', fontSize: '0.6rem', marginBottom: '3px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{label}</div>
      <div style={{ color, fontSize: '0.9rem', fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{value}</div>
      <div style={{ color: '#7a8aaa', fontSize: '0.6rem', marginTop: '2px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{sub}</div>
    </div>
  )
}
