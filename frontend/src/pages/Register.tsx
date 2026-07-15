import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '../api/client'

export default function Register() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', password: '', name: '', role: 'patient', clinic: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await api.register(form)
      navigate('/login')
    } catch (err: any) {
      setError(err.message || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <form onSubmit={handleSubmit} className="bg-gray-900 border border-gray-800 rounded-xl p-8 w-full max-w-sm space-y-4">
        <h1 className="text-2xl font-bold text-pink-300 text-center">Register</h1>
        {error && <div className="bg-red-900/30 text-red-400 text-sm p-2 rounded">{error}</div>}
        <input placeholder="Username" value={form.username} onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm" />
        <input type="password" placeholder="Password" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm" />
        <input placeholder="Full Name" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm" />
        <input placeholder="Clinic / Institution Code" value={form.clinic} onChange={e => setForm(f => ({ ...f, clinic: e.target.value }))}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm" />
        <select value={form.role} onChange={e => setForm(f => ({ ...f, role: e.target.value }))}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm">
          <option value="patient">Patient</option>
          <option value="psychologist">Psychologist</option>
          <option value="admin">Admin</option>
        </select>
        <button type="submit" disabled={loading}
          className="w-full bg-pink-600 hover:bg-pink-500 disabled:opacity-50 text-white font-medium py-2 px-4 rounded-lg transition-colors">
          {loading ? 'Registering...' : 'Register'}
        </button>
        <p className="text-xs text-gray-500 text-center">
          Already have an account? <Link to="/login" className="text-pink-400">Sign in</Link>
        </p>
      </form>
    </div>
  )
}
