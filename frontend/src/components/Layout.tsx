import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom'
import { getUser, logout } from '../stores/auth'
import { useEffect, useState } from 'react'
import { cn } from '../lib/utils'

const navItems = {
  Patient: [
    { to: '/dashboard', label: 'Dashboard', icon: '📊' },
    { to: '/journal', label: 'Journal', icon: '📝' },
    { to: '/mood', label: 'Mood', icon: '😊' },
    { to: '/bookings', label: 'Bookings', icon: '📅' },
    { to: '/followups', label: 'Follow-Ups', icon: '✅' },
    { to: '/timeline', label: 'Timeline', icon: '🔍' },
    { to: '/crisis', label: 'Emergency', icon: '🚨' },
    { to: '/profile', label: 'Profile', icon: '👤' },
  ],
  Psychologist: [
    { to: '/dashboard', label: 'Dashboard', icon: '📊' },
    { to: '/patients', label: 'Patients', icon: '👥' },
    { to: '/journal', label: 'Journal', icon: '📝' },
    { to: '/bookings', label: 'Bookings', icon: '📅' },
    { to: '/followups', label: 'Follow-Ups', icon: '✅' },
    { to: '/timeline', label: 'Timeline', icon: '🔍' },
    { to: '/profile', label: 'Profile', icon: '👤' },
  ],
}

export default function Layout() {
  const navigate = useNavigate()
  const location = useLocation()
  const [user, setUser] = useState(getUser())

  useEffect(() => {
    const unsub = subscribe(() => setUser(getUser()))
    return unsub
  }, [])

  const role = user?.role === 'psychologist' ? 'Psychologist' : 'Patient'
  const items = navItems[role] || navItems.Patient

  return (
    <div className="flex min-h-screen">
      <aside className="w-56 bg-gray-900 border-r border-gray-800 p-4 flex flex-col gap-1">
        <div className="text-lg font-bold text-pink-300 mb-6">Sentinel</div>
        {items.map(item => (
          <Link
            key={item.to}
            to={item.to}
            className={cn(
              'flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors',
              location.pathname === item.to
                ? 'bg-pink-900/30 text-pink-200'
                : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800',
            )}
          >
            <span>{item.icon}</span>
            {item.label}
          </Link>
        ))}
        <div className="mt-auto pt-4 border-t border-gray-800">
          <div className="text-xs text-gray-500 mb-2">{user?.name}</div>
          <button
            onClick={() => { logout(); navigate('/login') }}
            className="w-full text-left px-3 py-2 text-sm text-gray-400 hover:text-red-400 rounded-lg hover:bg-gray-800"
          >
            Logout
          </button>
        </div>
      </aside>
      <main className="flex-1 p-6 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
