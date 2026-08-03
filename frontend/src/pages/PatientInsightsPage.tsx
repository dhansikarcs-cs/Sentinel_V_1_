import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { EmotionBars } from '../components/EmotionBar'
import PatientSelector, { usePatientContext } from '../components/PatientSelector'
import PrioritiesPanel from '../components/PrioritiesPanel'
import { moodIcon, formatTime, formatDate } from '../constants'

const SUB_TABS = [
  { key: 'overview', label: '\u{1F9ED} Current State' },
  { key: 'emotions', label: '\u{1F3AD} Emotions' },
  { key: 'ai-trace', label: '\u{1F9E0} AI Trace' },
  { key: 'patterns', label: '\u{1F50D} Patterns' },
]

export default function PatientInsightsPage() {
  const { patients } = usePatientContext()
  const [selected, setSelected] = useState('')
  const [overview, setOverview] = useState<any>(null)
  const [overviewLoading, setOverviewLoading] = useState(false)
  const [subTab, setSubTab] = useState('overview')

  useEffect(() => {
    if (!selected) { setOverview(null); return }
    setOverviewLoading(true)
    api.getPatientOverview(selected)
      .then(d => setOverview(d))
      .catch(() => setOverview(null))
      .finally(() => setOverviewLoading(false))
  }, [selected])

  return (
    <div className="animate-fade-in">
      <h2>{'\u{1F50D}'} Patient Insights</h2>
      <p style={{ color: '#6a6474', fontSize: '0.75rem', marginBottom: '12px' }}>
        One composed view of the patient's current state — identity, clinical brief, trends, risk, and activity.
      </p>

      <PatientSelector
        patients={patients}
        value={selected}
        onChange={setSelected}
        placeholder="-- Select patient --"
        style={{ marginBottom: '16px' }}
      />

      {selected && (
        <div style={{ display: 'flex', gap: '4px', marginBottom: '20px' }}>
          {SUB_TABS.map(t => (
            <button
              key={t.key}
              onClick={() => setSubTab(t.key)}
              style={{
                padding: '8px 16px', fontSize: '0.8125rem', borderRadius: '8px',
                background: subTab === t.key ? '#2a2040' : 'transparent',
                border: `1px solid ${subTab === t.key ? '#c49ea460' : '#2d2d44'}`,
                color: subTab === t.key ? '#c49ea4' : '#6a6474',
                cursor: 'pointer', fontWeight: subTab === t.key ? 600 : 400,
              }}
            >
              {t.label}
            </button>
          ))}
        </div>
      )}

      {!selected && (
        <div className="card" style={{ color: '#6a6474', textAlign: 'center', padding: '32px' }}>
          Select a patient to view their current state.
        </div>
      )}

      {selected && subTab === 'overview' && <OverviewSection overview={overview} loading={overviewLoading} />}
      {selected && subTab === 'emotions' && <EmotionsSection patient={selected} />}
      {selected && subTab === 'ai-trace' && <AITraceSection patient={selected} />}
      {selected && subTab === 'patterns' && <PatternsSection patient={selected} overview={overview} />}
    </div>
  )
}

