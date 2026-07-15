import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'

export default function Unlock() {
  const navigate = useNavigate()
  const [passphrase, setPassphrase] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await api.unlock(passphrase)
      navigate('/dashboard')
    } catch (err: any) {
      setError(err.message || 'Incorrect passphrase')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <form onSubmit={handleSubmit} className="bg-gray-900 border border-gray-800 rounded-xl p-8 w-full max-w-sm space-y-4">
        <h1 className="text-xl font-bold text-pink-300 text-center">Encryption Unlock</h1>
        <p className="text-xs text-gray-500 text-center">Enter your passphrase to decrypt session data</p>
        {error && <div className="bg-red-900/30 text-red-400 text-sm p-2 rounded">{error}</div>}
        <input type="password" placeholder="Passphrase" value={passphrase} onChange={e => setPassphrase(e.target.value)}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm" />
        <button type="submit" disabled={loading}
          className="w-full bg-pink-600 hover:bg-pink-500 disabled:opacity-50 text-white font-medium py-2 px-4 rounded-lg transition-colors">
          {loading ? 'Unlocking...' : 'Unlock'}
        </button>
      </form>
    </div>
  )
}
