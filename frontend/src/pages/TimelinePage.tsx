import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { getUser } from '../stores/auth'
import { moodIcon, formatTime } from '../constants'
import PatientSelector from '../components/PatientSelector'

function eventBorder(type: string) {
  return { borderLeft: `3px solid ${type === 'mood' ? '#22c55e' : type === 'journal' ? '#6366f1' : type === 'followup' ? '#f59e0b' : '#ef4444'}`, background: '#111827', borderRadius: '6px', padding: '8px 12px', margin: '4px 0' }
}

export default function TimelinePage() {
  const user = getUser()
  const [patients, setPatients] = useState<any[]>([])
  const [selectedPatient, setSelectedPatient] = useState('')
  const [days, setDays] = useState(30)
  const [metrics, setMetrics] = useState<any>(null)
  const [events, setEvents] = useState<any[]>([])
  const isPsych = user?.role === 'psychologist'

  useEffect(() => {
    if (isPsych) api.getPsychPatients().then(d => setPatients(d || [])).catch(() => {})
    else if (user?.username) { setSelectedPatient(user.username); fetchData(user.username) }
  }, [])

  useEffect(() => { if (selectedPatient) fetchData(selectedPatient) }, [selectedPatient, days])

  async function fetchData(patient: string) {
    try {
      const [m, e] = await Promise.all([
        api.getMetrics(patient),
        api.getTimeline(patient, days)
      ])
      setMetrics(m || {})
      setEvents(e?.events || e || [])
    } catch {}
  }

  return (
    <div className="animate-fade-in">
      {isPsych && (
        <div>
          <h2>🔍 Behavioral Timeline</h2>
          <div style={{ color: '#7d877e', fontSize: '0.85rem', marginBottom: '16px' }}>
            Track behavioral evolution across time — not isolated symptoms. Select a patient to see their unified event feed and change metrics.
          </div>
          <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
            <div style={{ flex: 2 }}>
              <label>Select Patient</label>
              <PatientSelector patients={patients} value={selectedPatient} onChange={setSelectedPatient} placeholder="Select..." />
            </div>
            <div style={{ flex: 1 }}>
              <label>Time range</label>
              <input type="range" min={7} max={90} value={days} onChange={e => setDays(Number(e.target.value))} style={{ padding: '0' }} />
              <div style={{ color: '#7d877e', fontSize: '0.75rem', textAlign: 'center' }}>{days} days</div>
            </div>
          </div>
        </div>
      )}

      {!isPsych && <h2>📋 Behavioral Timeline</h2>}

      {!selectedPatient ? (
        <div className="card"><span style={{ color: '#7d877e' }}>Select a patient to view their timeline.</span></div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '24px' }}>
          {/* Metrics Panel */}
          <div>
            <h3>📊 Change Metrics</h3>
            <div className="card-dark" style={{ padding: '14px' }}>
              {metrics && (
                <>
                  <div style={{ marginBottom: '10px' }}>
                    <div style={{ color: '#7d877e', fontSize: '0.7rem' }}>MOOD TREND (7d vs 7-14d ago)</div>
                    <div style={{ color: metrics.mood_trend === 'improving' ? '#22c55e' : metrics.mood_trend === 'declining' ? '#ef4444' : '#fbbf24', fontSize: '1.3rem', fontWeight: 700 }}>
                      {metrics.mood_trend === 'improving' ? '↗️ improving' : metrics.mood_trend === 'declining' ? '↘️ declining' : metrics.mood_trend === 'stable' ? '→️ stable' : '—'}
                    </div>
                    <div style={{ color: '#8aa198', fontSize: '0.75rem' }}>
                      Current avg: {metrics.current_mood_avg ? `${metrics.current_mood_avg.toFixed(1)}/5` : 'N/A'} | Previous: {metrics.previous_mood_avg ? `${metrics.previous_mood_avg.toFixed(1)}/5` : 'N/A'}
                    </div>
                  </div>

                  <div style={{ marginBottom: '10px' }}>
                    <div style={{ color: '#7d877e', fontSize: '0.7rem' }}>ENGAGEMENT (journal entries)</div>
                    <div style={{ color: metrics.engagement_trend === 'increasing' ? '#22c55e' : metrics.engagement_trend === 'declining' ? '#ef4444' : '#fbbf24', fontSize: '1.3rem', fontWeight: 700 }}>
                      {metrics.engagement_trend === 'increasing' ? '↗️' : metrics.engagement_trend === 'declining' ? '↘️' : metrics.engagement_trend === 'stable' ? '→️' : '—'}
                    </div>
                    <div style={{ color: '#8aa198', fontSize: '0.75rem' }}>
                      Last 7d: {metrics.journal_count_7 || 0} | Last 14d: {metrics.journal_count_14 || 0}
                    </div>
                  </div>

                      {metrics.latest_mood && (
                    <div>
                      <div style={{ color: '#7d877e', fontSize: '0.7rem' }}>LATEST MOOD</div>
                      <div style={{ fontSize: '1.5rem' }}>{moodIcon(metrics.latest_mood.label)}</div>
                      <div style={{ color: '#8aa198', fontSize: '0.75rem' }}>{metrics.latest_mood.label} — {formatTime(metrics.latest_mood.timestamp)}</div>
                    </div>
                  )}
                </>
              )}
              {!metrics && <div style={{ color: '#7d877e', fontSize: '0.8125rem' }}>No data available.</div>}
            </div>
          </div>

          {/* Event Feed */}
          <div>
            <h3>📅 Event Feed</h3>
            {events.length === 0 ? (
              <div className="card"><span style={{ color: '#7d877e' }}>No events in the selected time period.</span></div>
            ) : (
              <div style={{ maxHeight: '500px', overflowY: 'auto', paddingRight: '6px' }}>
                {events.map((ev: any, i: number) => {
                  const etype = ev.type
                  if (etype === 'mood') {
                    const label = ev.data?.label || 'unknown'
                    return (
                      <div key={i} style={eventBorder(etype)}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div><span style={{ color: '#e0e8f0', fontWeight: 600, fontSize: '0.85rem' }}>{moodIcon(label)} [{label.toUpperCase()}]</span></div>
                          <span style={{ color: '#7d877e', fontSize: '0.7rem' }}>{formatTime(ev.timestamp)}</span>
                        </div>
                        <div style={{ color: '#8aa198', fontSize: '0.75rem', marginTop: '2px' }}>Mood logged: {label} on {ev.data?.date || ''}</div>
                      </div>
                    )
                  }
                  if (etype === 'journal') {
                    const d = ev.data || {}
                    return (
                      <div key={i} style={eventBorder(etype)}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div><span style={{ color: '#e0e8f0', fontWeight: 600, fontSize: '0.85rem' }}>📝 {d.title || 'Journal Entry'}</span></div>
                          <span style={{ color: '#7d877e', fontSize: '0.7rem' }}>{formatTime(ev.timestamp)}</span>
                        </div>
                        <div style={{ color: '#8aa198', fontSize: '0.75rem', marginTop: '2px' }}>{(d.summary || '').slice(0, 200)}</div>
                      </div>
                    )
                  }
                  if (etype === 'followup') {
                    const d = ev.data || {}
                    return (
                      <div key={i} style={eventBorder(etype)}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div><span style={{ color: '#e0e8f0', fontWeight: 600, fontSize: '0.85rem' }}>{d.status === 'completed' ? '✅' : '⏳'} {d.title || 'Task'}</span></div>
                          <span style={{ color: '#7d877e', fontSize: '0.7rem' }}>{formatTime(d.completed_at || d.assigned_at || '')}</span>
                        </div>
                        <div style={{ color: '#8aa198', fontSize: '0.75rem', marginTop: '2px' }}>{d.description || ''}</div>
                      </div>
                    )
                  }
                  if (etype === 'crisis') {
                    const d = ev.data || {}
                    return (
                      <div key={i} style={eventBorder(etype)}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div><span style={{ color: '#e0e8f0', fontWeight: 600, fontSize: '0.85rem' }}>🚨 {(d.event || 'Crisis').toUpperCase()}</span></div>
                          <span style={{ color: '#7d877e', fontSize: '0.7rem' }}>{formatTime(ev.timestamp)}</span>
                        </div>
                        <div style={{ color: '#8aa198', fontSize: '0.75rem', marginTop: '2px' }}>{d.details || d.event || ''}</div>
                      </div>
                    )
                  }
                  return null
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
