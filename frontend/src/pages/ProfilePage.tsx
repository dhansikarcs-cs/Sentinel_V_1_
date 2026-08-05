import { useEffect, useState } from 'react'
import { getUser, fetchMe } from '../stores/auth'
import { api } from '../api/client'

export default function ProfilePage() {
  const user = getUser()
  const [contact, setContact] = useState(user?.contact_info || '')
  const [trusted, setTrusted] = useState(user?.trusted_contact || '')
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')

  useEffect(() => {
    setContact(user?.contact_info || '')
    setTrusted(user?.trusted_contact || '')
  }, [user])

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setMsg('')
    try {
      await api.updateContact({ contact_info: contact, trusted_contact: trusted })
      await fetchMe()
      setMsg('Saved successfully.')
    } catch (err: any) {
      setMsg(err.message || 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  if (!user) return null

  return (
    <div className="space-y-6 animate-fade-in">
      <h1>👤 My Profile</h1>
      <div className="card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div className="grid grid-cols-2" style={{ gap: '16px' }}>
          {[
            { label: 'Name', value: user.name },
            { label: 'Username', value: user.username },
            { label: 'Role', value: user.role },
            { label: 'Clinic', value: user.clinic || '\u2014' },
          ].map(f => (
            <div key={f.label}>
              <div className="metric-label">{f.label}</div>
              <div style={{ fontSize: '0.9rem', color: 'var(--heading)', marginTop: '2px' }}>{f.value}</div>
            </div>
          ))}
        </div>
        <hr />
        <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div>
            <label style={{ fontSize: '0.75rem', color: 'var(--secondary)', fontWeight: 500, marginBottom: '4px', display: 'block' }}>Contact Info</label>
            <input value={contact} onChange={e => setContact(e.target.value)} placeholder="Phone or email" style={{ width: '100%', padding: '10px 12px', fontSize: '0.875rem' }} />
          </div>
          <div>
            <label style={{ fontSize: '0.75rem', color: 'var(--secondary)', fontWeight: 500, marginBottom: '4px', display: 'block' }}>Trusted Contact</label>
            <input value={trusted} onChange={e => setTrusted(e.target.value)} placeholder="Name and phone/email" style={{ width: '100%', padding: '10px 12px', fontSize: '0.875rem' }} />
          </div>
          <div className="flex items-center gap-3">
            <button type="submit" disabled={saving} className="btn-primary">{saving ? 'Saving...' : '💾 Save'}</button>
            {msg && <span style={{ fontSize: '0.75rem', color: msg === 'Saved successfully.' ? 'var(--ok)' : 'var(--danger)' }}>{msg}</span>}
          </div>
        </form>
      </div>
    </div>
  )
}
