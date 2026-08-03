import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { getUser } from '../stores/auth'

export default function FollowupsPage() {
  const user = getUser()
  if (user?.role === 'psychologist') return <PsychFollowups />
  return <PatientFollowups />
}

function PatientFollowups() {
  const [tasks, setTasks] = useState<any[]>([])
  const [uploadingProof, setUploadingProof] = useState<Record<string, File | null>>({})

  useEffect(() => { api.getFollowups().then(d => setTasks(d || [])).catch(() => {}) }, [])

  const myTasks = (tasks || []).filter((t: any) => t.patient_username === getUser()?.username)

  if (myTasks.length === 0) return (
    <div className="animate-fade-in">
      <h2>📋 My Follow-Up Tasks</h2>
      <div className="card"><span style={{ color: '#6a6474', fontSize: '0.875rem' }}>No tasks assigned yet.</span></div>
    </div>
  )

  async function uploadProofAndComplete(taskId: string) {
    const file = uploadingProof[taskId]
    if (!file) return
    const formData = new FormData()
    formData.append('file', file)
    try {
      const res = await fetch(`/api/followups/${taskId}/upload-proof`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
        body: formData,
      })
      if (res.ok) setTasks((await api.getFollowups()) || [])
    } catch {}
  }

  return (
    <div className="animate-fade-in">
      <h2>📋 My Follow-Up Tasks</h2>
      <div className="space-y-3">
        {myTasks.slice().reverse().map((t: any) => {
          let borderColor = '#ffa500'
          if (t.status === 'pending') borderColor = '#ffa500'
          else if (t.status === 'completed') {
            borderColor = t.grade === 'green' ? '#44ff44' : t.grade === 'yellow' ? '#ffd93d' : t.grade === 'red' ? '#ff4444' : '#44ff44'
          } else if (t.status === 'skipped') borderColor = '#ff4444'

          return (
            <div key={t.id} style={{ border: `1px solid ${borderColor}`, borderRadius: '10px', padding: '14px', background: '#161d30', marginBottom: '10px' }}>
              <div style={{ fontWeight: 600, marginBottom: '4px' }}>{t.title}</div>
              {t.description && <div style={{ color: '#7a8aaa', fontSize: '0.8125rem', marginBottom: '8px' }}>{t.description}</div>}

              {t.file_path && (
                <div style={{ marginBottom: '8px' }}>
                  <a href={`/api/followups/${t.id}/download`} target="_blank" rel="noreferrer"
                    style={{ color: '#c49ea4', fontSize: '0.75rem' }}>
                    📎 View Attachment
                  </a>
                </div>
              )}

              {t.status === 'pending' && (
                <div>
                  <div style={{ display: 'flex', gap: '6px', alignItems: 'center', marginTop: '8px', flexWrap: 'wrap' }}>
                    <input type="file" onChange={e => setUploadingProof({ ...uploadingProof, [t.id]: e.target.files?.[0] || null })}
                      style={{ fontSize: '0.7rem', color: '#9a92a2', flex: 1, minWidth: '100px' }} />
                    <button className="btn-primary" style={{ fontSize: '0.7rem', padding: '5px 10px' }}
                      onClick={() => uploadProofAndComplete(t.id)}
                      disabled={!uploadingProof[t.id]}>📤 Upload & Done</button>
                    <button style={{ fontSize: '0.7rem', padding: '5px 10px' }}
                      onClick={async () => {
                        try {
                          await api.updateFollowup(t.id, { status: 'completed', grade: 'none' })
                           setTasks((await api.getFollowups()) || [])
                        } catch {}
                      }}>✅ Mark Done</button>
                    <button style={{ fontSize: '0.7rem', padding: '5px 10px' }}
                      onClick={async () => {
                        try {
                          await api.updateFollowup(t.id, { status: 'skipped', grade: 'none' })
                           setTasks((await api.getFollowups()) || [])
                        } catch {}
                      }}>❌ Skip</button>
                  </div>
                </div>
              )}

              {t.status === 'completed' && (
                <div>
                  <div style={{ color: '#22c55e', fontSize: '0.8125rem', fontWeight: 600 }}>✅ Completed</div>
                  {t.grade && t.grade !== 'none' && (
                    <div style={{ color: t.grade === 'green' ? '#44ff44' : t.grade === 'yellow' ? '#ffd93d' : '#ff4444', fontWeight: 'bold', fontSize: '15px' }}>
                      {t.grade === 'green' ? '🟢 Correctly done' : t.grade === 'yellow' ? '🟡 Partially done' : '🔴 Needs improvement'}
                    </div>
                  )}
                </div>
              )}

              {t.status === 'skipped' && <div style={{ color: '#ef4444' }}>❌ Not Completed</div>}

              <div style={{ color: '#6a6474', fontSize: '0.6875rem', marginTop: '8px' }}>Assigned: {t.assigned_at?.slice(0, 10)}</div>
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
  const [newFile, setNewFile] = useState<File | null>(null)
  const [showAssign, setShowAssign] = useState(false)
  const [aiPatient, setAiPatient] = useState('')
  const [agentResult, setAgentResult] = useState<any>(null)
  const [feedbackBuf, setFeedbackBuf] = useState<Record<string, string>>({})

  useEffect(() => {
    api.getFollowups().then(d => setTasks(d || [])).catch(() => {})
    api.getPsychPatients().then(d => setPatients(d || [])).catch(() => {})
  }, [])

  const myTasks = (tasks || []).filter((t: any) => t.psychologist_username === getUser()?.username)

  async function assignTask() {
    if (!newPatient || !newTitle.trim()) return
    try {
      const task = await api.createFollowup({ patient_username: newPatient, title: newTitle, description: newDesc })
      if (newFile && task?.id) {
        const formData = new FormData()
        formData.append('file', newFile)
        await fetch(`/api/followups/${task.id}/upload`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
          body: formData,
        })
      }
      setNewTitle(''); setNewDesc(''); setNewFile(null)
      setTasks((await api.getFollowups()) || [])
      setShowAssign(false)
    } catch {}
  }

  async function analyze() {
    if (!aiPatient) return
    try {
      const result = await api.draftFollowup(aiPatient)
      setAgentResult(result)
    } catch {}
  }

  async function gradeTask(id: string, grade: string) {
    try {
      await api.updateFollowup(id, { grade, status: 'completed' })
      setTasks((await api.getFollowups()) || [])
    } catch {}
  }

  const gradeBorders: Record<string, string> = {
    green: '#44ff44', yellow: '#ffd93d', red: '#ff4444', none: '#2d2d44',
  }

  return (
    <div className="animate-fade-in">
      <h2>📋 Follow-Up Tasks</h2>
      <div style={{ display: 'grid', gridTemplateColumns: '3fr 1fr', gap: '24px' }}>
        <div>
          <div className="expander" style={{ borderColor: showAssign ? '#c49ea4' : '#2d2d44' }}>
            <div className="expander-header" onClick={() => setShowAssign(!showAssign)}>
              <span>➕ Assign New Task</span><span>{showAssign ? '▲' : '▼'}</span>
            </div>
            {showAssign && (
              <div className="expander-body">
                <div style={{ display: 'flex', gap: '12px', marginBottom: '8px' }}>
                  <div style={{ flex: 1 }}>
                    <label>Patient</label>
                    <select value={newPatient} onChange={e => setNewPatient(e.target.value)}>
                      <option value="">Select...</option>
                      {patients.map((p: any) => (
                        <option key={p.username || p} value={p.username || p}>{p.name || p}</option>
                      ))}
                    </select>
                  </div>
                  <div style={{ flex: 2 }}>
                    <label>Task title</label>
                    <input value={newTitle} onChange={e => setNewTitle(e.target.value)} placeholder="e.g. Breathing exercise" />
                  </div>
                </div>
                <div style={{ marginBottom: '8px' }}>
                  <label>Description</label>
                  <textarea value={newDesc} onChange={e => setNewDesc(e.target.value)} placeholder="What should the patient do?" rows={3} />
                </div>
                <div style={{ marginBottom: '8px' }}>
                  <label>Attachment (optional)</label>
                  <input type="file" onChange={e => setNewFile(e.target.files?.[0] || null)}
                    style={{ width: '100%', fontSize: '0.8rem', color: '#9a92a2' }} />
                </div>
                <button className="btn-primary" onClick={assignTask} style={{ marginTop: '8px', width: '100%' }}>📝 Assign Task</button>
              </div>
            )}
          </div>

          <h3 style={{ marginTop: '16px' }}>Assigned Tasks</h3>
          {myTasks.length === 0 ? (
            <div className="card"><span style={{ color: '#6a6474', fontSize: '0.875rem' }}>No tasks assigned yet.</span></div>
          ) : (
            <div className="space-y-2">
              {myTasks.slice().reverse().map((t: any) => {
                const open = expanded[t.id]
                const borderColor = t.status === 'completed' && t.grade && t.grade !== 'none'
                  ? gradeBorders[t.grade] || '#2d2d44' : '#2d2d44'
                return (
                  <div key={t.id} className="expander" style={{ borderColor }}>
                    <div className="expander-header" onClick={() => setExpanded({ ...expanded, [t.id]: !open })}>
                      <span>{t.title} → {t.patient_username}</span>
                      <span>{open ? '▲' : '▼'}</span>
                    </div>
                    {open && (
                      <div className="expander-body">
                        <div style={{ fontSize: '0.8125rem', marginBottom: '4px' }}><strong>Patient:</strong> {t.patient_username}</div>
                        <div style={{ color: '#7a8aaa', fontSize: '0.8125rem', marginBottom: '8px' }}>{t.description}</div>
                        <div style={{ color: '#6a6474', fontSize: '0.75rem', marginBottom: '8px' }}>Status: <strong>{t.status === 'pending' ? '⏳ PENDING' : t.status === 'completed' ? '✅ COMPLETED' : '❌ SKIPPED'}</strong></div>

                        {t.file_path && (
                          <div style={{ marginBottom: '8px' }}>
                            <a href={`/api/followups/${t.id}/download`} target="_blank" rel="noreferrer"
                              style={{ color: '#c49ea4', fontSize: '0.75rem' }}>
                              {t.status === 'completed' ? '📤 View Proof' : '📎 View Attachment'}
                            </a>
                          </div>
                        )}

                        {t.status === 'completed' && (
                          <div>
                            <hr style={{ margin: '8px 0' }} />
                            <div style={{ fontWeight: 600, fontSize: '0.8125rem', marginBottom: '8px' }}>Grade & Feedback</div>
                            {(!t.grade || t.grade === 'none') ? (
                              <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                                <button style={{ fontSize: '0.75rem', padding: '6px 12px' }} onClick={() => gradeTask(t.id, 'green')}>🟢 Correct</button>
                                <button style={{ fontSize: '0.75rem', padding: '6px 12px' }} onClick={() => gradeTask(t.id, 'yellow')}>🟡 Partial</button>
                                <button style={{ fontSize: '0.75rem', padding: '6px 12px' }} onClick={() => gradeTask(t.id, 'red')}>🔴 Wrong</button>
                              </div>
                            ) : (
                              <div style={{ color: gradeBorders[t.grade], fontWeight: 'bold', fontSize: '14px', marginBottom: '8px' }}>
                                {t.grade === 'green' ? '🟢 Correctly done' : t.grade === 'yellow' ? '🟡 Partially done' : '🔴 Needs improvement'} <span style={{ color: '#6a6474', fontWeight: 400, fontSize: '0.75rem' }}>(locked)</span>
                              </div>
                            )}
                          </div>
                        )}

                        <div style={{ color: '#6a6474', fontSize: '0.6875rem', marginTop: '8px' }}>Assigned: {t.assigned_at?.slice(0, 10)}</div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>

        <div className="psych-box">
          <div className="psych-box-title">🤖 Follow-Up Agent</div>
          <div className="psych-box-desc">AI-powered task drafting</div>
          <select value={aiPatient} onChange={e => setAiPatient(e.target.value)} style={{ marginBottom: '8px', fontSize: '0.8125rem', padding: '8px' }}>
            <option value="">Select patient...</option>
            {patients.map((p: any) => (
              <option key={p.username || p} value={p.username || p}>{p.name || p}</option>
            ))}
          </select>
          <button onClick={analyze} className="btn-primary" style={{ width: '100%', fontSize: '0.8125rem' }}>Analyze & Draft Tasks</button>

          {agentResult && (
            <div className="ai-box" style={{ marginTop: '8px' }}>
              <div style={{ color: '#6a6474', fontSize: '0.6875rem', marginBottom: '6px' }}>{agentResult.reasoning}</div>
              {agentResult.tasks?.map((task: any, i: number) => (
                <div key={i} className="card" style={{ margin: '6px 0', padding: '10px' }}>
                  <div style={{ color: '#c49ea4', fontSize: '0.8125rem', fontWeight: 600 }}>{task.title}</div>
                  <div style={{ color: '#9a92a2', fontSize: '0.75rem', marginTop: '4px' }}>{task.description}</div>
                  <button style={{ fontSize: '0.6875rem', padding: '4px 10px', marginTop: '6px' }}
                    onClick={() => { setNewPatient(aiPatient); setNewTitle(task.title); setNewDesc(task.description); setShowAssign(true) }}>
                    Fill Form
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
