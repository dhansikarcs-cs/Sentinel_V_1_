import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom'
import { getUser, logout, subscribe } from '../stores/auth'
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { computeCrisisStage, CRISIS_STAGE_MESSAGES, todayStr } from '../constants'
import TourGuide from './TourGuide'

const QUOTES = [
  "The wound is the place where the Light enters you. — Rumi",
  "Out of suffering have emerged the strongest souls. — Kahlil Gibran",
  "Healing takes time, and asking for help is a courageous step.",
  "Rest is not idleness. It is preparation for meaningful work.",
  "The greatest glory in living lies not in never falling, but in rising every time we fall. — Mandela",
  "What mental health needs is more sunlight, more candor, more unashamed conversation. — Glenn Close",
  "You are not your illness. You have an individual story to tell. — Viktor Frankl",
  "There is hope, even when your brain tells you there isn't. — John Green",
  "Self-care is not selfish. You cannot serve from an empty vessel.",
  "The only journey is the journey within. — Rainer Maria Rilke",
]

interface Tab { to: string; label: string }
const patientTabs: Tab[] = [
  { to: '/dashboard', label: '📊 Wellness' },
  { to: '/journal', label: '📝 Journal' },
  { to: '/bookings', label: '📅 Booking' },
  { to: '/followups', label: '📋 Follow-Up' },
  { to: '/timeline', label: '🔍 Timeline' },
  { to: '/crisis', label: '🚨 Emergency' },
]
const psychTabs: Tab[] = [
  { to: '/open-session', label: '🧑‍⚕️ Open Session' },
  { to: '/triage', label: '📋 Patient Triage' },
  { to: '/clinical-notes', label: '📝 Clinical Notes' },
  { to: '/patient-insights', label: '📊 Patient Insights' },
  { to: '/psych-journal', label: '📓 Journal & Wellness' },
  { to: '/bookings', label: '📅 Bookings' },
  { to: '/followups', label: '📋 Follow-Up' },
  { to: '/export', label: '📦 Export Center' },
]
export default function Layout() {
  const navigate = useNavigate()
  const location = useLocation()
  const [user, setUser] = useState(getUser())
  const [crisisState, setCrisisState] = useState<any>(null)
  const [crisisLog, setCrisisLog] = useState<any[]>([])
  const [quoteIdx] = useState(() => Math.floor(Math.random() * QUOTES.length))
  const [crisisElapsed, setCrisisElapsed] = useState(0)

  const [patients, setPatients] = useState<any[]>([])
  const [bookings, setBookings] = useState<any[]>([])
  const [journals, setJournals] = useState<any[]>([])
  const [moods, setMoods] = useState<any[]>([])
  const [sensorData, setSensorData] = useState<any>(null)
  const [notifications, setNotifications] = useState<any[]>([])
  const unreadCount = notifications.filter((n: any) => !n.read).length
  const [triagePriorities, setTriagePriorities] = useState<any[]>([])
  const [aiInsights, setAiInsights] = useState<Record<string, any>>({})
  const [aiStatus, setAiStatus] = useState<any>(null)

  useEffect(() => {
    const unsub = subscribe(() => setUser(getUser()))
    return unsub
  }, [])

  useEffect(() => {
    api.getCrisisState().then(setCrisisState).catch(() => {})
    api.get('/crisis/log').then((d: any) => setCrisisLog(Array.isArray(d) ? d : [])).catch(() => setCrisisLog([]))
    api.get('/ai/health').then(setAiStatus).catch(() => setAiStatus(null))
  }, [])

  useEffect(() => {
    const interval = setInterval(() => {
      api.getCrisisState().then((state) => {
        setCrisisState(state)
        if (state?.active) {
          api.getCrisisElapsed().then((e: any) => setCrisisElapsed(e?.elapsed || 0)).catch(() => {})
        }
      }).catch(() => {})
      api.get('/crisis/log').then((d: any) => setCrisisLog(Array.isArray(d) ? d : [])).catch(() => {})
      api.getNotifications().then((d: any) => setNotifications(Array.isArray(d) ? d : [])).catch(() => {})
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  const role = user?.role === 'psychologist' ? 'Psychologist' : 'Patient'

  useEffect(() => {
    if (role === 'Psychologist') {
      api.getPsychPatients().then(async (d: any) => {
        const pts = Array.isArray(d) ? d : []
        setPatients(pts)
        if (pts.length > 0) {
          const results = await Promise.allSettled(
            pts.map((p: any) => api.triageSummary(p.username || p).catch(() => null))
          )
          const computed = pts.map((p: any, i: any) => {
            const result = results[i]?.status === 'fulfilled' ? results[i].value : null
            const tier: string = result?.tier || 'stable'
            const crisis: boolean = result?.crisis ?? false
            const score: number = result?.priority_score ?? 0
            return { patient: p.username || p, name: p.name || p, score, tier, crisis, ...(result || {}) }
          })
          computed.sort((a: any, b: any) => b.score - a.score)
          setTriagePriorities(computed)
          const insights: Record<string, any> = {}
          await Promise.allSettled(
            pts.map(async (p: any) => {
              try {
                const res = await api.get(`/journal/${p.username || p}/summaries`)
                if (res && (res as any).summary) insights[p.username || p] = res
              } catch {}
            })
          )
          setAiInsights(insights)
        }
      }).catch(() => {})
    } else {
      api.getWellness().then((d: any) => {}).catch(() => {})
      api.getSensorData().then(d => setSensorData(d)).catch(() => {})
      api.getNotifications().then((d: any) => setNotifications(Array.isArray(d) ? d : [])).catch(() => {})
    }
    api.getBookings().then((d: any) => setBookings(Array.isArray(d) ? d : [])).catch(() => {})
  }, [role])

  useEffect(() => {
    if (role === 'Patient') {
      api.getJournals().then((d: any) => setJournals(Array.isArray(d) ? d : [])).catch(() => {})
      api.getMoods().then((d: any) => setMoods(Array.isArray(d) ? d : [])).catch(() => {})
    }
  }, [role])

  const tabs = role === 'Psychologist' ? psychTabs : patientTabs
  const activeTab = tabs.find(t => location.pathname === t.to) || tabs[0]

  const heartRate = sensorData?.bpm || sensorData?.heart_rate || '-'
  const journalOk = journals.some((j: any) => {
    const d = (j.created_at || j.timestamp || '').slice(0, 10)
    return d === todayStr()
  }) ? 'Logged' : 'Not yet'
  const nextSession = (() => {
    const approved = bookings.filter((b: any) => b.status === 'Approved').sort((a: any, b: any) => (a.date || '').localeCompare(b.date || ''))
    if (approved.length === 0) return '-'
    return `${approved[0].date || ''} @ ${approved[0].time || ''}`
  })()
  const todayMood = (() => {
    const m = moods.find((m: any) => (m.date || '').slice(0, 10) === todayStr())
    return m ? m.emoji || m.label || 'Logged' : '-'
  })()

  const patientCount = patients.length
  const pendingBookings = bookings.filter((b: any) => b.status === 'Pending').length
  const silentPatients = patients.filter((p: any) => {
    const lastActive = p.last_active ? new Date(p.last_active) : null
    if (!lastActive) return true
    const diff = (Date.now() - lastActive.getTime()) / (1000 * 60 * 60)
    return diff > 48
  }).length

  const isPsychRole = role === 'Psychologist'

  async function triggerSelfCrisis() {
    try { await api.triggerCrisis() } catch {}
  }

  const showCrisisBanner = crisisState?.active
  const cs = crisisState || {}
  const crisisStage = computeCrisisStage(cs, crisisElapsed)

  const lastBooking = bookings.length > 0 ? bookings[bookings.length - 1] : null
  const bookingMsg = lastBooking ? ({
    Approved: { text: '✅ Booking Accepted! Your session has been confirmed.', color: '#22c55e' },
    Rejected: { text: '❌ Booking Declined.', color: '#ef4444' },
    Cancelled: { text: '🔴 Booking Cancelled.', color: '#6a6474' },
  } as Record<string, { text: string; color: string } | undefined>)[lastBooking.status] : null

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <aside style={{
        width: '220px', minWidth: '220px',
        background: '#151824', borderRight: '1px solid #2d2d44',
        padding: '20px 14px', display: 'flex', flexDirection: 'column', gap: '2px', overflow: 'auto',
      }}>
        <Link to={role === 'Psychologist' ? '/triage' : '/dashboard'} style={{ textDecoration: 'none' }}>
          <div style={{ fontSize: '1.15rem', fontWeight: 700, color: '#c49ea4', marginBottom: '16px', padding: '0 4px' }}>
            Sentinel
          </div>
        </Link>

        <div style={{ fontSize: '0.75rem', color: '#6a6474', padding: '0 4px', marginBottom: '4px' }}>
          {role === 'Psychologist' ? '🧑‍⚕️' : '👤'} {user?.name} <span style={{ color: '#9a92a2' }}>({role})</span>
        </div>

        <div style={{ fontSize: '0.75rem', color: '#6a6474', fontStyle: 'italic', padding: '6px 0 6px 12px', borderLeft: '2px solid #c49ea4', lineHeight: '1.5', margin: '8px 0' }}>
          "{QUOTES[quoteIdx]}"
        </div>

        <hr style={{ margin: '8px 0', borderColor: '#2d2d44', opacity: 0.4 }} />

        <div style={{ fontSize: '0.6875rem', color: '#9a92a2', fontWeight: 600, marginBottom: '4px', padding: '0 4px' }}>
          📊 System Status
        </div>
        <div style={{ fontSize: '0.75rem', padding: '0 4px', marginBottom: '4px' }}>
          <span style={{ color: crisisState?.active ? '#ef4444' : '#22c55e' }}>
            {crisisState?.active ? '🔴 Crisis Active' : '🟢 Online'}
          </span>
        </div>
        <div style={{ fontSize: '0.6875rem', padding: '0 4px', color: aiStatus?.any_available ? '#22c55e' : '#ef4444' }}>
          🤖 AI: {aiStatus?.any_available ? 'Connected' : 'Unavailable'}
        </div>

        {isPsychRole ? (
          <>
            <hr style={{ margin: '8px 0', borderColor: '#2d2d44', opacity: 0.4 }} />
            <div style={{ fontSize: '0.6875rem', color: '#9a92a2', fontWeight: 600, marginBottom: '4px', padding: '0 4px' }}>
              📊 Daily Ops
            </div>
            <div style={{ padding: '0 4px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.6rem', color: '#6a6474', marginBottom: '3px' }}>
                <span>Workload</span>
                <span>{pendingBookings + silentPatients} tasks</span>
              </div>
              <div style={{ height: '5px', background: '#1e2940', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{
                  height: '100%', borderRadius: '3px',
                  width: `${Math.min(((pendingBookings + silentPatients) / Math.max(patientCount, 1)) * 100, 100)}%`,
                  background: pendingBookings + silentPatients > patientCount * 0.5 ? '#ef4444' : pendingBookings + silentPatients > 0 ? '#f59e0b' : '#22c55e',
                  transition: 'width 0.3s',
                }} />
              </div>
              <div style={{ fontSize: '0.6rem', color: '#6a6474', marginTop: '3px', display: 'flex', justifyContent: 'space-between' }}>
                <span>{pendingBookings} pending</span>
                <span>{silentPatients} silent</span>
              </div>
            </div>

            <hr style={{ margin: '8px 0', borderColor: '#2d2d44', opacity: 0.4 }} />
            <div style={{ fontSize: '0.6875rem', color: '#9a92a2', fontWeight: 600, marginBottom: '4px', padding: '0 4px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span>⚠️ High Risk</span>
              <span style={{ background: '#ef444422', color: '#fca5a5', fontSize: '0.55rem', padding: '1px 5px', borderRadius: '3px' }}>
                {triagePriorities.filter((p: any) => p.tier === 'crisis' || p.tier === 'high').length}
              </span>
            </div>
            <div style={{ fontSize: '0.6875rem', padding: '0 4px', maxHeight: '110px', overflow: 'auto' }}>
              {triagePriorities.filter((p: any) => p.tier === 'crisis' || p.tier === 'high').length === 0 && silentPatients === 0 && !crisisState?.active ? (
                <div style={{ color: '#22c55e', padding: '2px 0' }}>✅ All patients stable</div>
              ) : (
                <>
                  {crisisState?.active && (
                    <div style={{ color: '#ef4444', padding: '3px 0', borderBottom: '1px solid #2d2d44', fontWeight: 600 }}>
                      🚨 {crisisState.patient || 'unknown'}
                    </div>
                  )}
                  {triagePriorities.filter((p: any) => p.tier === 'high').slice(0, 5).map((p: any) => (
                    <div key={p.patient} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #2d2d44', color: '#f59e0b', fontSize: '0.65rem' }}>
                      <span>{p.name}</span>
                      <span style={{ color: '#6a6474', fontSize: '0.6rem' }}>score {p.score}</span>
                    </div>
                  ))}
                  {silentPatients > 0 && (
                    <div style={{ color: '#f59e0b', padding: '3px 0', fontSize: '0.65rem' }}>
                      ⏳ {silentPatients} silent &gt;48h
                    </div>
                  )}
                </>
              )}
            </div>

            <hr style={{ margin: '8px 0', borderColor: '#2d2d44', opacity: 0.4 }} />
            <div style={{ fontSize: '0.6875rem', color: '#9a92a2', fontWeight: 600, marginBottom: '4px', padding: '0 4px' }}>
              🤖 AI Insights
            </div>
            <div style={{ fontSize: '0.6875rem', padding: '0 4px', maxHeight: '100px', overflow: 'auto' }}>
              {Object.keys(aiInsights).length === 0 ? (
                <div style={{ color: '#5a4a5a' }}>Loading...</div>
              ) : (
                Object.entries(aiInsights).slice(0, 4).map(([patient, insight]: [string, any]) => (
                  <div key={patient} style={{ padding: '3px 0', borderBottom: '1px solid #2d2d44' }}>
                    <div style={{ color: '#c49ea4', fontWeight: 600, fontSize: '0.625rem' }}>{patient}</div>
                    <div style={{ color: '#7a8aaa', fontSize: '0.6rem', lineHeight: 1.4 }}>
                      {(insight.summary || '').slice(0, 80)}{(insight.summary || '').length > 80 ? '...' : ''}
                    </div>
                  </div>
                ))
              )}
            </div>
          </>
        ) : (
          <>
            <hr style={{ margin: '8px 0', borderColor: '#2d2d44', opacity: 0.4 }} />
            <div style={{ fontSize: '0.6875rem', color: '#9a92a2', fontWeight: 600, marginBottom: '4px', padding: '0 4px' }}>
              🆘 Emergency
            </div>
            <button
              onClick={triggerSelfCrisis}
              style={{ width: '100%', padding: '6px 8px', fontSize: '0.7rem', background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: '6px', color: '#fca5a5', cursor: 'pointer', marginBottom: '4px' }}
            >
              🔥 Trigger SOS
            </button>
            {crisisState?.active && (
              <div style={{ fontSize: '0.65rem', color: '#ef4444', padding: '4px' }}>
                🚨 Crisis active
              </div>
            )}

            <hr style={{ margin: '8px 0', borderColor: '#2d2d44', opacity: 0.4 }} />
            <div style={{ fontSize: '0.6875rem', color: '#9a92a2', fontWeight: 600, marginBottom: '4px', padding: '0 4px' }}>
              📡 Recent Activity
            </div>
            <div style={{ flex: 1, overflow: 'auto', fontSize: '0.6875rem', padding: '0 4px' }}>
              {journals.length === 0 ? (
                <div style={{ color: '#5a4a5a' }}>No entries yet.</div>
              ) : (
                journals.slice(0, 6).map((j: any, i: number) => (
                  <div key={i} style={{ display: 'flex', gap: '6px', padding: '3px 0', borderBottom: '1px solid #2d2d44', alignItems: 'center' }}>
                    <span style={{ color: '#6a6474', fontSize: '0.625rem' }}>📝</span>
                    <span style={{ color: '#6a6474', fontSize: '0.625rem' }}>{(j.timestamp || '').slice(0, 10)}</span>
                    <span style={{ color: '#9a92a2', fontSize: '0.625rem' }}>{(j.emotions || '').slice(0, 20) || 'journal entry'}</span>
                  </div>
                ))
              )}
            </div>
          </>
        )}

        <hr style={{ margin: '8px 0', borderColor: '#2d2d44', opacity: 0.4 }} />

        <div style={{ fontSize: '0.6875rem', color: '#9a92a2', fontWeight: 600, marginBottom: '4px', padding: '0 4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          🔔 Notifications
          {unreadCount > 0 && (
            <span style={{ background: '#ef4444', color: 'white', fontSize: '0.55rem', borderRadius: '50%', width: '16px', height: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700 }}>
              {unreadCount}
            </span>
          )}
        </div>
        <div style={{ flex: 1, overflow: 'auto', fontSize: '0.6875rem', padding: '0 4px', maxHeight: '100px' }}>
          {notifications.filter((n: any) => !n.read).length === 0 ? (
            <div style={{ color: '#5a4a5a' }}>All caught up.</div>
          ) : (
            notifications.filter((n: any) => !n.read).slice(0, 4).map((n: any) => (
              <div key={n.id} style={{ padding: '3px 0', borderBottom: '1px solid #2d2d44', cursor: 'pointer' }}
                onClick={() => { api.markNotificationRead(n.id).then(() => setNotifications(prev => prev.map((p: any) => p.id === n.id ? { ...p, read: true } : p))).catch(() => {}) }}>
                <span style={{ color: n.notification_type === 'crisis' ? '#ef4444' : '#c49ea4', fontWeight: 600 }}>{n.title}</span>
                <div style={{ color: '#6a6474', fontSize: '0.6rem' }}>{n.message?.slice(0, 60)}{n.message?.length > 60 ? '...' : ''}</div>
              </div>
            ))
          )}
        </div>

        {isPsychRole && crisisLog.length > 0 && (
          <>
            <hr style={{ margin: '8px 0', borderColor: '#2d2d44', opacity: 0.4 }} />
            <div style={{ fontSize: '0.6875rem', color: '#9a92a2', fontWeight: 600, marginBottom: '4px', padding: '0 4px' }}>
              🚨 Crisis History
            </div>
            {crisisLog.slice(-3).reverse().map((e: any, i: number) => (
              <div key={i} style={{ fontSize: '0.6875rem', padding: '3px 0', color: '#c0d0e0', lineHeight: '1.5' }}>
                <strong>{e.event}</strong> <span style={{ color: '#5a4a5a', fontSize: '0.625rem' }}>{(e.timestamp || '').slice(0, 19).replace('T', ' ')}</span>
              </div>
            ))}
          </>
        )}

        <div style={{ marginTop: 'auto', paddingTop: '12px', borderTop: '1px solid #2d2d44' }}>
          <button
            onClick={() => { logout(); navigate('/login') }}
            style={{
              width: '100%', padding: '8px 12px', fontSize: '0.75rem',
              background: '#1e2336', border: '1px solid #2d2d44', borderRadius: '8px',
              color: '#9a92a2', cursor: 'pointer', transition: 'all 0.2s',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = '#c49ea4'; e.currentTarget.style.color = '#151824' }}
            onMouseLeave={e => { e.currentTarget.style.background = '#1e2336'; e.currentTarget.style.color = '#9a92a2' }}
          >
            Logout
          </button>
        </div>
      </aside>

      <main style={{ flex: 1, padding: '28px 36px', overflow: 'auto' }}>
        <div style={{ maxWidth: '1100px' }}>
          {showCrisisBanner && (
            <div className="card" style={{ borderColor: '#ef4444', background: 'rgba(239,68,68,0.08)', marginBottom: '16px', padding: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '4px' }}>
                <span style={{ color: '#ef4444', fontSize: '1.25rem' }}>⏱️ {crisisElapsed >= 60 ? '60+' : crisisElapsed}s</span>
                <span style={{ color: CRISIS_STAGE_MESSAGES[crisisStage]?.color || '#ef4444', fontWeight: 600, fontSize: '0.875rem' }}>
                  {CRISIS_STAGE_MESSAGES[crisisStage]?.text || '🔴 Crisis Active'}
                </span>
              </div>
              <div style={{ display: 'flex', gap: '4px', marginTop: '8px' }}>
                {[
                  { key: 'triggered', label: '🚨 Triggered', sec: 0 },
                  { key: 'trustee_notified', label: '👤 Trusted Contact', sec: 30 },
                  { key: 'helpline_escalated', label: '🏥 Helpline', sec: 60 },
                ].map(s => {
                  const isActive = s.key === crisisStage || (crisisElapsed >= s.sec && crisisElapsed < (s.sec === 0 ? 30 : 999))
                  const passed = crisisElapsed >= s.sec
                  return (
                    <div key={s.key} style={{
                      flex: 1, textAlign: 'center', padding: '6px', borderRadius: '6px',
                      background: isActive ? 'rgba(239,68,68,0.15)' : passed ? 'rgba(34,197,94,0.12)' : 'rgba(26,34,56,0.6)',
                      border: `1px solid ${isActive ? 'rgba(239,68,68,0.4)' : passed ? 'rgba(34,197,94,0.3)' : '#1e2940'}`,
                      color: isActive ? '#ef4444' : passed ? '#22c55e' : '#3a4a5a',
                      fontSize: '0.75rem', fontWeight: 600,
                    }}>
                      {s.label}<br /><span style={{ fontSize: '0.625rem', fontWeight: 400 }}>{s.sec}s</span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {bookingMsg && (
            <div className="card" style={{ borderColor: '#f59e0b', marginBottom: '12px', padding: '10px 14px' }}>
              <span style={{ color: bookingMsg.color, fontSize: '0.8125rem' }}>{bookingMsg.text}</span>
            </div>
          )}

          <div style={{ marginBottom: '16px' }}>
            <h2 style={{ margin: 0 }}>🌿 Welcome, {user?.name}</h2>
            {role === 'Patient' && user?.assigned_psych && (
              <div style={{ color: '#c0d0e0', fontSize: '0.8125rem', marginTop: '4px' }}>
                💉 Your psychologist: <strong style={{ color: '#c49ea4' }}>{user.assigned_psych}</strong>
              </div>
            )}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', marginBottom: '16px' }}>
            {role === 'Psychologist' ? (
              <>
                <StatusCard label="Patients" value={patientCount} unit="under care" color="#c49ea4" />
                <StatusCard label="Pending" value={pendingBookings} unit="booking approvals" color={pendingBookings > 0 ? '#f59e0b' : '#c49ea4'} />
                <StatusCard label="Silent" value={silentPatients} unit="patients >48h" color={silentPatients > 0 ? '#ef4444' : '#22c55e'} />
                <StatusCard label="Crisis" value={crisisState?.active ? 'ACTIVE' : 'None'} unit="current" color={crisisState?.active ? '#ef4444' : '#6a6474'} />
              </>
            ) : (
              <>
                <StatusCard label="Heart" value={heartRate} unit="bpm" color="#ff6b6b" />
                <StatusCard label="Journal" value={journalOk} unit="today" color={journalOk === 'Logged' ? '#22c55e' : '#6a6474'} />
                <StatusCard label="Next Session" value={nextSession} unit="" color={nextSession !== '-' ? '#22c55e' : '#6a6474'} />
                <StatusCard label="Mood" value={todayMood} unit="today" color={todayMood !== '-' ? '#22c55e' : '#6a6474'} />
              </>
            )}
          </div>

          <div className="segmented-control" style={{ marginBottom: '20px' }}>
            {tabs.map(tab => (
              <button
                key={tab.to}
                className={`segmented-btn${activeTab.to === tab.to ? ' active' : ''}`}
                onClick={() => navigate(tab.to)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <Outlet />
        </div>
      </main>
      <TourGuide role={role} />
    </div>
  )
}

function StatusCard({ label, value, unit, color }: { label: string; value: string | number; unit: string; color: string }) {
  return (
    <div style={{ background: 'linear-gradient(135deg, #1e2336, #1a1e30)', border: '1px solid #2d2d44', borderRadius: '8px', padding: '8px 12px', display: 'flex', alignItems: 'center', gap: '12px' }}>
      <div>
        <div style={{ color: '#6a6474', fontSize: '0.6875rem', fontWeight: 500 }}>{label}</div>
        <div style={{ color, fontSize: '1.125rem', fontWeight: 700 }}>{value}</div>
      </div>
      {unit && <div style={{ color: '#5a4a5a', fontSize: '0.625rem' }}>{unit}</div>}
    </div>
  )
}
