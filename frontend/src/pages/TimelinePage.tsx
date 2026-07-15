import { useEffect, useState } from 'react'
import { getUser } from '../stores/auth'
import { api } from '../api/client'

export default function TimelinePage() {
  const user = getUser()
  const [events, setEvents] = useState<any[]>([])
  const [metrics, setMetrics] = useState<any>(null)

  useEffect(() => {
    if (!user?.username) return
    api.getTimeline(user.username).then(setEvents).catch(() => {})
    api.getMetrics(user.username).then(setMetrics).catch(() => {})
  }, [user])

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-2xl font-semibold">Behavioral Timeline</h1>

      {metrics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricBox label="Mood Trend" value={metrics.mood_trend || 'stable'}
            color={metrics.mood_trend === 'improving' ? 'text-green-400' : metrics.mood_trend === 'declining' ? 'text-red-400' : 'text-yellow-400'} />
          <MetricBox label="Mood Change" value={metrics.mood_change_pct != null ? `${metrics.mood_change_pct}%` : '—'} color="text-gray-300" />
          <MetricBox label="Engagement" value={metrics.engagement_trend || 'stable'}
            color={metrics.engagement_trend === 'increasing' ? 'text-green-400' : 'text-gray-300'} />
          <MetricBox label="Latest Mood" value={metrics.latest_mood || '—'} color="text-gray-300" />
        </div>
      )}

      <div className="space-y-3">
        {events.map((e: any, i: number) => (
          <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-xs px-2 py-0.5 rounded ${
                e.type === 'crisis' ? 'bg-red-900/30 text-red-400' :
                e.type === 'mood' ? 'bg-blue-900/30 text-blue-400' :
                e.type === 'journal' ? 'bg-purple-900/30 text-purple-400' :
                'bg-gray-800 text-gray-400'
              }`}>{e.type}</span>
              <span className="text-xs text-gray-500">{new Date(e.date).toLocaleDateString()}</span>
            </div>
            <div className="text-sm text-gray-300">{e.description}</div>
          </div>
        ))}
        {events.length === 0 && <p className="text-gray-600 text-sm">No timeline events yet.</p>}
      </div>
    </div>
  )
}

function MetricBox({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-3">
      <div className="text-xs text-gray-500 uppercase tracking-wide">{label}</div>
      <div className={`text-sm font-medium mt-1 ${color}`}>{value}</div>
    </div>
  )
}
