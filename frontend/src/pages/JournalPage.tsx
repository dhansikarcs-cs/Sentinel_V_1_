import { useEffect, useState } from 'react'
import { api } from '../api/client'

export default function JournalPage() {
  const [text, setText] = useState('')
  const [entries, setEntries] = useState<any[]>([])
  const [saving, setSaving] = useState(false)
  const [summary, setSummary] = useState('')

  async function load() {
    try {
      const data = await api.getJournals()
      setEntries(data || [])
    } catch {}
  }

  useEffect(() => { load() }, [])

  async function handleSave() {
    if (!text.trim()) return
    setSaving(true)
    try {
      const res = await api.createJournal(text.trim())
      setSummary(res.summary || '')
      setText('')
      await load()
    } catch (err: any) {
      alert(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-2xl font-semibold">Journal</h1>
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-3">
        <textarea
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder="How are you feeling today?"
          rows={5}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg p-3 text-sm text-gray-200 placeholder-gray-500 resize-none focus:outline-none focus:border-pink-500"
        />
        <button onClick={handleSave} disabled={saving || !text.trim()}
          className="bg-pink-600 hover:bg-pink-500 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg transition-colors">
          {saving ? 'Saving...' : 'Save Entry'}
        </button>
        {summary && (
          <div className="bg-gray-800/50 rounded-lg p-3 text-sm text-gray-400">
            <span className="text-gray-300 font-medium">AI Summary: </span>{summary}
          </div>
        )}
      </div>
      <div className="space-y-3">
        {entries.map((e: any) => (
          <div key={e.id} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="text-xs text-gray-500 mb-1">{new Date(e.created_at).toLocaleDateString()}</div>
            <div className="text-sm text-gray-300 whitespace-pre-wrap">{e.raw_content}</div>
            {e.summary && <div className="text-xs text-gray-500 mt-2 italic">{e.summary}</div>}
          </div>
        ))}
        {entries.length === 0 && <p className="text-gray-600 text-sm">No entries yet.</p>}
      </div>
    </div>
  )
}
