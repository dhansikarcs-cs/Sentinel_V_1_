import { useEffect, useState } from 'react'
import { api } from '../api/client'

const moods = [
  { emoji: '😊', label: 'Good' },
  { emoji: '😐', label: 'Okay' },
  { emoji: '😢', label: 'Sad' },
  { emoji: '😤', label: 'Irritable' },
  { emoji: '😰', label: 'Anxious' },
  { emoji: '😴', label: 'Tired' },
]

export default function MoodPage() {
  const [logs, setLogs] = useState<any[]>([])
  const [todayDone, setTodayDone] = useState(false)

  async function load() {
    try {
      const data = await api.getMoods()
      setLogs(data || [])
    } catch {}
    try {
      const t = await api.checkTodayMood()
      setTodayDone(t.logged ?? false)
    } catch {}
  }

  useEffect(() => { load() }, [])

  async function handleMood(m: typeof moods[0]) {
    const date = new Date().toISOString().split('T')[0]
    try {
      await api.logMood(date, m.emoji, m.label)
      setTodayDone(true)
      await load()
    } catch (err: any) {
      alert(err.message)
    }
  }

  return (
    <div className="max-w-lg space-y-6">
      <h1 className="text-2xl font-semibold">Mood Log</h1>
      {!todayDone ? (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <p className="text-sm text-gray-400 mb-3">How are you feeling right now?</p>
          <div className="flex gap-3 flex-wrap">
            {moods.map(m => (
              <button key={m.label} onClick={() => handleMood(m)}
                className="flex flex-col items-center gap-1 p-3 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors">
                <span className="text-2xl">{m.emoji}</span>
                <span className="text-xs text-gray-400">{m.label}</span>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-sm text-gray-400">
          Mood logged for today. Check back tomorrow!
        </div>
      )}
      <div className="space-y-2">
        {logs.slice(-14).reverse().map((l: any) => (
          <div key={l.id} className="flex items-center gap-3 bg-gray-900 border border-gray-800 rounded-lg px-4 py-2">
            <span className="text-lg">{l.emoji}</span>
            <span className="text-xs text-gray-500">{l.date}</span>
            <span className="text-sm text-gray-300">{l.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