function OverviewSection({ overview, loading }: { overview: any; loading: boolean }) {
  if (loading) return <div className="card" style={{ color: '#6a6474', textAlign: 'center', padding: '20px' }}>Composing patient state...</div>
  if (!overview) return <div className="card" style={{ color: '#ef4444', textAlign: 'center', padding: '20px' }}>Failed to load overview.</div>

  const identity = overview.patient || {}
  const changes = overview.changes_since_last_visit || {}
  const moodTrend = overview.mood_trend || []
  const followups = overview.followups || {}
  const sensor = overview.sensor_trends || []
  const latestSensor = sensor[0]
  const events = overview.timeline || []
  const risk = overview.risk
  const crisis = overview.crisis

  const latestMood = moodTrend.length > 0 ? moodTrend[0] : null

  return (
    <>
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

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: '12px', marginBottom: '16px' }}>
        <div className="card" style={{ padding: '14px' }}>
          <div style={{ color: '#c49ea4', fontWeight: 600, fontSize: '0.75rem', marginBottom: '6px' }}>PATIENT</div>
          <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#f0f4ff' }}>{identity.name || identity.username}</div>
          <div style={{ color: '#7a8aaa', fontSize: '0.7rem', marginTop: '2px' }}>
            @{identity.username} &middot; {identity.role}
          </div>
          <div style={{ color: '#6a6474', fontSize: '0.65rem', marginTop: '4px' }}>
            {identity.age || '?'} yrs &middot; {identity.occupation || '—'} &middot; {identity.clinic || '—'}
          </div>
        </div>

        <div className="card" style={{ padding: '14px' }}>
          <div style={{ color: '#6a6474', fontSize: '0.7rem' }}>MOOD TREND</div>
          <div style={{ color: changes.mood_trend === 'improving' ? '#22c55e' : changes.mood_trend === 'declining' ? '#ef4444' : '#fbbf24', fontSize: '1.1rem', fontWeight: 700 }}>
            {changes.mood_trend === 'improving' ? '\u2197\uFE0F improving' : changes.mood_trend === 'declining' ? '\u2198 declining' : changes.mood_trend === 'stable' ? '\u2192 stable' : '\u2014'}
          </div>
          <div style={{ color: '#7a8aaa', fontSize: '0.65rem' }}>
            Now: {changes.current_mood_avg ? `${Number(changes.current_mood_avg).toFixed(1)}/5` : 'N/A'} | Prev: {changes.previous_mood_avg ? `${Number(changes.previous_mood_avg).toFixed(1)}/5` : 'N/A'}
          </div>
        </div>

        <div className="card" style={{ padding: '14px' }}>
          <div style={{ color: '#6a6474', fontSize: '0.7rem' }}>ENGAGEMENT</div>
          <div style={{ color: '#f0f4ff', fontSize: '1.1rem', fontWeight: 700 }}>
            {changes.journal_count_7 || 0} <span style={{ fontSize: '0.6rem', color: '#6a6474' }}>journals 7d</span>
          </div>
          <div style={{ color: changes.engagement_trend === 'increasing' ? '#22c55e' : changes.engagement_trend === 'declining' ? '#ef4444' : '#fbbf24', fontSize: '0.65rem' }}>
            {changes.engagement_trend === 'increasing' ? '\u2197' : changes.engagement_trend === 'declining' ? '\u2198' : '\u2192'} {changes.journal_count_14 || 0} in 14d
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px', marginBottom: '16px' }}>
        <div className="card" style={{ padding: '14px' }}>
          <div style={{ color: '#c49ea4', fontWeight: 600, fontSize: '0.75rem', marginBottom: '8px' }}>RISK SNAPSHOT</div>
          {risk ? (
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ color: risk.triggered ? '#ef4444' : risk.risk_score >= 7 ? '#f59e0b' : '#22c55e', fontSize: '1.4rem', fontWeight: 700 }}>{risk.risk_score}/10</span>
                {risk.triggered && <span style={{ fontSize: '0.9rem' }}>{'\u{1F6A8}'}</span>}
              </div>
              <div style={{ color: '#6a6474', fontSize: '0.6rem' }}>
                {formatDate(risk.created_at)} &middot; confidence {risk.confidence ? `${(risk.confidence * 100).toFixed(0)}%` : 'N/A'}
                {risk.algorithm_version ? ` &middot; engine v${risk.algorithm_version}` : ''}
              </div>
              {(risk.explanation || '').length > 0 && (
                <div style={{ color: '#7a8aaa', fontSize: '0.62rem', marginTop: '4px', lineHeight: 1.5 }}>
                  {risk.explanation.slice(0, 160)}
                </div>
              )}
            </>
          ) : (
            <div style={{ color: '#6a6474', fontSize: '0.7rem' }}>No assessments yet.</div>
          )}
        </div>

        <div className="card" style={{ padding: '14px' }}>
          <div style={{ color: '#c49ea4', fontWeight: 600, fontSize: '0.75rem', marginBottom: '8px' }}>FOLLOW-UPS</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ color: '#f0f4ff', fontSize: '1.4rem', fontWeight: 700 }}>{followups.pending || 0}</span>
            <span style={{ color: '#6a6474', fontSize: '0.65rem' }}>pending of {followups.total || 0}</span>
          </div>
          <div style={{ color: '#22c55e', fontSize: '0.65rem' }}>{followups.completed || 0} completed</div>
          {(followups.list || []).slice(0, 3).map((f: any) => (
            <div key={f.id} style={{ color: '#7a8aaa', fontSize: '0.62rem', marginTop: '3px' }}>
              {f.status === 'completed' ? '\u2705' : '\u23F3'} {f.title}
            </div>
          ))}
        </div>

        <div className="card" style={{ padding: '14px' }}>
          <div style={{ color: '#c49ea4', fontWeight: 600, fontSize: '0.75rem', marginBottom: '8px' }}>LATEST RING</div>
          {latestSensor ? (
            <>
              <div style={{ display: 'flex', gap: '10px', fontSize: '0.68rem', color: '#7a8aaa' }}>
                <span><span style={{ color: '#f0f4ff', fontWeight: 700 }}>{latestSensor.bpm || '—'}</span> BPM</span>
                <span><span style={{ color: '#f0f4ff', fontWeight: 700 }}>{latestSensor.stress || '—'}</span> stress</span>
                <span><span style={{ color: '#f0f4ff', fontWeight: 700 }}>{latestSensor.sleep_hours || '—'}</span>h sleep</span>
              </div>
              <div style={{ display: 'flex', gap: '10px', fontSize: '0.68rem', color: '#7a8aaa', marginTop: '3px' }}>
                <span><span style={{ color: '#f0f4ff', fontWeight: 700 }}>{latestSensor.spo2 || '—'}</span> SpO2</span>
                <span><span style={{ color: '#f0f4ff', fontWeight: 700 }}>{latestSensor.hrv || '—'}</span> HRV</span>
              </div>
              <div style={{ color: '#6a6474', fontSize: '0.6rem', marginTop: '4px' }}>{formatTime(latestSensor.logged_at)}</div>
            </>
          ) : (
            <div style={{ color: '#6a6474', fontSize: '0.7rem' }}>No ring data yet.</div>
          )}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
        <div className="card" style={{ padding: '14px' }}>
          <div style={{ color: '#c49ea4', fontWeight: 600, fontSize: '0.75rem', marginBottom: '6px' }}>CLINICAL BRIEF</div>
          {overview.clinical_brief ? (
            <>
              <div style={{ color: '#f0f4ff', fontSize: '0.72rem', fontWeight: 600 }}>{formatTime(overview.clinical_brief.timestamp)}</div>
              <div style={{ color: '#7a8aaa', fontSize: '0.68rem', marginTop: '4px', lineHeight: 1.5 }}>
                {(overview.clinical_brief.clinical_summary || overview.clinical_brief.summary || '').slice(0, 260)}
              </div>
              {(overview.clinical_brief.emotions || '').length > 0 && (
                <div style={{ color: '#6a6474', fontSize: '0.62rem', marginTop: '4px' }}>Emotions: {overview.clinical_brief.emotions}</div>
              )}
              {overview.clinical_brief.ai_analysis && (
                <div style={{ color: '#5a5464', fontSize: '0.58rem', marginTop: '6px', lineHeight: 1.6 }}>
                  AI: {overview.clinical_brief.ai_analysis.provider || 'rule'} &middot; prompt {overview.clinical_brief.ai_analysis.prompt_version || 'rule'}
                  {overview.clinical_brief.ai_analysis.model_version ? ` &middot; model v${overview.clinical_brief.ai_analysis.model_version}` : ''}
                  {overview.clinical_brief.ai_analysis.confidence ? ` &middot; confidence ${(overview.clinical_brief.ai_analysis.confidence * 100).toFixed(0)}%` : ''}
                  {overview.clinical_brief.ai_analysis.priority ? ` &middot; priority ${overview.clinical_brief.ai_analysis.priority}` : ''}
                </div>
              )}
            </>
          ) : (
            <div style={{ color: '#6a6474', fontSize: '0.7rem' }}>No recent journals.</div>
          )}
        </div>

        <div className="card" style={{ padding: '14px' }}>
          <div style={{ color: '#c49ea4', fontWeight: 600, fontSize: '0.75rem', marginBottom: '6px' }}>LAST APPOINTMENT</div>
          {overview.last_appointment ? (
            <>
              <div style={{ color: '#f0f4ff', fontSize: '0.72rem', fontWeight: 600 }}>
                {formatDate(overview.last_appointment.date)} {overview.last_appointment.time}
              </div>
              <div style={{ color: '#7a8aaa', fontSize: '0.68rem', marginTop: '2px' }}>
                {overview.last_appointment.session_type || 'Session'} &middot; {overview.last_appointment.status}
              </div>
              <div style={{ color: '#6a6474', fontSize: '0.62rem', marginTop: '2px' }}>{overview.last_appointment.psychologist_username}</div>
            </>
          ) : (
            <div style={{ color: '#6a6474', fontSize: '0.7rem' }}>No appointments yet.</div>
          )}
          {crisis && (
            <div style={{ marginTop: '8px', background: '#2a0f1c', border: '1px solid #ef444455', borderRadius: '6px', padding: '6px 8px' }}>
              <span style={{ color: '#ef4444', fontSize: '0.65rem', fontWeight: 700 }}>{'\u{1F6A8}'} CRISIS ACTIVE</span>
              <div style={{ color: '#7a8aaa', fontSize: '0.6rem', marginTop: '2px' }}>
                triggered {formatTime(crisis.triggered_at)} &middot; {crisis.acknowledged ? 'acknowledged' : 'NOT acknowledged'}
              </div>
            </div>
          )}
        </div>
      </div>

      {latestMood && (
        <div className="card" style={{ padding: '10px', marginBottom: '16px' }}>
          <div style={{ color: '#6a6474', fontSize: '0.6rem', marginBottom: '4px' }}>LATEST MOOD &middot; MOOD TREND (14d)</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '1.4rem' }}>{moodIcon(latestMood.label)}</span>
            <span style={{ color: '#e0e8f0', fontWeight: 600, fontSize: '0.75rem' }}>{latestMood.label}</span>
            <span style={{ color: '#6a6474', fontSize: '0.65rem' }}>{formatTime(latestMood.timestamp)}</span>
            <div style={{ flex: 1, display: 'flex', gap: '3px' }}>
              {moodTrend.map((m: any, i: number) => (
                <div key={i} style={{ flex: 1, fontSize: '0.8rem', opacity: m.timestamp === latestMood.timestamp ? 1 : 0.55 }} title={`${m.label} ${formatDate(m.timestamp)}`}>
                  {moodIcon(m.label)}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <h3 style={{ marginTop: '4px' }}>{'\u{1F4C5}'} Recent Activity</h3>
      {events.length === 0 ? (
        <div className="card" style={{ color: '#6a6474', textAlign: 'center', padding: '20px' }}>No events in the last 30 days.</div>
      ) : (
        <div style={{ maxHeight: '400px', overflowY: 'auto', paddingRight: '4px' }}>
          {events.slice(0, 40).map((ev: any, i: number) => {
            const colors: Record<string, string> = { mood: '#22c55e', journal: '#6366f1', followup: '#f59e0b', crisis: '#ef4444' }
            const borderLeft = `3px solid ${colors[ev.type] || '#6a6474'}`
            return (
              <div key={i} style={{ borderLeft, background: '#111827', borderRadius: '6px', padding: '8px 12px', margin: '4px 0' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#e0e8f0', fontWeight: 600, fontSize: '0.8rem' }}>
                    {ev.type === 'mood' ? `${moodIcon(ev.data?.label)} [${ev.data?.label?.toUpperCase()}]` :
                     ev.type === 'journal' ? `\u{1F4DD} ${ev.data?.title || 'Journal Entry'}` :
                     ev.type === 'followup' ? `${ev.data?.status === 'completed' ? '\u2705' : '\u23F3'} ${ev.data?.title || 'Task'}` :
                     `\u{1F6A8} ${(ev.data?.event || 'Crisis').toUpperCase()}`}
                  </span>
                  <span style={{ color: '#6a6474', fontSize: '0.65rem' }}>{formatTime(ev.timestamp)}</span>
                </div>
                <div style={{ color: '#7a8aaa', fontSize: '0.7rem', marginTop: '2px' }}>
                  {ev.type === 'mood' ? `Mood: ${ev.data?.label || 'N/A'} on ${ev.data?.date || ''}` :
                   ev.type === 'journal' ? (ev.data?.summary || '').slice(0, 150) :
                   ev.data?.description || ev.data?.details || ''}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </>
  )
}

function EmotionsSection({ patient }: { patient: string }) {
  const [data, setData] = useState<any>(null)

  useEffect(() => {
    api.getEmotionTimeline(patient, 30).then(setData).catch(() => {})
  }, [patient])

  if (!data) return <div className="card" style={{ color: '#6a6474', textAlign: 'center', padding: '20px' }}>Loading emotion data...</div>

  return (
    <>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '10px', marginBottom: '20px' }}>
        {Object.entries(data.emotion_summary || {}).slice(0, 8).map(([emotion, info]: [string, any]) => (
          <div key={emotion} className="card" style={{ padding: '10px' }}>
            <div style={{ color: '#c49ea4', fontSize: '0.6875rem', fontWeight: 600 }}>{emotion}</div>
            <div style={{ color: '#f0f4ff', fontSize: '1rem', fontWeight: 700 }}>{info.average}%</div>
            <div style={{ color: '#6a6474', fontSize: '0.625rem' }}>peak {info.max}% &middot; {info.count}x</div>
          </div>
        ))}
      </div>

      <h3>Entry Timeline ({data.entries_count ?? 0} entries)</h3>
      {(data.timeline?.length ?? 0) === 0 ? (
        <div className="card" style={{ color: '#6a6474', textAlign: 'center', padding: '20px' }}>No analyzed entries.</div>
      ) : (
        data.timeline.map((point: any) => (
          <div key={point.journal_id} className="expander" style={{ cursor: 'default' }}>
            <div className="expander-header">
              <span>{point.timestamp?.slice(0, 10)} &middot; {point.emotions}</span>
            </div>
            <div className="expander-body">
              <EmotionBars emotionProbabilities={point.emotion_probabilities} />
            </div>
          </div>
        ))
      )}
    </>
  )
}

function AITraceSection({ patient }: { patient: string }) {
  const [analyses, setAnalyses] = useState<any[]>([])
  const [risks, setRisks] = useState<any[]>([])
  const [emotionResults, setEmotionResults] = useState<any[]>([])

  useEffect(() => {
    Promise.allSettled([
      api.getAIAnalysesForPatient(patient),
      api.getRiskAssessmentsForPatient(patient),
      api.getEmotionResultsForPatient(patient),
    ]).then(([a, r, e]) => {
      setAnalyses(a.status === 'fulfilled' ? a.value : [])
      setRisks(r.status === 'fulfilled' ? r.value : [])
      setEmotionResults(e.status === 'fulfilled' ? e.value : [])
    })
  }, [patient])

  return (
    <>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '20px' }}>
        <div className="card" style={{ padding: '12px', textAlign: 'center' }}>
          <div style={{ color: '#889', fontSize: '0.65rem' }}>AI Analyses</div>
          <div style={{ color: '#c49ea4', fontSize: '1.3rem', fontWeight: 700 }}>{analyses.length}</div>
        </div>
        <div className="card" style={{ padding: '12px', textAlign: 'center' }}>
          <div style={{ color: '#889', fontSize: '0.65rem' }}>Risk Assessments</div>
          <div style={{ color: '#ef4444', fontSize: '1.3rem', fontWeight: 700 }}>{risks.length}</div>
        </div>
        <div className="card" style={{ padding: '12px', textAlign: 'center' }}>
          <div style={{ color: '#889', fontSize: '0.65rem' }}>Emotion Results</div>
          <div style={{ color: '#3b82f6', fontSize: '1.3rem', fontWeight: 700 }}>{emotionResults.length}</div>
        </div>
      </div>

      {risks.length > 0 && (
        <>
          <h3>Risk Assessments</h3>
          {risks.slice(0, 10).map((r: any) => (
            <div key={r.id} className="expander" style={{ cursor: 'default' }}>
              <div className="expander-header">
                <span>{r.created_at?.slice(0, 10)} &middot; Risk: {r.risk_score}/10 {r.triggered ? '\u{1F6A8}' : ''}</span>
                <span style={{ color: '#6a6474', fontSize: '0.6rem' }}>v{r.algorithm_version}</span>
              </div>
              <div className="expander-body">
                <div style={{ fontSize: '0.6875rem', color: '#9aa8c0', lineHeight: 1.6 }}>
                  {r.explanation && (() => {
                    try {
                      const exp = JSON.parse(r.explanation)
                      return (
                        <>
                          {exp.top_contributors?.map((c: any, i: number) => (
                            <div key={i}>&bull; {c.emotion}: P={c.probability?.toFixed(2)}, weight={c.weight}, contribution={c.contribution?.toFixed(3)}</div>
                          ))}
                          <div style={{ marginTop: '4px', color: '#6a6474' }}>
                            Keyword: {exp.keyword_base_score} | Emotion: {exp.emotion_risk_score} | Blended: {exp.blended_score}
                          </div>
                        </>
                      )
                    } catch { return r.explanation }
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
            <div key={a.id} className="card" style={{ marginBottom: '6px', padding: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: '#c49ea4', fontWeight: 600, fontSize: '0.7rem' }}>{a.created_at?.slice(0, 10)} &middot; {a.priority}</span>
                <span style={{ fontSize: '0.55rem', padding: '1px 5px', borderRadius: '3px', background: a.provider === 'groq' ? '#22c55e22' : '#f59e0b22', color: a.provider === 'groq' ? '#22c55e' : '#f59e0b' }}>
                  {a.provider} v{a.model_version}
                </span>
              </div>
              <div style={{ color: '#9aa8c0', fontSize: '0.65rem', marginTop: '2px' }}>
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
              <div key={er.id} className="card" style={{ marginBottom: '6px', padding: '10px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ color: '#c49ea4', fontSize: '0.7rem' }}>{er.created_at?.slice(0, 10)}</span>
                  <span style={{ color: '#6a6474', fontSize: '0.55rem' }}>v{er.model_version}</span>
                </div>
                <EmotionBars emotionProbabilities={probs} maxItems={8} />
              </div>
            )
          })}
        </>
      )}

      {analyses.length === 0 && risks.length === 0 && emotionResults.length === 0 && (
        <div className="card" style={{ color: '#6a6474', textAlign: 'center', padding: '20px' }}>
          No AI analysis data for this patient yet.
        </div>
      )}
    </>
  )
}

function PatternsSection({ patient, overview }: { patient: string; overview: any }) {
  const [patterns, setPatterns] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    const timelineRaw = overview?.timeline || []
    const timeline = Array.isArray(timelineRaw) ? timelineRaw : timelineRaw.events || []

    Promise.allSettled([
      overview?.changes_since_last_visit
        ? Promise.resolve(overview.changes_since_last_visit)
        : api.getMetrics(patient),
      api.getEmotionTimeline(patient, 30),
      api.getRiskAssessmentsForPatient(patient),
      overview?.timeline ? Promise.resolve({ events: timeline }) : api.getTimeline(patient, 30),
    ]).then(([metricsRes, emoRes, riskRes, timelineRes]) => {
      const metrics = metricsRes.status === 'fulfilled' ? metricsRes.value : null
      const emoData = emoRes.status === 'fulfilled' ? emoRes.value : null
      const risks = riskRes.status === 'fulfilled' ? (riskRes.value || []) : []
      const tl = timelineRes.status === 'fulfilled' ? timelineRes.value : []
      const timelineEvents = tl?.events || tl || timeline

      const moodEvents = (timelineEvents as any[]).filter((e: any) => e.type === 'mood')
      const journalEvents = (timelineEvents as any[]).filter((e: any) => e.type === 'journal')

      const moodCounts: Record<string, number> = {}
      moodEvents.forEach((e: any) => {
        const label = e.data?.label || 'unknown'
        moodCounts[label] = (moodCounts[label] || 0) + 1
      })

      const dayOfWeekMood: Record<string, number[]> = {}
      moodEvents.forEach((e: any) => {
        const day = new Date(e.timestamp).toLocaleDateString('en-US', { weekday: 'short' })
        if (!dayOfWeekMood[day]) dayOfWeekMood[day] = []
        const score = e.data?.score || 3
        dayOfWeekMood[day].push(score)
      })
      const avgByDay: Record<string, number> = {}
      Object.entries(dayOfWeekMood).forEach(([day, scores]) => {
        avgByDay[day] = scores.reduce((a: number, b: number) => a + b, 0) / scores.length
      })

      const journalLengths = journalEvents.map((e: any) => (e.data?.content || '').length)
      const avgJournalLength = journalLengths.length > 0 ? Math.round(journalLengths.reduce((a: number, b: number) => a + b, 0) / journalLengths.length) : 0

      const riskScores = (risks as any[]).map((r: any) => r.risk_score || 0)
      const avgRisk = riskScores.length > 0 ? (riskScores.reduce((a: number, b: number) => a + b, 0) / riskScores.length).toFixed(1) : 'N/A'
      const maxRisk = riskScores.length > 0 ? Math.max(...riskScores) : 0

      const topEmotions = Object.entries(emoData?.emotion_summary || {})
        .sort(([, a]: [string, any], [, b]: [string, any]) => (b.average || 0) - (a.average || 0))
        .slice(0, 5)

      setPatterns({
        moodCounts,
        avgByDay,
        avgJournalLength,
        journalCount: journalEvents.length,
        avgRisk,
        maxRisk,
        riskCount: riskScores.length,
        topEmotions,
        moodTrend: (metrics as any)?.mood_trend || 'N/A',
        engagementTrend: (metrics as any)?.engagement_trend || 'N/A',
      })
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [patient, overview])

  if (loading) return <div className="card" style={{ color: '#6a6474', textAlign: 'center', padding: '20px' }}>Analyzing patterns...</div>
  if (!patterns) return <div className="card" style={{ color: '#6a6474', textAlign: 'center', padding: '20px' }}>No data available.</div>

  const dayOrder = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

  return (
    <>
      <h3>Behavioral Patterns</h3>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '20px' }}>
        <div className="card" style={{ padding: '14px' }}>
          <div style={{ color: '#c49ea4', fontWeight: 600, fontSize: '0.75rem', marginBottom: '8px' }}>Mood Distribution</div>
          {Object.keys(patterns.moodCounts).length === 0 ? (
            <div style={{ color: '#6a6474', fontSize: '0.7rem' }}>No mood data.</div>
          ) : (
            Object.entries(patterns.moodCounts).sort(([, a], [, b]) => (b as number) - (a as number)).map(([label, count]: [string, any]) => {
              const max = Math.max(...(Object.values(patterns.moodCounts) as number[]))
              return (
                <div key={label} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                  <span style={{ color: '#9a92a2', fontSize: '0.65rem', width: '50px' }}>{label}</span>
                  <div style={{ flex: 1, height: '6px', background: '#1e2940', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', borderRadius: '3px', width: `${(count / max) * 100}%`, background: '#c49ea4' }} />
                  </div>
                  <span style={{ color: '#6a6474', fontSize: '0.6rem' }}>{count}</span>
                </div>
              )
            })
          )}
        </div>

        <div className="card" style={{ padding: '14px' }}>
          <div style={{ color: '#c49ea4', fontWeight: 600, fontSize: '0.75rem', marginBottom: '8px' }}>Mood by Day of Week</div>
          {Object.keys(patterns.avgByDay).length === 0 ? (
            <div style={{ color: '#6a6474', fontSize: '0.7rem' }}>Not enough data.</div>
          ) : (
            dayOrder.filter(d => patterns.avgByDay[d] != null).map(day => {
              const avg = patterns.avgByDay[day]
              const pct = ((avg - 1) / 4) * 100
              return (
                <div key={day} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                  <span style={{ color: '#9a92a2', fontSize: '0.65rem', width: '30px' }}>{day}</span>
                  <div style={{ flex: 1, height: '6px', background: '#1e2940', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', borderRadius: '3px', width: `${pct}%`, background: avg >= 3.5 ? '#22c55e' : avg >= 2.5 ? '#fbbf24' : '#ef4444' }} />
                  </div>
                  <span style={{ color: '#6a6474', fontSize: '0.6rem' }}>{avg.toFixed(1)}</span>
                </div>
              )
            })
          )}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px', marginBottom: '20px' }}>
        <div className="card" style={{ padding: '10px', textAlign: 'center' }}>
          <div style={{ color: '#889', fontSize: '0.6rem' }}>MOOD TREND</div>
          <div style={{ color: patterns.moodTrend === 'improving' ? '#22c55e' : patterns.moodTrend === 'declining' ? '#ef4444' : '#fbbf24', fontSize: '1rem', fontWeight: 700 }}>
            {patterns.moodTrend === 'improving' ? '\u2197 improving' : patterns.moodTrend === 'declining' ? '\u2198 declining' : patterns.moodTrend}
          </div>
        </div>
        <div className="card" style={{ padding: '10px', textAlign: 'center' }}>
          <div style={{ color: '#889', fontSize: '0.6rem' }}>ENGAGEMENT</div>
          <div style={{ color: patterns.engagementTrend === 'increasing' ? '#22c55e' : patterns.engagementTrend === 'declining' ? '#ef4444' : '#fbbf24', fontSize: '1rem', fontWeight: 700 }}>
            {patterns.journalCount} journals
          </div>
        </div>
        <div className="card" style={{ padding: '10px', textAlign: 'center' }}>
          <div style={{ color: '#889', fontSize: '0.6rem' }}>AVG ENTRY</div>
          <div style={{ color: '#c49ea4', fontSize: '1rem', fontWeight: 700 }}>
            {patterns.avgJournalLength} chars
          </div>
        </div>
        <div className="card" style={{ padding: '10px', textAlign: 'center' }}>
          <div style={{ color: '#889', fontSize: '0.6rem' }}>AVG RISK</div>
          <div style={{ color: Number(patterns.avgRisk) >= 5 ? '#ef4444' : '#22c55e', fontSize: '1rem', fontWeight: 700 }}>
            {patterns.avgRisk}/10
          </div>
        </div>
      </div>

      {patterns.topEmotions.length > 0 && (
        <div className="card" style={{ padding: '14px' }}>
          <div style={{ color: '#c49ea4', fontWeight: 600, fontSize: '0.75rem', marginBottom: '8px' }}>Top Emotions (30d)</div>
          {patterns.topEmotions.map(([emotion, info]: [string, any]) => (
            <div key={emotion} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span style={{ color: '#9a92a2', fontSize: '0.65rem', width: '100px' }}>{emotion}</span>
              <div style={{ flex: 1, height: '6px', background: '#1e2940', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ height: '100%', borderRadius: '3px', width: `${info.average}%`, background: '#3b82f6' }} />
              </div>
              <span style={{ color: '#6a6474', fontSize: '0.6rem' }}>{info.average}% (x{info.count})</span>
            </div>
          ))}
        </div>
      )}
    </>
  )
}
