import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { getUser } from '../stores/auth'
import PatientSelector from '../components/PatientSelector'

const STATUS_COLORS: Record<string, string> = { Approved: '#2E8B57', Rejected: '#C7463B', Cancelled: '#6E837A', Pending: '#17796E' }
const STATUS_ICONS: Record<string, string> = { Approved: '✅', Rejected: '❌', Cancelled: '🔴', Pending: '⏳' }

export default function BookingsPage() {
  const user = getUser()
  const isPsych = user?.role === 'psychologist'

  if (isPsych) return <PsychBookings />
  return <PatientBookings />
}

function PatientBookings() {
  const [bookings, setBookings] = useState<any[]>([])
  const [tab, setTab] = useState(0)

  useEffect(() => { api.getBookings().then(d => setBookings(d || [])).catch(() => {}) }, [])

  const aiBookings = (bookings || []).filter((b: any) => b.explanation?.includes('AI-suggested'))
  const manualBookings = bookings.filter((b: any) => !b.explanation?.includes('AI-suggested'))
  const proposed = aiBookings.filter((b: any) => b.status === 'Proposed')
  const pastAi = aiBookings.filter((b: any) => b.status !== 'Proposed')

  async function handleAction(booking: any, action: string) {
    try {
      await api.updateBookingStatus(booking.id, action)
      const updated = await api.getBookings()
      setBookings(updated || [])
    } catch (err: any) { alert(err.message) }
  }

  return (
    <div className="animate-fade-in">
      <h2>📅 Booking</h2>
      {bookings.length > 0 && (
        <div style={{ fontSize: '0.8125rem', marginBottom: '16px' }}>
          {(() => {
            const latest = bookings[bookings.length - 1]
            if (latest.status === 'Approved') return <div style={{ color: '#2E8B57' }}>✅ Your last request was <strong>Approved</strong>. Check your contact for details.</div>
            if (latest.status === 'Rejected') return <div style={{ color: '#C7463B' }}>❌ Your last request was <strong>Rejected</strong>.</div>
            return <div style={{ color: '#17796E' }}>⏳ Your request is <strong>Pending Review</strong> by the clinician.</div>
          })()}
        </div>
      )}

      <div className="sub-tabs">
        <button className={`sub-tab ${tab === 0 ? 'active' : ''}`} onClick={() => setTab(0)}>📨 Psych Suggested</button>
        <button className={`sub-tab ${tab === 1 ? 'active' : ''}`} onClick={() => setTab(1)}>📅 Book Appointment</button>
      </div>

      {tab === 0 && (
        <div>
          {proposed.length > 0 ? (
            <>
              <div className="card" style={{ borderColor: '#B7791A' }}>
                <div style={{ color: '#B7791A', fontSize: '0.75rem', fontWeight: 600 }}>💡 NEW — Psychologist Suggested</div>
                <div style={{ color: '#6E837A', fontSize: '0.75rem', marginTop: '4px' }}>
                  Your psychologist recommended the following appointment. Accept to request a review or decline to suggest a different time.
                </div>
              </div>
              {proposed.map((b: any, i: number) => (
                <div key={i} className="card" style={{ borderColor: '#B7791A' }}>
                  <div style={{ color: '#B7791A', fontSize: '0.9rem', fontWeight: 600 }}>{b.date} @ {b.time}</div>
                  <div style={{ color: '#6E837A', fontSize: '0.75rem', marginTop: '4px' }}>{b.explanation}</div>
                  <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                    <button className="btn-primary" onClick={() => handleAction(b, 'Approved')}>✅ Accept</button>
                    <button onClick={() => handleAction(b, 'Rejected')}>❌ Decline</button>
                  </div>
                </div>
              ))}
            </>
          ) : (
            <div className="card"><span style={{ color: '#6E837A', fontSize: '0.875rem' }}>No suggestions from your psychologist yet.</span></div>
          )}
          {pastAi.length > 0 && (
            <div style={{ marginTop: '16px' }}>
              <h3>History</h3>
              <div className="space-y-2">
                {pastAi.slice(-5).reverse().map((b: any, i: number) => (
                  <div key={i} className="card-stage" style={{ justifyContent: 'space-between' }}>
                    <span style={{ fontSize: '0.75rem' }}>{STATUS_ICONS[b.status] || '⚪'} <strong>{b.date} @ {b.time}</strong></span>
                    <span style={{ fontSize: '0.6875rem', color: STATUS_COLORS[b.status] || '#6E837A' }}>{b.status}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 1 && <PatientBookingForm />}
    </div>
  )
}

function PatientBookingForm() {
  const [psychs, setPsychs] = useState<any[]>([])
  const [selectedPsych, setSelectedPsych] = useState('')
  const [availableDates, setAvailableDates] = useState<string[]>([])
  const [selectedDate, setSelectedDate] = useState('')
  const [time, setTime] = useState('10:00')
  const [sessionType, setSessionType] = useState('Therapy')
  const [memberCount, setMemberCount] = useState(1)
  const [members, setMembers] = useState<{ name: string; age: number }[]>([{ name: '', age: 25 }])
  const [contact, setContact] = useState('')
  const [context, setContext] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api.getAvailablePsychs().then(d => setPsychs(d || [])).catch(() => {})
  }, [])

  useEffect(() => {
    if (!selectedPsych) { setAvailableDates([]); return }
    api.get(`/psychologists/${selectedPsych}/availability`).then((dates: string[]) => {
      setAvailableDates(dates || [])
    }).catch(() => {})
  }, [selectedPsych])

  useEffect(() => {
    setMembers(Array.from({ length: memberCount }, (_, i) => members[i] || { name: '', age: 25 }))
  }, [memberCount])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!selectedPsych || !selectedDate || !contact.trim() || !context.trim() || members.some(m => !m.name.trim())) {
      alert('Please fill all required fields.')
      return
    }
    setSaving(true)
    try {
      await api.createBooking({
        patient: getUser()?.username,
        psychologist_username: selectedPsych,
        date: selectedDate,
        time,
        session_type: sessionType,
        members: members.map(m => `${m.name.trim()} (${m.age})`).join('; '),
        contact: contact.trim(),
        explanation: context.trim(),
      })
      alert('Request sent!')
    } catch (err: any) { alert(err.message) }
    setSaving(false)
  }

  return (
    <div>
      <h3>📅 Clinic Booking Portal</h3>

      <div className="space-y-4" style={{ marginTop: '12px' }}>
        {/* Step 1: Psychologist */}
        <div>
          <label>Psychologist</label>
          <select value={selectedPsych} onChange={e => setSelectedPsych(e.target.value)}>
            <option value="">Select psychologist...</option>
            {psychs.map((p: any) => (
              <option key={p.username || p} value={p.username || p}>{p.name || p}</option>
            ))}
          </select>
        </div>

        {/* Step 2: Available dates */}
        <div>
          <label>Available dates</label>
          {availableDates.length > 0 ? (
            <select value={selectedDate} onChange={e => setSelectedDate(e.target.value)}>
              <option value="">Select a date...</option>
              {availableDates.map((d: string) => (
                <option key={d} value={d}>{new Date(d).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })}</option>
              ))}
            </select>
          ) : (
            <div style={{ color: '#6E837A', fontSize: '0.8125rem', padding: '8px 0' }}>No available dates. Your psychologist hasn't opened slots yet.</div>
          )}
        </div>

        {/* Step 3: Attendance */}
        <div>
          <label>How many members are attending?</label>
          <input type="number" min={1} max={6} value={memberCount} onChange={e => setMemberCount(Number(e.target.value))} style={{ width: '100px' }} />
        </div>

        {/* Step 4: Session Details */}
        <div>
          <div style={{ fontSize: '0.8125rem', color: '#50695F', fontWeight: 500, marginBottom: '8px' }}>Session Details</div>
          <div style={{ display: 'flex', gap: '12px' }}>
            <div style={{ flex: 1 }}>
              <label>Time</label>
              <input type="time" value={time} onChange={e => setTime(e.target.value)} />
            </div>
            <div style={{ flex: 1 }}>
              <label>Type</label>
              <select value={sessionType} onChange={e => setSessionType(e.target.value)}>
                <option>Therapy</option>
                <option>Follow-up</option>
                <option>Crisis Check-in</option>
                <option>Mindfulness</option>
              </select>
            </div>
          </div>
        </div>

        <hr />

        {/* Step 5: Member Details */}
        <div>
          <div style={{ fontSize: '0.8125rem', color: '#50695F', fontWeight: 500, marginBottom: '8px' }}>Member Details</div>
          {members.map((m, i) => (
            <div key={i} style={{ display: 'flex', gap: '12px', marginBottom: '8px' }}>
              <div style={{ flex: 3 }}>
                <label>Member {i + 1} Full Name</label>
                <input value={m.name} onChange={e => {
                  const next = [...members]; next[i] = { ...next[i], name: e.target.value }; setMembers(next)
                }} placeholder="Full name" />
              </div>
              <div style={{ flex: 1 }}>
                <label>Age</label>
                <input type="number" min={0} max={120} value={m.age} onChange={e => {
                  const next = [...members]; next[i] = { ...next[i], age: Number(e.target.value) }; setMembers(next)
                }} />
              </div>
            </div>
          ))}
        </div>

        <hr />

        <div>
          <label>Preferred Contact (Phone/Email)</label>
          <input value={contact} onChange={e => setContact(e.target.value)} placeholder="Phone or email" />
        </div>
        <div>
          <label>Context for the session</label>
          <textarea value={context} onChange={e => setContext(e.target.value)} placeholder="Briefly describe the goal for this visit." rows={3} />
        </div>

        <button className="btn-primary" onClick={handleSubmit} disabled={saving} style={{ width: '100%', padding: '10px' }}>
          {saving ? 'Submitting...' : 'Submit Request'}
        </button>
      </div>
    </div>
  )
}

