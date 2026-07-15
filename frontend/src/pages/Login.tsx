import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { login } from '../stores/auth'

export default function Login() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      navigate('/dashboard')
    } catch (err: any) {
      setError(err.message || 'Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <form onSubmit={handleSubmit} className="bg-gray-900 border border-gray-800 rounded-xl p-8 w-full max-w-sm space-y-4">
        <h1 className="text-2xl font-bold text-pink-300 text-center">Sentinel</h1>
        <p className="text-sm text-gray-500 text-center">Sign in to your account</p>
        {error && <div className="bg-red-900/30 text-red-400 text-sm p-2 rounded">{error}</div>}
        <div>
          <input
            placeholder="Username"
            value={username}
            onChange={e => setUsername(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-pink-500"
          />
        </div>
        <div>
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-pink-500"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-pink-600 hover:bg-pink-500 disabled:opacity-50 text-white font-medium py-2 px-4 rounded-lg transition-colors"
        >
          {loading ? 'Signing in...' : 'Sign In'}
        </button>
        <p className="text-xs text-gray-500 text-center">
          Don't have an account? <Link to="/register" className="text-pink-400 hover:text-pink-300">Register</Link>
        </p>
      </form>
    </div>
  )
}
