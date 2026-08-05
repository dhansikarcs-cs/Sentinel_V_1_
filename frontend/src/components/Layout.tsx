import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom'
import { getUser, logout, subscribe } from '../stores/auth'
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { computeCrisisStage, CRISIS_STAGE_MESSAGES, todayStr } from '../constants'
import TourGuide from './TourGuide'
import { useTheme } from '../hooks/useTheme'

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
  const [theme, setTheme] = useTheme()

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
    Approved: { text: '✅ Booking Accepted! Your session has been confirmed.', color: 'var(--ok)' },
    Rejected: { text: '❌ Booking Declined.', color: 'var(--danger)' },
    Cancelled: { text: '🔴 Booking Cancelled.', color: 'var(--muted)' },
  } as Record<string, { text: string; color: string } | undefined>)[lastBooking.status] : null

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <aside style={{
        width: '220px', minWidth: '220px',
        background: 'var(--surface-soft)', borderRight: '1px solid var(--border)',
        padding: '20px 14px', display: 'flex', flexDirection: 'column', gap: '2px', overflow: 'auto',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <Link to={role === 'Psychologist' ? '/triage' : '/dashboard'} style={{ textDecoration: 'none' }}>
            <div style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--accent)', padding: '0 4px' }}>
              Sentinel
            </div>
          </Link>
          <button
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            style={{
              background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px',
              padding: '5px 8px', fontSize: '0.9rem', cursor: 'pointer', lineHeight: 1, boxShadow: 'none',
            }}
          >
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>
        </div>

        <div style={{ fontSize: '0.75rem', color: 'var(--muted)', padding: '0 4px', marginBottom: '4px' }}>
          {role === 'Psychologist' ? '🧑‍⚕️' : '👤'} {user?.name} <span style={{ color: 'var(--secondary)' }}>({role})</span>
        </div>

        <div style={{ fontSize: '0.75rem', color: 'var(--muted)', fontStyle: 'italic', padding: '6px 0 6px 12px', borderLeft: '2px solid var(--accent)', lineHeight: '1.5', margin: '8px 0' }}>
          "{QUOTES[quoteIdx]}"
        </div>

        <hr style={{ margin: '8px 0', borderColor: 'var(--border)', opacity: 0.4 }} />

        <div style={{ fontSize: '0.6875rem', color: 'var(--secondary)', fontWeight: 600, marginBottom: '4px', padding: '0 4px' }}>
          📊 System Status
        </div>
        <div style={{ fontSize: '0.75rem', padding: '0 4px', marginBottom: '4px' }}>
          <span style={{ color: crisisState?.active ? 'var(--danger)' : 'var(--ok)' }}>
            {crisisState?.active ? '🔴 Crisis Active' : '🟢 Online'}
          </span>
        </div>
        <div style={{ fontSize: '0.6875rem', padding: '0 4px', color: aiStatus?.any_available ? 'var(--ok)' : 'var(--danger)' }}>
          🤖 AI: {aiStatus?.any_available ? 'Connected' : 'Unavailable'}
        </div>

        {isPsychRole ? (
          <>
            <hr style={{ margin: '8px 0', borderColor: 'var(--border)', opacity: 0.4 }} />
            <div style={{ fontSize: '0.6875rem', color: 'var(--secondary)', fontWeight: 600, marginBottom: '4px', padding: '0 4px' }}>
              📊 Daily Ops
            </div>
            <div style={{ padding: '0 4px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.6rem', color: 'var(--muted)', marginBottom: '3px' }}>
                <span>Workload</span>
                <span>{pendingBookings + silentPatients} tasks</span>
              </div>
              <div style={{ height: '5px', background: 'var(--border-soft)', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{
                  height: '100%', borderRadius: '3px',
                  width: `${Math.min(((pendingBookings + silentPatients) / Math.max(patientCount, 1)) * 100, 100)}%`,
                  background: pendingBookings + silentPatients > patientCount * 0.5 ? 'var(--danger)' : pendingBookings + silentPatients > 0 ? 'var(--warn)' : 'var(--ok)',
                  transition: 'width 0.3s',
                }} />
              </div>
              <div style={{ fontSize: '0.6rem', color: 'var(--muted)', marginTop: '3px', display: 'flex', justifyContent: 'space-between' }}>
                <span>{pendingBookings} pending</span>
                <span>{silentPatients} silent</span>
              </div>
            </div>

            <hr style={{ margin: '8px 0', borderColor: 'var(--border)', opacity: 0.4 }} />
            <div style={{ fontSize: '0.6875rem', color: 'var(--secondary)', fontWeight: 600, marginBottom: '4px', padding: '0 4px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span>⚠️ High Risk</span>
              <span style={{ background: 'color-mix(in srgb, var(--danger) 13%, transparent)', color: 'var(--danger-deep)', fontSize: '0.55rem', padding: '1px 5px', borderRadius: '3px' }}>
                {triagePriorities.filter((p: any) => p.tier === 'crisis' || p.tier === 'high').length}
              </span>
            </div>
            <div style={{ fontSize: '0.6875rem', padding: '0 4px', maxHeight: '110px', overflow: 'auto' }}>
              {triagePriorities.filter((p: any) => p.tier === 'crisis' || p.tier === 'high').length === 0 && silentPatients === 0 && !crisisState?.active ? (
                <div style={{ color: 'var(--ok)', padding: '2px 0' }}>✅ All patients stable</div>
              ) : (
                <>
                  {crisisState?.active && (
                    <div style={{ color: 'var(--danger)', padding: '3px 0', borderBottom: '1px solid var(--border)', fontWeight: 600 }}>
                      🚨 {crisisState.patient || 'unknown'}
                    </div>
                  )}
                  {triagePriorities.filter((p: any) => p.tier === 'high').slice(0, 5).map((p: any) => (
                    <div key={p.patient} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid var(--border)', color: 'var(--warn)', fontSize: '0.65rem' }}>
                      <span>{p.name}</span>
                      <span style={{ color: 'var(--muted)', fontSize: '0.6rem' }}>score {p.score}</span>
                    </div>
                  ))}
                  {silentPatients > 0 && (
                    <div style={{ color: 'var(--warn)', padding: '3px 0', fontSize: '0.65rem' }}>
                      ⏳ {silentPatients} silent &gt;48h
                    </div>
                  )}
                </>
              )}
            </div>

            <hr style={{ margin: '8px 0', borderColor: 'var(--border)', opacity: 0.4 }} />
            <div style={{ fontSize: '0.6875rem', color: 'var(--secondary)', fontWeight: 600, marginBottom: '4px', padding: '0 4px' }}>
              🤖 AI Insights
            </div>
            <div style={{ fontSize: '0.6875rem', padding: '0 4px', maxHeight: '100px', overflow: 'auto' }}>
              {Object.keys(aiInsights).length === 0 ? (
                <div style={{ color: 'var(--faint)' }}>Loading...</div>
              ) : (
                Object.entries(aiInsights).slice(0, 4).map(([patient, insight]: [string, any]) => (
                  <div key={patient} style={{ padding: '3px 0', borderBottom: '1px solid var(--border)' }}>
                    <div style={{ color: 'var(--accent)', fontWeight: 600, fontSize: '0.625rem' }}>{patient}</div>
                    <div style={{ color: 'var(--soft)', fontSize: '0.6rem', lineHeight: 1.4 }}>
                      {(insight.summary || '').slice(0, 80)}{(insight.summary || '').length > 80 ? '...' : ''}
                    </div>
                  </div>
                ))
              )}
            </div>
          </>
        ) : (
          <>
            <hr style={{ margin: '8px 0', borderColor: 'var(--border)', opacity: 0.4 }} />
            <div style={{ fontSize: '0.6875rem', color: 'var(--secondary)', fontWeight: 600, marginBottom: '4px', padding: '0 4px' }}>
              🆘 Emergency
            </div>
            <button
              onClick={triggerSelfCrisis}
              style={{ width: '100%', padding: '6px 8px', fontSize: '0.7rem', background: 'var(--danger-alpha)', border: '1px solid rgba(199,70,59,0.3)', borderRadius: '6px', color: 'var(--danger-deep)', cursor: 'pointer', marginBottom: '4px' }}
            >
              🔥 Trigger SOS
            </button>
            {crisisState?.active && (
              <div style={{ fontSize: '0.65rem', color: 'var(--danger)', padding: '4px' }}>
                🚨 Crisis active
              </div>
            )}

            <hr style={{ margin: '8px 0', borderColor: 'var(--border)', opacity: 0.4 }} />
            <div style={{ fontSize: '0.6875rem', color: 'var(--secondary)', fontWeight: 600, marginBottom: '4px', padding: '0 4px' }}>
              📡 Recent Activity
            </div>
            <div style={{ flex: 1, overflow: 'auto', fontSize: '0.6875rem', padding: '0 4px' }}>
              {journals.length === 0 ? (
                <div style={{ color: 'var(--faint)' }}>No entries yet.</div>
              ) : (
                journals.slice(0, 6).map((j: any, i: number) => (
                  <div key={i} style={{ display: 'flex', gap: '6px', padding: '3px 0', borderBottom: '1px solid var(--border)', alignItems: 'center' }}>
                    <span style={{ color: 'var(--muted)', fontSize: '0.625rem' }}>📝</span>
                    <span style={{ color: 'var(--muted)', fontSize: '0.625rem' }}>{(j.timestamp || '').slice(0, 10)}</span>
                    <span style={{ color: 'var(--secondary)', fontSize: '0.625rem' }}>{(j.emotions || '').slice(0, 20) || 'journal entry'}</span>
                  </div>
                ))
              )}
            </div>
          </>
        )}

        <hr style={{ margin: '8px 0', borderColor: 'var(--border)', opacity: 0.4 }} />

        <div style={{ fontSize: '0.6875rem', color: 'var(--secondary)', fontWeight: 600, marginBottom: '4px', padding: '0 4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          🔔 Notifications
          {unreadCount > 0 && (
            <span style={{ background: 'var(--danger)', color: 'white', fontSize: '0.55rem', borderRadius: '50%', width: '16px', height: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700 }}>
              {unreadCount}
            </span>
          )}
        </div>
        <div style={{ flex: 1, overflow: 'auto', fontSize: '0.6875rem', padding: '0 4px', maxHeight: '100px' }}>
          {notifications.filter((n: any) => !n.read).length === 0 ? (
            <div style={{ color: 'var(--faint)' }}>All caught up.</div>
          ) : (
            notifications.filter((n: any) => !n.read).slice(0, 4).map((n: any) => (
              <div key={n.id} style={{ padding: '3px 0', borderBottom: '1px solid var(--border)', cursor: 'pointer' }}
                onClick={() => { api.markNotificationRead(n.id).then(() => setNotifications(prev => prev.map((p: any) => p.id === n.id ? { ...p, read: true } : p))).catch(() => {}) }}>
                <span style={{ color: n.notification_type === 'crisis' ? 'var(--danger)' : 'var(--accent)', fontWeight: 600 }}>{n.title}</span>
                <div style={{ color: 'var(--muted)', fontSize: '0.6rem' }}>{n.message?.slice(0, 60)}{n.message?.length > 60 ? '...' : ''}</div>
              </div>
            ))
          )}
        </div>

        {isPsychRole && crisisLog.length > 0 && (
          <>
            <hr style={{ margin: '8px 0', borderColor: 'var(--border)', opacity: 0.4 }} />
            <div style={{ fontSize: '0.6875rem', color: 'var(--secondary)', fontWeight: 600, marginBottom: '4px', padding: '0 4px' }}>
              🚨 Crisis History
            </div>
            {crisisLog.slice(-3).reverse().map((e: any, i: number) => (
              <div key={i} style={{ fontSize: '0.6875rem', padding: '3px 0', color: 'var(--soft)', lineHeight: '1.5' }}>
                <strong>{e.event}</strong> <span style={{ color: 'var(--faint)', fontSize: '0.625rem' }}>{(e.timestamp || '').slice(0, 19).replace('T', ' ')}</span>
              </div>
            ))}
          </>
        )}

        <div style={{ marginTop: 'auto', paddingTop: '12px', borderTop: '1px solid var(--border)' }}>
          <button
            onClick={() => { logout(); navigate('/login') }}
            style={{
              width: '100%', padding: '8px 12px', fontSize: '0.75rem',
              background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px',
              color: 'var(--secondary)', cursor: 'pointer', transition: 'all 0.2s',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--accent)'; e.currentTarget.style.color = 'var(--on-accent)' }}
            onMouseLeave={e => { e.currentTarget.style.background = 'var(--surface)'; e.currentTarget.style.color = 'var(--secondary)' }}
          >
            Logout
          </button>
        </div>
      </aside>

      <main style={{ flex: 1, padding: '28px 36px', overflow: 'auto' }}>
        <div style={{ maxWidth: '1100px' }}>
          {showCrisisBanner && (
            <div className="card" style={{ borderColor: 'var(--danger)', background: 'var(--danger-alpha)', marginBottom: '16px', padding: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '4px' }}>
                <span style={{ color: 'var(--danger)', fontSize: '1.25rem' }}>⏱️ {crisisElapsed >= 60 ? '60+' : crisisElapsed}s</span>
                <span style={{ color: CRISIS_STAGE_MESSAGES[crisisStage]?.color || 'var(--danger)', fontWeight: 600, fontSize: '0.875rem' }}>
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
                      background: isActive ? 'rgba(199,70,59,0.15)' : passed ? 'var(--ok-alpha)' : 'var(--surface-soft)',
                      border: `1px solid ${isActive ? 'rgba(199,70,59,0.4)' : passed ? 'rgba(46,139,87,0.3)' : 'var(--border-soft)'}`,
                      color: isActive ? 'var(--danger)' : passed ? 'var(--ok)' : 'var(--faint)',
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
            <div className="card" style={{ borderColor: 'var(--warn)', marginBottom: '12px', padding: '10px 14px' }}>
              <span style={{ color: bookingMsg.color, fontSize: '0.8125rem' }}>{bookingMsg.text}</span>
            </div>
          )}

          <div style={{ marginBottom: '16px' }}>
            <h2 style={{ margin: 0 }}>🌿 Welcome, {user?.name}</h2>
            {role === 'Patient' && user?.assigned_psych && (
              <div style={{ color: 'var(--soft)', fontSize: '0.8125rem', marginTop: '4px' }}>
                💉 Your psychologist: <strong style={{ color: 'var(--accent)' }}>{user.assigned_psych}</strong>
              </div>
            )}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', marginBottom: '16px' }}>
            {role === 'Psychologist' ? (
              <>
                <StatusCard label="Patients" value={patientCount} unit="under care" color="var(--accent)" />
                <StatusCard label="Pending" value={pendingBookings} unit="booking approvals" color={pendingBookings > 0 ? 'var(--warn)' : 'var(--accent)'} />
                <StatusCard label="Silent" value={silentPatients} unit="patients >48h" color={silentPatients > 0 ? 'var(--danger)' : 'var(--ok)'} />
                <StatusCard label="Crisis" value={crisisState?.active ? 'ACTIVE' : 'None'} unit="current" color={crisisState?.active ? 'var(--danger)' : 'var(--muted)'} />
              </>
            ) : (
              <>
                <StatusCard label="Heart" value={heartRate} unit="bpm" color="#CC5A4E" />
                <StatusCard label="Journal" value={journalOk} unit="today" color={journalOk === 'Logged' ? 'var(--ok)' : 'var(--muted)'} />
                <StatusCard label="Next Session" value={nextSession} unit="" color={nextSession !== '-' ? 'var(--ok)' : 'var(--muted)'} />
                <StatusCard label="Mood" value={todayMood} unit="today" color={todayMood !== '-' ? 'var(--ok)' : 'var(--muted)'} />
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
    <div style={{ background: 'linear-gradient(135deg, var(--surface), var(--surface))', border: '1px solid var(--border)', borderRadius: '8px', padding: '8px 12px', display: 'flex', alignItems: 'center', gap: '12px' }}>
      <div>
        <div style={{ color: 'var(--muted)', fontSize: '0.6875rem', fontWeight: 500 }}>{label}</div>
        <div style={{ color, fontSize: '1.125rem', fontWeight: 700 }}>{value}</div>
      </div>
      {unit && <div style={{ color: 'var(--faint)', fontSize: '0.625rem' }}>{unit}</div>}
    </div>
  )
}
