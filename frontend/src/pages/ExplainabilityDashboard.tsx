import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { EmotionBars } from '../components/EmotionBar'

export default function ExplainabilityDashboard() {
  const [patients, setPatients] = useState<any[]>([])
  const [selected, setSelected] = useState('')
  const [analyses, setAnalyses] = useState<any[]>([])
  const [risks, setRisks] = useState<any[]>([])
  const [emotionResults, setEmotionResults] = useState<any[]>([])

  useEffect(() => {
    api.getPsychPatients().then(setPatients).catch(() => {})
  }, [])

  useEffect(() => {
    if (!selected) return
    Promise.allSettled([
      api.getAIAnalysesForPatient(selected),
      api.getRiskAssessmentsForPatient(selected),
      api.getEmotionResultsForPatient(selected),
    ]).then(([a, r, e]) => {
      setAnalyses(a.status === 'fulfilled' ? a.value : [])
      setRisks(r.status === 'fulfilled' ? r.value : [])
      setEmotionResults(e.status === 'fulfilled' ? e.value : [])
    })
  }, [selected])

  return (
    <div className="animate-fade-in">
      <h2>AI Explainability Dashboard</h2>
      <p style={{ color: '#6a6474', fontSize: '0.75rem', marginBottom: '16px' }}>
        Trace AI decisions across emotion results, risk assessments, and model versions.
      </p>

      <select
        value={selected}
        onChange={e => setSelected(e.target.value)}
        style={{
          width: '100%', padding: '8px 12px', borderRadius: '8px',
          background: '#1e2336', border: '1px solid #2d2d44', color: '#e0e8f0',
          fontSize: '0.8125rem', marginBottom: '16px',
        }}
      >
        <option value="">-- Select patient --</option>
        {patients.map((p: any) => (
          <option key={p.username || p} value={p.username || p}>{p.name || p}</option>
        ))}
      </select>

      {selected && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '20px' }}>
          <MetricCard label="AI Analyses" value={analyses.length} color="#c49ea4" />
          <MetricCard label="Risk Assessments" value={risks.length} color="#ef4444" />
          <MetricCard label="Emotion Results" value={emotionResults.length} color="#3b82f6" />
        </div>
      )}

      {risks.length > 0 && (
        <>
          <h3>Recent Risk Assessments</h3>
          {risks.slice(0, 10).map((r: any) => (
            <div key={r.id} className="expander" style={{ cursor: 'default' }}>
              <div className="expander-header">
                <span>
                  {r.created_at?.slice(0, 10)} &middot; Risk: {r.risk_score}/10
                  {r.triggered ? ' 🚨' : ''}
                </span>
                <span style={{ color: '#6a6474', fontSize: '0.625rem' }}>v{r.algorithm_version}</span>
              </div>
              <div className="expander-body">
                <div style={{ fontSize: '0.6875rem', color: '#9aa8c0', lineHeight: 1.6 }}>
                  {r.explanation && (() => {
                    try {
                      const exp = JSON.parse(r.explanation)
                      return (
                        <>
                          {exp.top_contributors?.map((c: any, i: number) => (
                            <div key={i}>• {c.emotion}: P={c.probability?.toFixed(2)}, weight={c.weight}, contribution={c.contribution?.toFixed(3)}</div>
                          ))}
                          <div style={{ marginTop: '4px', color: '#6a6474' }}>
                            Keyword score: {exp.keyword_base_score} | Emotion score: {exp.emotion_risk_score} | Blended: {exp.blended_score}
                          </div>
                        </>
                      )
                    } catch {
                      return r.explanation
                    }
                  })()}
                </div>
              </div>
            </div>
          ))}
        </>
      )}

      {analyses.length > 0 && (
        <>
          <h3>AI Analysis History</h3>
          {analyses.slice(0, 10).map((a: any) => (
            <div key={a.id} className="card" style={{ marginBottom: '8px', padding: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: '#c49ea4', fontWeight: 600, fontSize: '0.75rem' }}>
                  {a.created_at?.slice(0, 10)} &middot; Priority: {a.priority}
                </span>
                <span style={{
                  fontSize: '0.6rem', padding: '1px 6px', borderRadius: '3px',
                  background: a.provider === 'ollama' ? '#c49ea422' : a.provider === 'groq' ? '#22c55e22' : '#f59e0b22',
                  color: a.provider === 'ollama' ? '#c49ea4' : a.provider === 'groq' ? '#22c55e' : '#f59e0b',
                }}>
                  {a.provider} v{a.model_version}
                </span>
              </div>
              <div style={{ color: '#9aa8c0', fontSize: '0.6875rem', marginTop: '4px' }}>
                Confidence: {a.confidence != null ? `${(a.confidence * 100).toFixed(1)}%` : 'N/A'}
              </div>
            </div>
          ))}
        </>
      )}

      {emotionResults.length > 0 && (
        <>
          <h3>Emotion Probability History</h3>
          {emotionResults.slice(0, 5).map((er: any) => {
            const probs: Record<string, number> = {}
            const fields = ['admiration','amusement','anger','annoyance','approval','caring','confusion','curiosity','desire','disappointment','disapproval','disgust','embarrassment','excitement','fear','gratitude','grief','joy','love','nervousness','optimism','pride','realization','relief','remorse','sadness','surprise','neutral']
            fields.forEach(f => { if (er[f] > 0) probs[f] = er[f] })
            return (
              <div key={er.id} className="card" style={{ marginBottom: '8px', padding: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ color: '#c49ea4', fontSize: '0.75rem' }}>{er.created_at?.slice(0, 10)}</span>
                  <span style={{ color: '#6a6474', fontSize: '0.625rem' }}>model v{er.model_version}</span>
                </div>
                <EmotionBars emotionProbabilities={probs} maxItems={8} />
              </div>
            )
          })}
        </>
      )}
    </div>
  )
}

function MetricCard({ label, value, color }: { label: string; value: number | string; color: string }) {
  return (
    <div className="card" style={{ padding: '14px', textAlign: 'center' }}>
      <div style={{ color: '#889', fontSize: '0.6875rem' }}>{label}</div>
      <div style={{ color, fontSize: '1.5rem', fontWeight: 700 }}>{value}</div>
    </div>
  )
}
