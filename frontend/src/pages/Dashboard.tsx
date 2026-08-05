import { useEffect, useState } from 'react'
import { AreaChart, Area, Tooltip, ResponsiveContainer, XAxis, YAxis } from 'recharts'
import { api } from '../api/client'
import { mockHistory } from '../constants'

export default function Dashboard() {
  const [wellness, setWellness] = useState<any>(null)
  const [sensorLogs, setSensorLogs] = useState<any[]>([])
  const [showTable, setShowTable] = useState(false)

  useEffect(() => {
    api.getWellness().then(setWellness).catch(() => {})
    api.getSensorData().then((d: any[]) => {
      if (Array.isArray(d) && d.length > 0) {
        const sorted = [...d].reverse()
        setSensorLogs(sorted)
      } else {
        setSensorLogs([])
      }
    }).catch(() => {})
  }, [])

  const ring = wellness?.ring || { bpm: 72, stress: 35, sleep: 7, spo2: 98, hrv: 45 }

  const trends = [
    { key: 'bpm', label: 'Heart Rate', unit: 'bpm', color: '#CC5A4E', data: sensorLogs.length > 0 ? sensorLogs.map(s => ({ v: s.bpm || 0 })) : mockHistory(ring.bpm || 72, 12).map(v => ({ v })) },
    { key: 'stress', label: 'Stress', unit: '%', color: '#ffd93d', data: sensorLogs.length > 0 ? sensorLogs.map(s => ({ v: s.stress || 0 })) : mockHistory(ring.stress || 35, 10).map(v => ({ v })) },
    { key: 'sleep_hours', label: 'Sleep', unit: 'hrs', color: '#6bcbff', data: sensorLogs.length > 0 ? sensorLogs.map(s => ({ v: s.sleep_hours || 0 })) : mockHistory(ring.sleep || 7, 1.5).map(v => ({ v })) },
    { key: 'spo2', label: 'SpO₂', unit: '%', color: '#6bffb8', data: sensorLogs.length > 0 ? sensorLogs.map(s => ({ v: s.spo2 || 0 })) : mockHistory(ring.spo2 || 98, 1).map(v => ({ v })) },
  ]

  return (
    <div className="animate-fade-in space-y-4">
      <h2>📊 Wellness Dashboard</h2>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '8px' }}>
        {trends.map(t => (
          <div key={t.key} className="card" style={{ padding: '12px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: 'var(--secondary)', fontSize: '0.75rem' }}>{t.label}</span>
              <span style={{ color: t.color, fontSize: '1rem', fontWeight: 700 }}>{t.data[t.data.length - 1]?.v || '-'}{t.unit === '%' ? '%' : t.unit === 'hrs' ? 'h' : ''}</span>
            </div>
            <ResponsiveContainer width="100%" height={80}>
              <AreaChart data={t.data}>
                <defs>
                  <linearGradient id={`grad_${t.key}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={t.color} stopOpacity={0.25} />
                    <stop offset="100%" stopColor={t.color} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="name" hide />
                <YAxis hide domain={['dataMin - 2', 'dataMax + 2']} />
                <Tooltip
                  contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px', fontSize: '0.75rem' }}
                  labelStyle={{ color: 'var(--muted)' }}
                  formatter={(val: any) => [`${val}${t.unit === '%' ? '%' : t.unit === 'hrs' ? 'h' : ''}`, t.label]}
                />
                <Area type="monotone" dataKey="v" stroke={t.color} strokeWidth={1.5} fill={`url(#grad_${t.key})`} dot={false} activeDot={{ r: 3, fill: t.color }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '4px' }}>
        <button
          onClick={() => setShowTable(!showTable)}
          className="btn-secondary"
          style={{ fontSize: '0.75rem', padding: '4px 12px', width: 'auto' }}
        >
          {showTable ? '📊 Show Charts' : '📋 Show as Table'}
        </button>
        <span style={{ color: 'var(--faint)', fontSize: '0.6875rem' }}>24-hour trend data</span>
      </div>

      {showTable && (
        <div className="card" style={{ padding: '16px', overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <th style={{ padding: '6px 8px', textAlign: 'left', color: 'var(--secondary)' }}>#</th>
                {trends.map(t => <th key={t.key} style={{ padding: '6px 8px', textAlign: 'right', color: t.color }}>{t.label}</th>)}
              </tr>
            </thead>
            <tbody>
              {trends[0].data.slice(-24).map((_, i) => (
                <tr key={i} style={{ borderBottom: '1px solid var(--surface)' }}>
                  <td style={{ padding: '4px 8px', color: 'var(--muted)' }}>{i + 1}</td>
                  {trends.map(t => (
                    <td key={t.key} style={{ padding: '4px 8px', textAlign: 'right', color: 'var(--text)' }}>{t.data[t.data.length - 24 + i]?.v ?? '-'}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="card" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Today's Mood</div>
            <div style={{ fontSize: '2rem' }}>{wellness?.mood?.emoji || '\u{1F610}'}</div>
            <div style={{ fontSize: '0.8125rem', color: 'var(--secondary)' }}>{wellness?.mood?.label || 'Not logged'}</div>
          </div>
          <div style={{ width: '1px', height: '40px', background: 'var(--border)' }} />
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Journal Activity</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--heading)' }}>{wellness?.journals_today || 0}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>entries today</div>
          </div>
        </div>
      </div>

      {wellness?.mood_trend && wellness.mood_trend.length > 0 && (
        <div className="card" style={{ padding: '20px' }}>
          <div style={{ fontSize: '0.8125rem', color: 'var(--secondary)', fontWeight: 600, marginBottom: '12px' }}>Mood Trend (7 days)</div>
          <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', flexWrap: 'wrap' }}>
            {wellness.mood_trend.map((m: any, i: number) => (
              <div key={i} style={{ textAlign: 'center', padding: '8px', background: 'var(--surface)', borderRadius: '8px', minWidth: '60px' }}>
                <div style={{ fontSize: '1.5rem' }}>{m.emoji}</div>
                <div style={{ fontSize: '0.65rem', color: 'var(--muted)', marginTop: '2px' }}>{m.date?.slice(-2)}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {wellness?.ai_insights && (
        <div className="expander">
          <details>
            <summary className="expander-header">📊 My Insights (AI-Powered)</summary>
            <div className="expander-body">
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '12px' }}>
                <div className="metric-card" style={{ textAlign: 'center', padding: '12px' }}>
                  <div style={{ color: 'var(--secondary)', fontSize: '0.75rem' }}>📝 Journals (7d)</div>
                  <div style={{ color: 'var(--heading)', fontSize: '1.5rem', fontWeight: 700 }}>{wellness.ai_insights.journal_count || 0}</div>
                </div>
                <div className="metric-card" style={{ textAlign: 'center', padding: '12px' }}>
                  <div style={{ color: 'var(--secondary)', fontSize: '0.75rem' }}>✅ Compliance</div>
                  <div style={{ color: 'var(--heading)', fontSize: '1.5rem', fontWeight: 700 }}>{wellness.ai_insights.compliance || 0}%</div>
                </div>
                <div className="metric-card" style={{ textAlign: 'center', padding: '12px' }}>
                  <div style={{ color: 'var(--secondary)', fontSize: '0.75rem' }}>❌ Missed</div>
                  <div style={{ color: 'var(--heading)', fontSize: '1.5rem', fontWeight: 700 }}>{wellness.ai_insights.missed || 0}</div>
                </div>
              </div>
              {wellness.ai_insights.grades && (
                <div style={{ color: 'var(--muted)', fontSize: '0.75rem', marginBottom: '8px' }}>
                  Grades: 🟢{wellness.ai_insights.grades.green || 0}  🟡{wellness.ai_insights.grades.yellow || 0}  🔴{wellness.ai_insights.grades.red || 0}
                </div>
              )}
              {wellness.ai_insights.mood_message && (
                <div style={{ color: 'var(--secondary)', fontSize: '0.8125rem', marginBottom: '4px' }}>{wellness.ai_insights.mood_message}</div>
              )}
              <div style={{ marginTop: '6px', color: 'var(--muted)', fontSize: '0.65rem', lineHeight: 1.5 }}>
                AI-generated insights, not reviewed by your psychologist. Sentinel assists monitoring — it never determines whether you are safe. If you feel unsafe, seek help immediately.
              </div>
              {wellness.ai_insights.relapse_flag && (
                <div className="card" style={{ borderColor: 'rgba(199,70,59,0.4)', color: 'var(--danger)', fontSize: '0.8125rem' }}>
                  ⚠️ {wellness.ai_insights.relapse_message || 'Warning flagged'}
                </div>
              )}
            </div>
          </details>
        </div>
      )}
    </div>
  )
}
