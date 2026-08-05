import { useEffect, useState } from 'react'
import { api } from '../api/client'

const ACTION_ICONS: Record<string, string> = {
  journal: '📝',
  mood: '😊',
  crisis: '🚨',
  booking: '📅',
  clinical_note: '📋',
  followup: '📋',
}

const SEVERITY_COLORS: Record<string, string> = {
  high: '#ef4444',
  medium: '#f59e0b',
  info: '#7d877e',
}

export default function ActivityFeedPage() {
  const [events, setEvents] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [days, setDays] = useState(7)

  useEffect(() => {
    setLoading(true)
    api.getActivityFeed(days).then((d: any) => {
      setEvents(Array.isArray(d?.events) ? d.events : [])
    }).catch(() => {}).finally(() => setLoading(false))
  }, [days])

  return (
    <div className="animate-fade-in">
      <h1>📡 Activity Feed</h1>

      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', alignItems: 'center' }}>
        <span style={{ color: '#7d877e', fontSize: '0.8125rem' }}>Show last:</span>
        {[1, 3, 7, 14, 30].map(d => (
          <button key={d} onClick={() => setDays(d)}
            style={{
              padding: '6px 14px', borderRadius: '6px', border: `1px solid ${days === d ? '#8fcbb1' : '#31423a'}`,
              background: days === d ? '#27322d' : '#1d2623', color: days === d ? '#8fcbb1' : '#9ca99e',
              fontSize: '0.8125rem', cursor: 'pointer',
            }}>
            {d}d
          </button>
        ))}
      </div>

      {loading ? (
        <div className="card"><span style={{ color: '#7d877e' }}>Loading...</span></div>
      ) : events.length === 0 ? (
        <div className="card"><span style={{ color: '#7d877e' }}>No activity found.</span></div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          {events.map((e: any, i: number) => (
            <div key={i} style={{
              display: 'flex', alignItems: 'center', gap: '10px',
              padding: '8px 12px', background: '#19211e',
              borderBottom: '1px solid #31423a', borderRadius: '4px',
            }}>
              <span style={{ fontSize: '1rem' }}>{ACTION_ICONS[e.type] || '💬'}</span>
              <span style={{
                width: '8px', height: '8px', borderRadius: '50%',
                background: SEVERITY_COLORS[e.severity] || '#7d877e',
                flexShrink: 0,
              }} />
              <span style={{ color: '#8aa198', fontSize: '0.6875rem', minWidth: '140px' }}>
                {(e.timestamp || '').slice(0, 16).replace('T', ' ')}
              </span>
              <span style={{ color: '#8fcbb1', fontSize: '0.75rem', fontWeight: 600, minWidth: '80px' }}>
                {e.patient}
              </span>
              <span style={{ color: '#bac9bf', fontSize: '0.75rem', flex: 1 }}>
                {e.summary || e.type}
              </span>
            </div>
          ))}
          <div style={{ color: '#3d4d45', fontSize: '0.6875rem', textAlign: 'center', padding: '12px' }}>
            Showing {events.length} events
          </div>
        </div>
      )}
    </div>
  )
}
