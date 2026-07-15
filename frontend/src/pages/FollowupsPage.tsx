import { useEffect, useState } from 'react'
import { api } from '../api/client'

export default function FollowupsPage() {
  const [tasks, setTasks] = useState<any[]>([])

  async function load() {
    try {
      const data = await api.getFollowups()
      setTasks(data || [])
    } catch {}
  }

  useEffect(() => { load() }, [])

  async function update(id: string, status: string, grade?: string) {
    try {
      await api.updateFollowup(id, { status, grade })
      await load()
    } catch (err: any) { alert(err.message) }
  }

  return (
    <div className="max-w-lg space-y-6">
      <h1 className="text-2xl font-semibold">Follow-Up Tasks</h1>
      {tasks.map((t: any) => (
        <div key={t.id} className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className={`text-sm font-medium ${t.status === 'completed' ? 'text-green-400 line-through' : 'text-gray-200'}`}>
              {t.description}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded ${t.status === 'completed' ? 'bg-green-900/30 text-green-400' : 'bg-yellow-900/30 text-yellow-400'}`}>
              {t.status}
            </span>
          </div>
          {t.due_date && <div className="text-xs text-gray-500">Due: {new Date(t.due_date).toLocaleDateString()}</div>}
          {t.status !== 'completed' && (
            <div className="flex gap-2">
              <button onClick={() => update(t.id, 'completed', t.grade || 'none')}
                className="bg-green-600 hover:bg-green-500 text-xs text-white px-3 py-1 rounded transition-colors">
                Complete
              </button>
              <button onClick={() => update(t.id, 'skipped')}
                className="bg-gray-700 hover:bg-gray-600 text-xs text-gray-300 px-3 py-1 rounded transition-colors">
                Skip
              </button>
            </div>
          )}
        </div>
      ))}
      {tasks.length === 0 && <p className="text-gray-600 text-sm">No pending follow-ups.</p>}
    </div>
  )
}
