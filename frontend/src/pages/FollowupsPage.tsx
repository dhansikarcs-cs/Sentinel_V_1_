import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { getUser } from '../stores/auth'
import { todayStr } from '../constants'
import PatientSelector from '../components/PatientSelector'

export default function FollowupsPage() {
  const user = getUser()
  if (user?.role === 'psychologist') return <PsychFollowups />
  return <PatientFollowups />
}

const STATUS_BADGE: Record<string, { label: string; color: string; bg: string }> = {
  pending: { label: 'â³ Pending', color: '#A66E0C', bg: 'rgba(251,191,36,0.12)' },
  completed: { label: 'âœ… Completed', color: '#2E8B57', bg: 'rgba(46,139,87,0.12)' },
  skipped: { label: 'âŒ Skipped', color: '#C7463B', bg: 'rgba(199,70,59,0.12)' },
}

function dueInfo(due?: string): { text: string; color: string } | null {
  if (!due) return null
  const today = todayStr()
  if (due < today) return { text: `Overdue Â· ${due}`, color: '#C7463B' }
  if (due === today) return { text: `Due today Â· ${due}`, color: '#A66E0C' }
  return { text: `Due ${due}`, color: '#5F7A70' }
}

function PatientFollowups() {
  const [tasks, setTasks] = useState<any[]>([])
  const [uploadingProof, setUploadingProof] = useState<Record<string, File | null>>({})
  const [busy, setBusy] = useState<Record<string, boolean>>({})

  useEffect(() => { api.getFollowups().then(d => setTasks(d || [])).catch(() => {}) }, [])

  const myTasks = (tasks || []).filter((t: any) => t.patient_username === getUser()?.username)

  async function refresh() {
    try { setTasks((await api.getFollowups()) || []) } catch {}
  }

  async function run(action: string, id: string, fn: () => Promise<any>) {
    setBusy(b => ({ ...b, [id]: true }))
    try { await fn(); await refresh() } catch {} finally {
      setBusy(b => ({ ...b, [id]: false }))
    }
  }

  if (myTasks.length === 0) return (
    <div className="animate-fade-in">
      <h2>ðŸ“‹ My Follow-Up Tasks</h2>
      <div className="card"><span style={{ color: '#6E837A', fontSize: '0.875rem' }}>No tasks assigned yet.</span></div>
    </div>
  )

  return (
    <div className="animate-fade-in">
      <h2>ðŸ“‹ My Follow-Up Tasks</h2>
      <div className="space-y-3">
        {myTasks.slice().reverse().map((t: any) => {
          const badge = STATUS_BADGE[t.status] || STATUS_BADGE.pending
          const due = dueInfo(t.due_date)
          const proof = uploadingProof[t.id]
          return (
            <div key={t.id} style={{ border: '1px solid #D9E7E3', borderRadius: '10px', padding: '14px', background: '#F4F9F8', marginBottom: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', flexWrap: 'wrap' }}>
                <div style={{ fontWeight: 600 }}>{t.title}</div>
                <span style={{ marginLeft: 'auto', fontSize: '0.62rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: badge.color, background: badge.bg, padding: '3px 8px', borderRadius: '999px' }}>{badge.label}</span>
              </div>
              {t.description && <div style={{ color: '#5F7A70', fontSize: '0.8125rem', marginBottom: '8px' }}>{t.description}</div>}

              {due && <div style={{ fontSize: '0.6875rem', color: due.color, marginBottom: '8px' }}>{due.text}</div>}

              {t.file_path && (
                <div style={{ marginBottom: '8px' }}>
                  <a href={`/api/followups/${t.id}/download`} target="_blank" rel="noreferrer"
                    style={{ color: '#17796E', fontSize: '0.75rem' }}>
                    ðŸ“Ž {t.status === 'completed' ? 'View my submission' : 'View attachment'}
                  </a>
                </div>
              )}

              {t.status === 'pending' && (
                <div>
                  <div style={{ display: 'flex', gap: '6px', alignItems: 'center', marginTop: '8px', flexWrap: 'wrap' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.7rem', color: '#7C9188', flex: 1, minWidth: '140px' }}>
                      <span>ðŸ“Ž</span>
                      <input type="file" onChange={e => setUploadingProof({ ...uploadingProof, [t.id]: e.target.files?.[0] || null })}
                        style={{ fontSize: '0.7rem', color: '#7C9188' }} />
                    </label>
                    <button className="btn-primary" style={{ fontSize: '0.7rem', padding: '5px 10px' }}
                      disabled={!proof || busy[t.id]}
                      onClick={() => run('proof', t.id, () => api.uploadFollowupProof(t.id, proof!))}>
                      {busy[t.id] ? 'â€¦' : proof ? 'ðŸ“¤ Submit with proof' : 'Submit with proof'}
                    </button>
                    <button style={{ fontSize: '0.7rem', padding: '5px 10px' }}
                      disabled={busy[t.id]}
                      onClick={() => run('done', t.id, () => api.updateFollowup(t.id, { status: 'completed', grade: 'none' }))}>
                      âœ… Mark done
                    </button>
                    <button style={{ fontSize: '0.7rem', padding: '5px 10px' }}
                      disabled={busy[t.id]}
                      onClick={() => run('skip', t.id, () => api.updateFollowup(t.id, { status: 'skipped', grade: 'none' }))}>
                      âŒ Skip
                    </button>
                  </div>
                </div>
              )}

              {t.status === 'completed' && (
                <div>
                  {t.grade && t.grade !== 'none' ? (
                    <div style={{ color: t.grade === 'green' ? '#44ff44' : t.grade === 'yellow' ? '#ffd93d' : '#C64537', fontWeight: 'bold', fontSize: '14px' }}>
                      {t.grade === 'green' ? 'ðŸŸ¢ Correctly done' : t.grade === 'yellow' ? 'ðŸŸ¡ Partially done' : 'ðŸ”´ Needs improvement'}
                    </div>
                  ) : (
                    <div style={{ color: '#2E8B57', fontSize: '0.8125rem', fontWeight: 600 }}>âœ… Submitted â€” awaiting review</div>
                  )}
                  {t.feedback ? (
                    <div style={{ marginTop: '8px', padding: '10px 12px', borderRadius: '8px', background: 'rgba(23,121,110,0.08)', border: '1px solid rgba(23,121,110,0.25)' }}>
                      <div style={{ color: '#17796E', fontSize: '0.65rem', fontWeight: 600, marginBottom: '4px' }}>ðŸ’¬ Feedback from your psychologist</div>
                      <div style={{ color: '#3A4F52', fontSize: '0.8125rem', lineHeight: 1.5 }}>{t.feedback}</div>
                    </div>
                  ) : t.grade && t.grade !== 'none' ? (
                    <div style={{ color: '#6E837A', fontSize: '0.6875rem', marginTop: '6px' }}>No written feedback yet.</div>
                  ) : null}
                </div>
              )}

              {t.status === 'skipped' && <div style={{ color: '#C7463B' }}>âŒ Not completed</div>}

              <div style={{ color: '#6E837A', fontSize: '0.6875rem', marginTop: '8px' }}>Assigned: {t.assigned_at?.slice(0, 10)}</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function PsychFollowups() {
  const [tasks, setTasks] = useState<any[]>([])
  const [patients, setPatients] = useState<any[]>([])
  const [expanded, setExpanded] = useState<Record<number, boolean>>({})
  const [newPatient, setNewPatient] = useState('')
  const [newTitle, setNewTitle] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [newDue, setNewDue] = useState('')
  const [newFile, setNewFile] = useState<File | null>(null)
  const [showAssign, setShowAssign] = useState(false)
  const [aiPatient, setAiPatient] = useState('')
  const [agentResult, setAgentResult] = useState<any>(null)
  const [agentBusy, setAgentBusy] = useState(false)
  const [assigningId, setAssigningId] = useState<number | null>(null)
  const [assignedId, setAssignedId] = useState<number | null>(null)
  const [busy, setBusy] = useState<Record<string, boolean>>({})
  const [feedbackBuf, setFeedbackBuf] = useState<Record<string, string>>({})
  const [feedbackSaved, setFeedbackSaved] = useState<Record<string, boolean>>({})

  useEffect(() => {
    api.getFollowups().then(d => setTasks(d || [])).catch(() => {})
    api.getPsychPatients().then(d => setPatients(d || [])).catch(() => {})
  }, [])

  const myTasks = (tasks || []).filter((t: any) => t.psychologist_username === getUser()?.username)

  async function refresh() {
    try { setTasks((await api.getFollowups()) || []) } catch {}
  }

  async function run(id: string, fn: () => Promise<any>) {
    setBusy(b => ({ ...b, [id]: true }))
    try { await fn(); await refresh() } catch {} finally {
      setBusy(b => ({ ...b, [id]: false }))
    }
  }

  async function assignTask() {
    if (!newPatient || !newTitle.trim()) return
    try {
      const task = await api.createFollowup({ patient_username: newPatient, title: newTitle, description: newDesc, due_date: newDue })
      if (newFile && task?.id) {
        await api.uploadFollowupAttachment(task.id, newFile)
      }
      setNewTitle(''); setNewDesc(''); setNewDue(''); setNewFile(null)
      await refresh()
      setShowAssign(false)
    } catch {}
  }

  async function analyze() {
    if (!aiPatient) return
    setAgentBusy(true); setAssignedId(null)
    try {
      const result = await api.draftFollowup(aiPatient)
      setAgentResult(result)
    } catch {} finally { setAgentBusy(false) }
  }

  async function assignDraft(i: number, task: any) {
    setAssigningId(i)
    try {
      await api.createFollowup({ patient_username: aiPatient, title: task.title, description: task.description, due_date: newDue || '' })
      setAssignedId(i)
      await refresh()
    } catch {} finally { setAssigningId(null) }
  }

  async function gradeTask(id: string, grade: string) {
    await run(`grade:${id}`, () => api.updateFollowup(id, { grade, status: 'completed' }))
  }

  async function saveFeedback(id: string, currentGrade: string) {
    const feedback = (feedbackBuf[id] ?? '').trim()
    const grade = currentGrade && currentGrade !== '' ? currentGrade : 'none'
    await run(`feedback:${id}`, () => api.updateFollowup(id, { feedback, grade, status: 'completed' }))
    setFeedbackSaved({ ...feedbackSaved, [id]: true })
  }

  const gradeBorders: Record<string, string> = {
    green: '#44ff44', yellow: '#ffd93d', red: '#C64537', none: '#D9E7E3',
  }

  return (
    <div className="animate-fade-in">
      <h2>ðŸ“‹ Follow-Up Tasks</h2>
      <div style={{ display: 'grid', gridTemplateColumns: '3fr 1fr', gap: '24px' }}>
        <div>
          <div className="expander" style={{ borderColor: showAssign ? '#17796E' : '#D9E7E3' }}>
            <div className="expander-header" onClick={() => setShowAssign(!showAssign)}>
              <span>âž• Assign New Task</span><span>{showAssign ? 'â–²' : 'â–¼'}</span>
            </div>
            {showAssign && (
              <div className="expander-body">
                <div style={{ display: 'flex', gap: '12px', marginBottom: '8px' }}>
                  <div style={{ flex: 1 }}>
                    <label>Patient</label>
                    <PatientSelector patients={patients} value={newPatient} onChange={setNewPatient} placeholder="Select..." />
                  </div>
                  <div style={{ flex: 2 }}>
                    <label>Task title</label>
                    <input value={newTitle} onChange={e => setNewTitle(e.target.value)} placeholder="e.g. Breathing exercise" />
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '12px', marginBottom: '8px' }}>
                  <div style={{ flex: 2 }}>
                    <label>Description</label>
                    <textarea value={newDesc} onChange={e => setNewDesc(e.target.value)} placeholder="What should the patient do?" rows={3} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <label>Due date (optional)</label>
                    <input type="date" value={newDue} onChange={e => setNewDue(e.target.value)} style={{ width: '100%' }} />
                    <div style={{ marginTop: '8px' }}>
                      <label>Attachment (optional)</label>
                      <input type="file" onChange={e => setNewFile(e.target.files?.[0] || null)}
                        style={{ width: '100%', fontSize: '0.8rem', color: '#7C9188' }} />
                    </div>
                  </div>
                </div>
                <button className="btn-primary" onClick={assignTask} style={{ marginTop: '8px', width: '100%' }}>ðŸ“ Assign Task</button>
              </div>
            )}
          </div>

          <h3 style={{ marginTop: '16px' }}>Assigned Tasks</h3>
          {myTasks.length === 0 ? (
            <div className="card"><span style={{ color: '#6E837A', fontSize: '0.875rem' }}>No tasks assigned yet.</span></div>
          ) : (
            <div className="space-y-2">
              {myTasks.slice().reverse().map((t: any) => {
                const open = expanded[t.id]
                const borderColor = t.status === 'completed' && t.grade && t.grade !== 'none'
                  ? gradeBorders[t.grade] || '#D9E7E3' : '#D9E7E3'
                const due = dueInfo(t.due_date)
                return (
                  <div key={t.id} className="expander" style={{ borderColor }}>
                    <div className="expander-header" onClick={() => setExpanded({ ...expanded, [t.id]: !open })}>
                      <span>{t.title} â†’ {t.patient_username}</span>
                      <span>{open ? 'â–²' : 'â–¼'}</span>
                    </div>
                    {open && (
                      <div className="expander-body">
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '4px', flexWrap: 'wrap' }}>
                          <div style={{ fontSize: '0.8125rem' }}><strong>Patient:</strong> {t.patient_username}</div>
                          <span style={{ marginLeft: 'auto', fontSize: '0.62rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: STATUS_BADGE[t.status]?.color, background: STATUS_BADGE[t.status]?.bg, padding: '3px 8px', borderRadius: '999px' }}>
                            {STATUS_BADGE[t.status]?.label}
                          </span>
                        </div>
                        <div style={{ color: '#5F7A70', fontSize: '0.8125rem', marginBottom: '8px' }}>{t.description}</div>
                        {due && <div style={{ fontSize: '0.6875rem', color: due.color, marginBottom: '8px' }}>{due.text}</div>}

                        {t.file_path && (
                          <div style={{ marginBottom: '8px' }}>
                            <a href={`/api/followups/${t.id}/download`} target="_blank" rel="noreferrer"
                              style={{ color: '#17796E', fontSize: '0.75rem' }}>
                              {t.status === 'completed' ? 'ðŸ“¤ View Proof' : 'ðŸ“Ž View Attachment'}
                            </a>
                          </div>
                        )}

                        {t.status === 'completed' && (
                          <div>
                            <hr style={{ margin: '8px 0' }} />
                            <div style={{ fontWeight: 600, fontSize: '0.8125rem', marginBottom: '8px' }}>
                              Grade & Feedback
                              {t.grade && t.grade !== 'none' && (
                                <span style={{ color: gradeBorders[t.grade], fontWeight: 700, marginLeft: '8px' }}>
                                  {t.grade === 'green' ? 'ðŸŸ¢ Correct' : t.grade === 'yellow' ? 'ðŸŸ¡ Partial' : 'ðŸ”´ Needs improvement'}
                                </span>
                              )}
                            </div>
                            <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '10px', flexWrap: 'wrap' }}>
                              <button style={{ fontSize: '0.75rem', padding: '6px 12px' }} disabled={busy[`grade:${t.id}`]} onClick={() => gradeTask(t.id, 'green')}>ðŸŸ¢ Correct</button>
                              <button style={{ fontSize: '0.75rem', padding: '6px 12px' }} disabled={busy[`grade:${t.id}`]} onClick={() => gradeTask(t.id, 'yellow')}>ðŸŸ¡ Partial</button>
                              <button style={{ fontSize: '0.75rem', padding: '6px 12px' }} disabled={busy[`grade:${t.id}`]} onClick={() => gradeTask(t.id, 'red')}>ðŸ”´ Needs work</button>
                              {t.grade && t.grade !== 'none' && (
                                <span style={{ color: '#6E837A', fontSize: '0.6875rem' }}>Tap to change grade</span>
                              )}
                            </div>
                            <label style={{ fontSize: '0.6875rem', color: '#7C9188', display: 'block', marginBottom: '4px' }}>Written feedback for {t.patient_username}</label>
                            <textarea
                              value={feedbackBuf[t.id] ?? t.feedback ?? ''}
                              onChange={e => { setFeedbackBuf({ ...feedbackBuf, [t.id]: e.target.value }); setFeedbackSaved({ ...feedbackSaved, [t.id]: false }) }}
                              rows={3}
                              placeholder="e.g. Nice work on the breathing exercise â€” notice how calm you felt after. Let's build on this next week."
                              style={{ width: '100%', fontSize: '0.8125rem', resize: 'vertical', marginBottom: '6px' }}
                            />
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                              <button className="btn-primary" style={{ fontSize: '0.72rem', padding: '6px 12px' }}
                                disabled={busy[`feedback:${t.id}`]}
                                onClick={() => saveFeedback(t.id, t.grade || 'none')}>
                                {busy[`feedback:${t.id}`] ? 'Savingâ€¦' : 'ðŸ’¬ Save Feedback'}
                              </button>
                              {feedbackSaved[t.id] && (
                                <span style={{ color: '#2E8B57', fontSize: '0.6875rem' }}>âœ“ Saved â€” visible to the patient</span>
                              )}
                            </div>
                          </div>
                        )}

                        <div style={{ color: '#6E837A', fontSize: '0.6875rem', marginTop: '8px' }}>Assigned: {t.assigned_at?.slice(0, 10)}{t.due_date ? ` Â· Due: ${t.due_date}` : ''}</div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>

        <div className="psych-box">
          <div className="psych-box-title">ðŸ¤– Follow-Up Agent</div>
          <div className="psych-box-desc">AI-powered task drafting</div>
          <PatientSelector patients={patients} value={aiPatient} onChange={setAiPatient} placeholder="Select patient..." style={{ marginBottom: '8px', fontSize: '0.8125rem', padding: '8px' }} />
          <button onClick={analyze} disabled={!aiPatient || agentBusy} className="btn-primary" style={{ width: '100%', fontSize: '0.8125rem' }}>
            {agentBusy ? 'Analyzingâ€¦' : 'Analyze & Draft Tasks'}
          </button>

          {agentResult && (
            <div className="ai-box" style={{ marginTop: '8px' }}>
              <div style={{ color: '#6E837A', fontSize: '0.6875rem', marginBottom: '6px' }}>{agentResult.reasoning}</div>
              {agentResult.tasks?.map((task: any, i: number) => (
                <div key={i} className="card" style={{ margin: '6px 0', padding: '10px' }}>
                  <div style={{ color: '#17796E', fontSize: '0.8125rem', fontWeight: 600 }}>{task.title}</div>
                  <div style={{ color: '#7C9188', fontSize: '0.75rem', marginTop: '4px' }}>{task.description}</div>
                  {assignedId === i ? (
                    <div style={{ color: '#2E8B57', fontSize: '0.7rem', fontWeight: 600, marginTop: '6px' }}>âœ… Assigned to {aiPatient}</div>
                  ) : (
                    <button style={{ fontSize: '0.6875rem', padding: '4px 10px', marginTop: '6px' }}
                      disabled={assigningId !== null || !aiPatient}
                      onClick={() => assignDraft(i, task)}>
                      {assigningId === i ? 'Assigningâ€¦' : 'ðŸ“ Assign Now'}
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
