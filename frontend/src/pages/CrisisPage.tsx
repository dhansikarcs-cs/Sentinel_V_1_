import { useEffect, useState } from 'react'
import { api } from '../api/client'

export default function CrisisPage() {
  const [state, setState] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  async function load() {
    try {
      const s = await api.getCrisisState()
      setState(s)
    } catch {}
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  async function trigger() {
    try {
      await api.triggerCrisis()
      await load()
    } catch (err: any) { alert(err.message) }
  }

  async function acknowledge() {
    try {
      await api.acknowledgeCrisis()
      await load()
    } catch (err: any) { alert(err.message) }
  }

  async function resolve() {
    try {
      await api.resolveCrisis()
      await load()
    } catch (err: any) { alert(err.message) }
  }

  if (loading) return <p className="text-gray-400">Loading crisis state...</p>

  const isActive = state?.is_active

  return (
    <div className="max-w-lg space-y-6">
      <h1 className="text-2xl font-semibold">Crisis / Emergency</h1>
      <div className={`rounded-xl p-6 border ${isActive ? 'bg-red-900/20 border-red-800' : 'bg-gray-900 border-gray-800'}`}>
        <div className="flex items-center gap-3 mb-4">
          <div className={`w-3 h-3 rounded-full ${isActive ? 'bg-red-500 animate-pulse' : 'bg-gray-600'}`} />
          <span className="text-sm font-medium">{isActive ? 'Active Crisis State' : 'No Active Crisis'}</span>
        </div>
        {!isActive ? (
          <button onClick={trigger} className="bg-red-600 hover:bg-red-500 text-white text-sm px-4 py-2 rounded-lg transition-colors">
            Trigger Crisis Alert
          </button>
        ) : (
          <div className="space-x-3">
            <button onClick={acknowledge} className="bg-yellow-600 hover:bg-yellow-500 text-white text-sm px-4 py-2 rounded-lg transition-colors">
              Acknowledge (Psych)
            </button>
            <button onClick={resolve} className="bg-green-600 hover:bg-green-500 text-white text-sm px-4 py-2 rounded-lg transition-colors">
              Resolve
            </button>
          </div>
        )}
      </div>
      <p className="text-xs text-gray-500">
        Emergency: Contact your trusted person or helpline. If in immediate danger, call emergency services.
      </p>
    </div>
  )
}
