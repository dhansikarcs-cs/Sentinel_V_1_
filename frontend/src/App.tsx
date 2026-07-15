import { Routes, Route, Navigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { isAuthenticated, fetchMe, getUser, subscribe } from './stores/auth'
import Layout from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import Unlock from './pages/Unlock'
import Dashboard from './pages/Dashboard'
import JournalPage from './pages/JournalPage'
import MoodPage from './pages/MoodPage'
import CrisisPage from './pages/CrisisPage'
import BookingsPage from './pages/BookingsPage'
import FollowupsPage from './pages/FollowupsPage'
import TimelinePage from './pages/TimelinePage'
import ProfilePage from './pages/ProfilePage'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const authed = isAuthenticated()
  const [ready, setReady] = useState(authed)

  useEffect(() => {
    if (!authed) return
    fetchMe().then(() => setReady(true))
  }, [])

  if (!authed) return <Navigate to="/login" replace />
  if (!ready) return <div className="p-8 text-gray-400">Loading...</div>
  return <>{children}</>
}

function RequireUnlock({ children }: { children: React.ReactNode }) {
  const [unlocked, setUnlocked] = useState<boolean | null>(null)

  useEffect(() => {
    fetch('/api/auth/encryption-status')
      .then(r => r.json())
      .then(d => setUnlocked(d.unlocked ?? false))
      .catch(() => setUnlocked(true))
  }, [])

  if (unlocked === null) return <div className="p-8 text-gray-400">Checking encryption...</div>
  if (!unlocked) return <Navigate to="/unlock" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/unlock" element={<Unlock />} />
      <Route
        element={
          <RequireAuth>
            <RequireUnlock>
              <Layout />
            </RequireUnlock>
          </RequireAuth>
        }
      >
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/journal" element={<JournalPage />} />
        <Route path="/mood" element={<MoodPage />} />
        <Route path="/crisis" element={<CrisisPage />} />
        <Route path="/bookings" element={<BookingsPage />} />
        <Route path="/followups" element={<FollowupsPage />} />
        <Route path="/timeline" element={<TimelinePage />} />
        <Route path="/profile" element={<ProfilePage />} />
      </Route>
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}
