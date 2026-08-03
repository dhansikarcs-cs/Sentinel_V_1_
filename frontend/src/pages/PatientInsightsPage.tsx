import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { EmotionBars } from '../components/EmotionBar'

const MOOD_ICONS: Record<string, string> = { great: '\u{1F929}', good: '\u{1F60A}', okay: '\u{1F610}', bad: '\u{1F61E}', awful: '\u{1F630}', terrible: '\u{1F4A9}' }

function formatTime(ts: string) {
  try { return new Date(ts).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) } catch { return ts }
}

const SUB_TABS = [
  { key: 'timeline', label: '\u{1F4C8} Timeline' },
  { key: 'emotions', label: '\u{1F3AD} Emotions' },
  { key: 'ai-trace', label: '\u{1F9E0} AI Trace' },
  { key: 'patterns', label: '\u{1F50D} Patterns' },
]

export default function PatientInsightsPage() {
  const [patients, setPatients] = useState<any[]>([])
  const [selected, setSelected] = useState('')
  const [subTab, setSubTab] = useState('timeline')

  useEffect(() => {
    api.getPsychPatients().then(d => setPatients(d || [])).catch(() => {})
  }, [])

  return (
    <div className="animate-fade-in">
      <h2>{'\u{1F50D}'} Patient Insights</h2>
      <p style={{ color: '#6a6474', fontSize: '0.75rem', marginBottom: '12px' }}>
        Unified view of behavioral timeline, emotion analysis, and AI explainability.
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
          Select a patient to view their insights.
        </div>
      )}

      {selected && subTab === 'timeline' && <TimelineSection patient={selected} />}
      {selected && subTab === 'emotions' && <EmotionsSection patient={selected} />}
      {selected && subTab === 'ai-trace' && <AITraceSection patient={selected} />}
      {selected && subTab === 'patterns' && <PatternsSection patient={selected} />}
    </div>
  )
}

function TimelineSection({ patient }: { patient: string }) {
  const [days, setDays] = useState(30)
  const [metrics, setMetrics] = useState<any>(null)
  const [events, setEvents] = useState<any[]>([])

  useEffect(() => {
    Promise.all([
      api.getMetrics(patient).then(setMetrics).catch(() => {}),
      api.getTimeline(patient, days).then(e => setEvents(e?.events || e || [])).catch(() => {}),
    ])
  }, [patient, days])

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '20px' }}>
      <div>
        <h3>{'\u{1F4CA}'} Change Metrics</h3>
        <div className="card-dark" style={{ padding: '14px' }}>
          {metrics && (
            <>
              <div style={{ marginBottom: '10px' }}>
                <div style={{ color: '#6a6474', fontSize: '0.7rem' }}>MOOD TREND</div>
                <div style={{ color: metrics.mood_trend === 'improving' ? '#22c55e' : metrics.mood_trend === 'declining' ? '#ef4444' : '#fbbf24', fontSize: '1.1rem', fontWeight: 700 }}>
                  {metrics.mood_trend === 'improving' ? '\u2197\uFE0F improving' : metrics.mood_trend === 'declining' ? '\u2198 declining' : metrics.mood_trend === 'stable' ? '\u2192 stable' : '\u2014'}
                </div>
                <div style={{ color: '#7a8aaa', fontSize: '0.7rem' }}>
                  Now: {metrics.current_mood_avg ? `${metrics.current_mood_avg.toFixed(1)}/5` : 'N/A'} | Prev: {metrics.previous_mood_avg ? `${metrics.previous_mood_avg.toFixed(1)}/5` : 'N/A'}
                </div>
              </div>
              <div style={{ marginBottom: '10px' }}>
                <div style={{ color: '#6a6474', fontSize: '0.7rem' }}>ENGAGEMENT</div>
                <div style={{ color: metrics.engagement_trend === 'increasing' ? '#22c55e' : metrics.engagement_trend === 'declining' ? '#ef4444' : '#fbbf24', fontSize: '1.1rem', fontWeight: 700 }}>
                  {metrics.journal_count_7 || 0} entries (7d) vs {metrics.journal_count_14 || 0} (14d)
                </div>
              </div>
              {metrics.latest_mood && (
                <div>
                  <div style={{ color: '#6a6474', fontSize: '0.7rem' }}>LATEST MOOD</div>
                  <div style={{ fontSize: '1.3rem' }}>{MOOD_ICONS[metrics.latest_mood.label?.toLowerCase()] || '?'}</div>
                  <div style={{ color: '#7a8aaa', fontSize: '0.7rem' }}>{metrics.latest_mood.label}</div>
                </div>
              )}
            </>
          )}
          {!metrics && <div style={{ color: '#6a6474', fontSize: '0.8rem' }}>No data available.</div>}
        </div>
        <div style={{ marginTop: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ color: '#6a6474', fontSize: '0.7rem' }}>Range:</span>
          <input type="range" min={7} max={90} value={days} onChange={e => setDays(Number(e.target.value))} style={{ flex: 1, padding: 0 }} />
          <span style={{ color: '#6a6474', fontSize: '0.7rem' }}>{days}d</span>
        </div>
      </div>

      <div>
        <h3>{'\u{1F4C5}'} Event Feed</h3>
        {events.length === 0 ? (
          <div className="card" style={{ color: '#6a6474', textAlign: 'center', padding: '20px' }}>No events in this period.</div>
        ) : (
          <div style={{ maxHeight: '500px', overflowY: 'auto', paddingRight: '4px' }}>
            {events.map((ev: any, i: number) => {
              const colors: Record<string, string> = { mood: '#22c55e', journal: '#6366f1', followup: '#f59e0b', crisis: '#ef4444' }
              const borderLeft = `3px solid ${colors[ev.type] || '#6a6474'}`
              return (
                <div key={i} style={{ borderLeft, background: '#111827', borderRadius: '6px', padding: '8px 12px', margin: '4px 0' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#e0e8f0', fontWeight: 600, fontSize: '0.8rem' }}>
                      {ev.type === 'mood' ? `${MOOD_ICONS[ev.data?.label?.toLowerCase()] || ''} [${ev.data?.label?.toUpperCase()}]` :
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
      </div>
    </div>
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

function PatternsSection({ patient }: { patient: string }) {
  const [patterns, setPatterns] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.allSettled([
      api.getMetrics(patient),
      api.getEmotionTimeline(patient, 30),
      api.getRiskAssessmentsForPatient(patient),
      api.getTimeline(patient, 30),
    ]).then(([metricsRes, emoRes, riskRes, timelineRes]) => {
      const metrics = metricsRes.status === 'fulfilled' ? metricsRes.value : null
      const emoData = emoRes.status === 'fulfilled' ? emoRes.value : null
      const risks = riskRes.status === 'fulfilled' ? (riskRes.value || []) : []
      const timelineRaw = timelineRes.status === 'fulfilled' ? timelineRes.value : []
      const timeline = timelineRaw?.events || timelineRaw || []

      const moodEvents = (timeline as any[]).filter((e: any) => e.type === 'mood')
      const journalEvents = (timeline as any[]).filter((e: any) => e.type === 'journal')

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
  }, [patient])

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
