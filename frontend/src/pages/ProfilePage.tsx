import { useEffect, useState } from 'react'
import { getUser, fetchMe } from '../stores/auth'
import { api } from '../api/client'

export default function ProfilePage() {
  const user = getUser()
  const [contact, setContact] = useState(user?.contact_info || '')
  const [trusted, setTrusted] = useState(user?.trusted_contact || '')
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setMsg('')
    try {
      await api.put('/patients/me/contact', { contact_info: contact, trusted_contact: trusted })
      await fetchMe()
      setMsg('Saved successfully.')
    } catch (err: any) {
      setMsg(err.message || 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  useEffect(() => {
    setContact(user?.contact_info || '')
    setTrusted(user?.trusted_contact || '')
  }, [user])

  return (
    <div className="max-w-lg space-y-6">
      <h1 className="text-2xl font-semibold">Profile</h1>
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
        <div>
          <label className="text-xs text-gray-500 uppercase tracking-wide">Name</label>
          <div className="text-sm text-gray-200 mt-1">{user?.name}</div>
        </div>
        <div>
          <label className="text-xs text-gray-500 uppercase tracking-wide">Username</label>
          <div className="text-sm text-gray-200 mt-1">{user?.username}</div>
        </div>
        <div>
          <label className="text-xs text-gray-500 uppercase tracking-wide">Role</label>
          <div className="text-sm text-gray-200 mt-1 capitalize">{user?.role}</div>
        </div>
        <div>
          <label className="text-xs text-gray-500 uppercase tracking-wide">Clinic</label>
          <div className="text-sm text-gray-200 mt-1">{user?.clinic || '—'}</div>
        </div>
        <form onSubmit={handleSave} className="space-y-3 pt-2 border-t border-gray-800">
          <div>
            <label className="text-xs text-gray-500">Contact Info</label>
            <input value={contact} onChange={e => setContact(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm mt-1" />
          </div>
          <div>
            <label className="text-xs text-gray-500">Trusted Contact</label>
            <input value={trusted} onChange={e => setTrusted(e.target.value)}
              placeholder="Name and phone/email"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm mt-1" />
          </div>
          <button type="submit" disabled={saving}
            className="bg-pink-600 hover:bg-pink-500 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg transition-colors">
            {saving ? 'Saving...' : 'Save'}
          </button>
          {msg && <p className="text-xs text-gray-400">{msg}</p>}
        </form>
      </div>
    </div>
  )
}