/* ──── Psychologist Booking ──── */

function PsychBookings() {
  const [tab, setTab] = useState(0)

  return (
    <div className="animate-fade-in">
      <h2>📅 Bookings</h2>
      <div style={{ display: 'grid', gridTemplateColumns: '3fr 1fr', gap: '24px' }}>
        <div>
          <div className="sub-tabs">
            <button className={`sub-tab ${tab === 0 ? 'active' : ''}`} onClick={() => setTab(0)}>📅 Calendar</button>
            <button className={`sub-tab ${tab === 1 ? 'active' : ''}`} onClick={() => setTab(1)}>📋 Queue</button>
          </div>
          {tab === 0 && <PsychCalendar />}
          {tab === 1 && <PsychQueue />}
        </div>
        <div>
          <PsychBookingAgent />
        </div>
      </div>
    </div>
  )
}

function PsychCalendar() {
  const today = new Date()
  const [year, setYear] = useState(today.getFullYear())
  const [month, setMonth] = useState(today.getMonth() + 1)
  const [avail, setAvail] = useState<string[]>([])

  useEffect(() => {
    api.get('/bookings/availability/me').then(d => setAvail(d || [])).catch(() => {})
  }, [])

  const daysInMonth = new Date(year, month, 0).getDate()
  const firstDay = new Date(year, month - 1, 1).getDay()
  const weekday = firstDay === 0 ? 6 : firstDay - 1

  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

  async function toggleDate(d: number) {
    const ds = `${year}-${String(month).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    try {
      if (avail.includes(ds)) {
        await api.delete(`/bookings/availability/date/${ds}`)
        setAvail(avail.filter(a => a !== ds))
      } else {
        await api.post('/bookings/availability', { date: ds })
        setAvail([...avail, ds])
      }
    } catch {}
  }

  return (
    <div>
      <h3>📅 Availability Calendar</h3>
      <div style={{ display: 'flex', gap: '12px', marginBottom: '12px' }}>
        <select value={month} onChange={e => setMonth(Number(e.target.value))} style={{ width: '140px' }}>
          {months.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
        </select>
        <select value={year} onChange={e => setYear(Number(e.target.value))} style={{ width: '100px' }}>
          {[today.getFullYear() - 1, today.getFullYear(), today.getFullYear() + 1, today.getFullYear() + 2].map(y => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
      </div>

      <div className="cal-wrap">
        {['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].map(d => (
          <div key={d} className="cal-hdr">{d}</div>
        ))}
        {Array.from({ length: weekday }).map((_, i) => <div key={`e${i}`}></div>)}
        {Array.from({ length: daysInMonth }, (_, i) => i + 1).map(d => {
          const ds = `${year}-${String(month).padStart(2, '0')}-${String(d).padStart(2, '0')}`
          const isAvail = avail.includes(ds)
          const isPast = new Date(year, month - 1, d) < new Date(today.getFullYear(), today.getMonth(), today.getDate())
          const isToday = year === today.getFullYear() && month === today.getMonth() + 1 && d === today.getDate()
          let cls = 'cal-cell'
          if (isPast) cls += ' cal-past'
          else if (isAvail) cls += ' cal-avail'
          else if (isToday) cls += ' cal-today'
          else cls += ' cal-day'
          return <div key={d} className={cls} style={{ cursor: isPast ? 'default' : 'pointer' }} onClick={() => !isPast && toggleDate(d)}>{d}</div>
        })}
      </div>

      <div style={{ display: 'flex', gap: '16px', fontSize: '0.75rem', marginTop: '8px' }}>
        <span><span style={{ display: 'inline-block', width: '12px', height: '12px', background: '#E2F5EA', border: '1px solid #2E8B57', borderRadius: '3px', verticalAlign: 'middle', marginRight: '4px' }}></span> Available ({avail.length})</span>
        <span style={{ color: '#A8B9B1' }}>Click a date to toggle available/blocked</span>
      </div>
    </div>
  )
}

function PsychQueue() {
  const [bookings, setBookings] = useState<any[]>([])
  const [expanded, setExpanded] = useState<Record<number, boolean>>({})

  useEffect(() => { api.getBookings().then(d => setBookings(d || [])).catch(() => {}) }, [])

  async function updateStatus(id: number, status: string) {
    try {
      await api.updateBookingStatus(id, status)
      const updated = await api.getBookings()
      setBookings(updated || [])
    } catch {}
  }

  if (bookings.length === 0) return <div className="card"><span style={{ color: '#6E837A' }}>The queue is currently empty.</span></div>

  return (
    <div>
      <h3>📋 Booking Management</h3>
      <div className="space-y-2">
        {bookings.map((item: any, idx: number) => {
          const s = item.status
          const icon = STATUS_ICONS[s] || '○'
          const open = expanded[idx]
          return (
            <div key={item.id} className="expander">
              <div className="expander-header" onClick={() => setExpanded({ ...expanded, [idx]: !open })}>
                <span>{icon} {item.patient_username} - {item.date} @ {item.time}</span>
                <span>{open ? '▲' : '▼'}</span>
              </div>
              {open && (
                <div className="expander-body">
                  <div className="space-y-2" style={{ fontSize: '0.8125rem' }}>
                    <div><strong>Status:</strong> <span style={{ color: STATUS_COLORS[s] || '#6E837A' }}>{s}</span></div>
                    <div><strong>Patient:</strong> {item.patient_username}</div>
                    <div><strong>Date:</strong> {item.date}</div>
                    <div><strong>Time:</strong> {item.time}</div>
                    <div><strong>Session:</strong> {item.session_type || 'Therapy'}</div>
                    <div><strong>Members:</strong> {item.members || 'N/A'}</div>
                    <div><strong>Contact:</strong> {item.contact || 'N/A'}</div>
                    <div className="card" style={{ padding: '10px' }}><strong>Reason:</strong> {item.explanation || 'N/A'}</div>

                    {s === 'Cancelled' && (
                      <div className="card" style={{ background: '#2a0a0a', borderColor: '#C7463B' }}>
                        <span style={{ color: '#C7463B' }}>❌ Patient cancelled this slot.</span>
                      </div>
                    )}
                    {s === 'Pending' && (
                      <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                        <button className="btn-primary" onClick={() => updateStatus(item.id, 'Approved')}>✅ Approve</button>
                        <button onClick={() => updateStatus(item.id, 'Rejected')}>❌ Reject</button>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function PsychBookingAgent() {
  const [patients, setPatients] = useState<any[]>([])
  const [selected, setSelected] = useState('')
  const [agentResult, setAgentResult] = useState<any>(null)

  useEffect(() => { api.getPsychPatients().then(d => setPatients(d || [])).catch(() => {}) }, [])

  async function analyze() {
    if (!selected) return
    try {
      const result = await api.suggestSlots(selected)
      setAgentResult(result)
    } catch {}
  }

  async function proposeSlot(slot: any) {
    try {
      await api.createBooking({
        psychologist_username: getUser()?.username,
        date: slot.date,
        time: slot.time || '10:00',
        session_type: 'Therapy',
        members: '1',
        contact: '',
        explanation: 'AI-suggested booking',
      })
      alert('Booking proposed - waiting for patient to confirm.')
      setAgentResult(null)
    } catch (err: any) { alert(err.message) }
  }

  return (
    <div className="psych-box">
      <div className="psych-box-title">🤖 Booking Agent</div>
      <div className="psych-box-desc">AI-powered slot suggestions</div>
      <PatientSelector patients={patients} value={selected} onChange={setSelected} placeholder="Select patient..." style={{ marginBottom: '8px' }} />
      <button onClick={analyze} className="btn-primary" style={{ width: '100%', fontSize: '0.8125rem' }}>🤖 Analyze & Suggest Slots</button>

      {agentResult && (
        <div className="ai-box" style={{ marginTop: '8px' }}>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', fontSize: '0.75rem', marginBottom: '6px' }}>
            <span style={{ color: '#7E948C' }}>Priority: <strong>{agentResult.priority}</strong></span>
            <span style={{ color: '#A8B9B1' }}>|</span>
            <span style={{ color: '#7E948C' }}>Urgency: <strong>{agentResult.urgency_score}/10</strong></span>
          </div>
          <div style={{ color: '#6E837A', fontSize: '0.6875rem', marginBottom: '8px' }}>{agentResult.reasoning}</div>
          {agentResult.suggested_slots?.map((s: any, i: number) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', borderTop: '1px solid #D9E7E3' }}>
              <span style={{ color: '#17796E', fontSize: '0.8125rem', fontWeight: 600 }}>{s.label}</span>
              <button className="btn-primary" style={{ fontSize: '0.6875rem', padding: '4px 10px' }} onClick={() => proposeSlot(s)}>Propose</button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
