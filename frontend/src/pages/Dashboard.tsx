import { useEffect, useState } from 'react'
import { getUser } from '../stores/auth'
import { api } from '../api/client'

export default function Dashboard() {
  const user = getUser()
  const [summary, setSummary] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (user?.username) {
      api.getPatientSummary(user.username).then(setSummary).catch(() => {}).finally(() => setLoading(false))
    }
  }, [user])

  if (!user) return null

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Welcome, {user.name}</h1>
      {loading ? (
        <p className="text-gray-400">Loading summary...</p>
      ) : summary ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card label="Recent Mood" value={summary.recent_mood || '—'} />
          <Card label="Journal Entries" value={String(summary.journal_count || 0)} />
          <Card label="Next Booking" value={summary.next_booking || 'None'} />
        </div>
      ) : (
        <p className="text-gray-500">No summary available</p>
      )}
    </div>
  )
}

function Card({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <div className="text-xs text-gray-500 uppercase tracking-wide">{label}</div>
      <div className="text-lg font-medium text-gray-100 mt-1">{value}</div>
    </div>
  )
}
