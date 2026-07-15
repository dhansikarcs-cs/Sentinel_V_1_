import { useEffect, useState } from 'react'
import { api } from '../api/client'

export default function BookingsPage() {
  const [bookings, setBookings] = useState<any[]>([])
  const [psychs, setPsychs] = useState<any[]>([])
  const [psychId, setPsychId] = useState('')
  const [slot, setSlot] = useState('')
  const [loading, setLoading] = useState(true)

  async function load() {
    try {
      const [b, p] = await Promise.all([api.getBookings(), api.getAvailablePsychs()])
      setBookings(b || [])
      setPsychs(p || [])
    } catch {}
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  async function handleBook() {
    if (!psychId || !slot) return
    try {
      await api.createBooking({ psych_id: Number(psychId), slot })
      setPsychId('')
      setSlot('')
      await load()
    } catch (err: any) { alert(err.message) }
  }

  if (loading) return <p className="text-gray-400">Loading...</p>

  return (
    <div className="max-w-lg space-y-6">
      <h1 className="text-2xl font-semibold">Bookings</h1>
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-3">
        <h2 className="text-sm font-medium text-gray-300">New Booking</h2>
        <select value={psychId} onChange={e => setPsychId(e.target.value)}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm">
          <option value="">Select psychologist...</option>
          {psychs.map((p: any) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
        <input type="datetime-local" value={slot} onChange={e => setSlot(e.target.value)}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm" />
        <button onClick={handleBook} disabled={!psychId || !slot}
          className="bg-pink-600 hover:bg-pink-500 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg transition-colors">
          Book Session
        </button>
      </div>
      <div className="space-y-2">
        {bookings.map((b: any) => (
          <div key={b.id} className="flex items-center justify-between bg-gray-900 border border-gray-800 rounded-lg px-4 py-3">
            <div>
              <div className="text-sm text-gray-300">{new Date(b.slot).toLocaleString()}</div>
              <div className="text-xs text-gray-500">{b.psych_name || 'Psychologist'}</div>
            </div>
            <span className={`text-xs px-2 py-1 rounded ${b.status === 'confirmed' ? 'bg-green-900/30 text-green-400' : b.status === 'cancelled' ? 'bg-red-900/30 text-red-400' : 'bg-yellow-900/30 text-yellow-400'}`}>
              {b.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
