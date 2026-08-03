import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { sourceColor } from '../constants'

function MetricCard({ label, value, unit, color }: { label: string; value: string; unit: string; color: string }) {
  return (
    <div style={{
      background: `linear-gradient(135deg, ${color}22, ${color}11)`,
      padding: '14px',
      borderRadius: '10px',
      border: `1px solid ${color}44`,
      textAlign: 'center',
    }}>
      <div style={{ color: '#889', fontSize: '12px' }}>{label}</div>
      <div style={{ color: 'white', fontSize: '24px', fontWeight: 700 }}>{value}</div>
      <div style={{ color: '#889', fontSize: '11px' }}>{unit}</div>
    </div>
  )
}

export default function PsychTriagePage() {
  const [patients, setPatients] = useState<any[]>([])
  const [priorities, setPriorities] = useState<any[]>([])
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const [showTable, setShowTable] = useState<Record<string, boolean>>({})
  const [riskAssessments, setRiskAssessments] = useState<Record<string, any>>({})
  const [explainOpen, setExplainOpen] = useState<Record<string, boolean>>({})

  useEffect(() => {
    api.getPsychPatients().then(async (pts) => {
      setPatients(pts || [])
      if (pts?.length) {
        const results = await Promise.allSettled(
          pts.map((p: any) => api.triageSummary(p.username || p).catch(() => null))
        )
        const computed = pts.map((p: any, i: any) => {
          const result = results[i]?.status === 'fulfilled' ? results[i].value : null
          const tier: string = result?.tier || 'stable'
          const crisis: boolean = result?.crisis ?? false
          const score: number = result?.priority_score ?? 0
          return { patient: p.username || p, name: p.name || p, score, tier, crisis, ...(result || {}) }
        })
        computed.sort((a: any, b: any) => b.score - a.score)
        setPriorities(computed)
      }
    }).catch(() => {})
  }, [])

  const counts: Record<string, number> = { crisis: 0, high: 0, attention: 0, stable: 0 }
  priorities.forEach((p: any) => { const t: string = p.tier || ''; counts[t] = (counts[t] || 0) + 1 })

  async function toggleCrisis(patient: string, isCrisis: boolean) {
    try {
      if (isCrisis) await api.resolveCrisis()
      else await api.triggerCrisis()
    } catch {}
  }

  async function assessRisk(patient: string, lastRaw: string) {
    if (!lastRaw) return
    try {
      const result = await api.assessRisk(lastRaw)
      setRiskAssessments({ ...riskAssessments, [patient]: result })
    } catch {}
  }

  return (
    <div className="animate-fade-in">
      <h2>📊 Priority Triage Dashboard</h2>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '24px' }}>
        {[
          { label: '🚨 Crisis', count: counts.crisis, color: '#ef4444' },
          { label: '🟠 High', count: counts.high, color: '#f59e0b' },
          { label: '🟡 Attention', count: counts.attention, color: '#c49ea4' },
          { label: '🟢 Stable', count: counts.stable, color: '#22c55e' },
        ].map(item => (
          <div key={item.label} className="card" style={{ textAlign: 'center', padding: '10px', borderColor: `${item.color}30` }}>
            <div style={{ color: item.color, fontSize: '0.75rem', fontWeight: 600 }}>{item.label}</div>
            <div style={{ color: '#f0f4ff', fontSize: '1.5rem', fontWeight: 700 }}>{item.count}</div>
          </div>
        ))}
      </div>

      <hr />

      {priorities.map((p: any) => {
        const patient = p.patient
        const isCrisis = p.crisis
        const open = expanded[patient]
        const ring = { bpm: p.bpm || 72, stress: p.stress || 35, sleep: p.sleep || 7, spo2: p.spo2 || 98, mood: (p.mood || 'neutral').toLowerCase() }

        return (
          <div key={patient} className="expander" style={{ borderColor: isCrisis ? '#ff4444' : '#2d2d44', borderWidth: isCrisis ? '2px' : '1px' }}>
            <div className="expander-header" onClick={() => setExpanded({ ...expanded, [patient]: !open })}>
              <span>{isCrisis ? '🚨 ' : ''}{p.name} (@{patient})</span>
              <span>{open ? '▲' : '▼'}</span>
            </div>
            {open && (
              <div className="expander-body">
                {/* 5 Bio metric cards */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '8px', marginBottom: '12px' }}>
                  <MetricCard label="BPM" value={`${ring.bpm}`} unit="" color="#ff6b6b" />
                  <MetricCard label="Stress" value={`${ring.stress}%`} unit="" color="#ffd93d" />
                  <MetricCard label="Sleep" value={`${ring.sleep}h`} unit="" color="#d8b4ba" />
                  <MetricCard label="SpO₂" value={`${ring.spo2}%`} unit="" color="#6bffb8" />
                  <MetricCard label="Mood" value={ring.mood.charAt(0).toUpperCase() + ring.mood.slice(1)} unit="" color="#c49ea4" />
                </div>

                {/* AI Clinical Insight */}
                {p.summary && (
                  <div className="ai-box" style={{ marginTop: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ fontWeight: 600, fontSize: '0.8125rem' }}>AI Clinical Insight</span>
                      {p.ai_source && (
                        <span style={{ background: `${sourceColor(p.ai_source)}22`, color: sourceColor(p.ai_source), fontSize: '0.6rem', padding: '1px 6px', borderRadius: '3px', fontWeight: 600, border: `1px solid ${sourceColor(p.ai_source)}44`, marginLeft: '6px' }}>{p.ai_source.charAt(0).toUpperCase() + p.ai_source.slice(1)}</span>
                      )}
                    </div>
                    <div style={{ color: '#9aa8c0', fontSize: '0.8125rem', marginTop: '4px' }}>{p.summary}</div>
                    {p.emotions && <div style={{ color: '#7a8aaa', fontSize: '0.65rem', marginTop: '2px' }}>Detected: {p.emotions}</div>}
                  </div>
                )}

                {/* Explainability */}
                <div style={{ marginTop: '8px' }}>
                  <button style={{ fontSize: '0.75rem', width: '100%' }} onClick={() => setExplainOpen({ ...explainOpen, [patient]: !explainOpen[patient] })}>
                    🔍 Why this summary?
                  </button>
                  {explainOpen[patient] && (
                    <div className="card-dark" style={{ padding: '10px', marginTop: '4px' }}>
                      <div style={{ color: '#c49ea4', fontSize: '0.7rem', fontWeight: 600, marginBottom: '4px' }}>Explainability</div>
                      <div style={{ color: '#9aa8c0', fontSize: '0.6875rem', lineHeight: 1.6 }}>
                        AI Source: <strong>{p.ai_source ? p.ai_source.charAt(0).toUpperCase() + p.ai_source.slice(1) : 'N/A'}</strong><br />
                        Prompt Mode: <strong>Clinical Summarization</strong><br />
                        {p.emotions ? `Detected Emotions: <strong>${p.emotions}</strong><br>` : ''}
                        The summary was generated by Sentinel using a {p.ai_source ? p.ai_source.charAt(0).toUpperCase() + p.ai_source.slice(1) : 'rule-based'} inference with a clinical documentation prompt. No raw journal text is exposed to preserve patient privacy.
                      </div>
                    </div>
                  )}
                </div>

                {/* Crisis Risk Assessment */}
                {p.last_raw && (
                  <div style={{ marginTop: '8px' }}>
                    {riskAssessments[patient] ? (
                      <div className="card-dark" style={{ padding: '10px', borderColor: riskAssessments[patient].triggered ? '#ef444444' : '#22c55e44' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                          <div style={{ color: riskAssessments[patient].triggered ? '#ef4444' : '#22c55e', fontSize: '0.7rem', fontWeight: 600 }}>Crisis Risk Assessment</div>
                          <div style={{ color: riskAssessments[patient].triggered ? '#ef4444' : '#22c55e', fontSize: '1rem', fontWeight: 700 }}>{riskAssessments[patient].risk_score || '?'}/10</div>
                        </div>
                        <div style={{ color: '#9aa8c0', fontSize: '0.6875rem', lineHeight: 1.6 }}>{riskAssessments[patient].reasoning || 'No reasoning available.'}</div>
                      </div>
                    ) : (
                      <button style={{ fontSize: '0.75rem', width: '100%' }} onClick={() => assessRisk(patient, p.last_raw)}>⚠️ Assess Crisis Risk</button>
                    )}
                  </div>
                )}

                {/* Contact info */}
                {(p.email || p.trusted_contact) && (
                  <div style={{ fontSize: '0.6875rem', color: '#6a6474', marginTop: '6px' }}>
                    {p.email ? `📧 Patient: ${p.email}` : ''}
                    {p.email && p.trusted_contact ? ' &nbsp;|&nbsp; ' : ''}
                    {p.trusted_contact ? `👤 TC: ${p.trusted_contact}` : ''}
                  </div>
                )}

                {/* Actions */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginTop: '12px', alignItems: 'center' }}>
                  <button
                    className={isCrisis ? 'btn-primary' : ''}
                    style={{ fontSize: '0.75rem' }}
                    onClick={() => toggleCrisis(patient, isCrisis)}
                  >
                    {isCrisis ? '✅ Resolve Crisis' : '🚨 Trigger Crisis'}
                  </button>
                  <div style={{ textAlign: 'center', fontSize: '0.75rem', color: '#6a6474' }}>
                    <span style={{ color: '#c49ea4' }}>{p.name}</span>
                  </div>
                  <div style={{ textAlign: 'right', fontSize: '0.6875rem', color: '#5a4a5a' }}>
                    Score: {p.score} | {isCrisis ? '🚨 CRISIS' : p.tier === 'high' ? 'HIGH' : p.tier === 'attention' ? 'ATTENTION' : 'STABLE'}
                  </div>
                </div>
              </div>
            )}
          </div>
        )
      })}

      {priorities.length === 0 && (
        <div className="card"><span style={{ color: '#6a6474', fontSize: '0.875rem' }}>No patients registered.</span></div>
      )}
    </div>
  )
}
