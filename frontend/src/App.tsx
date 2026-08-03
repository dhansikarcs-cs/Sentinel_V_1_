import { Routes, Route, Navigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { isAuthenticated, fetchMe, getUser } from './stores/auth'
import Layout from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import JournalPage from './pages/JournalPage'
import MoodPage from './pages/MoodPage'
import CrisisPage from './pages/CrisisPage'
import BookingsPage from './pages/BookingsPage'
import FollowupsPage from './pages/FollowupsPage'
import TimelinePage from './pages/TimelinePage'
import PatientInsightsPage from './pages/PatientInsightsPage'
import ProfilePage from './pages/ProfilePage'
import PsychTriagePage from './pages/PsychTriagePage'
import ClinicalNotesPage from './pages/ClinicalNotesPage'
import PsychJournalPage from './pages/PsychJournalPage'
import ExportPage from './pages/ExportPage'
import OnboardingPage from './pages/OnboardingPage'
import PsychOnboardingPage from './pages/PsychOnboardingPage'
import TrusteePortalPage from './pages/TrusteePortalPage'
import ActivityFeedPage from './pages/ActivityFeedPage'
import ErrorBoundary from './ErrorBoundary'

const PATIENT_ONLY = ['/dashboard', '/journal', '/mood', '/crisis', '/timeline']
const PSYCH_ONLY = ['/triage', '/clinical-notes', '/psych-journal', '/patient-insights', '/export']
const SHARED = ['/bookings', '/followups', '/profile']

function RequireAuth({ children }: { children: React.ReactNode }) {
  const authed = isAuthenticated()
  const [ready, setReady] = useState(false)

  useEffect(() => {
    if (!authed) return
    fetchMe().then(() => setReady(true)).catch(() => setReady(true))
  }, [authed])

  if (!authed) return <Navigate to="/login" replace />
  if (!ready) return <div className="p-8 text-gray-400">Loading...</div>
  return <>{children}</>
}

function RequireRole({ roles, children }: { roles: string[]; children: React.ReactNode }) {
  const user = getUser()
  if (user && !roles.includes(user.role)) {
    return <Navigate to={user.role === 'psychologist' ? '/triage' : '/dashboard'} replace />
  }
  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/onboarding" element={<RequireAuth><OnboardingPage /></RequireAuth>} />
      <Route path="/psych-onboarding" element={<RequireAuth><PsychOnboardingPage /></RequireAuth>} />
      <Route path="/trustee" element={<TrusteePortalPage />} />
      <Route path="/activity" element={<RequireAuth><ErrorBoundary><Layout /></ErrorBoundary></RequireAuth>}>
        <Route index element={<ActivityFeedPage />} />
      </Route>
        <Route element={<RequireAuth><ErrorBoundary><Layout /></ErrorBoundary></RequireAuth>}>
        <Route path="/dashboard" element={<RequireRole roles={['patient']}><Dashboard /></RequireRole>} />
        <Route path="/journal" element={<RequireRole roles={['patient']}><JournalPage /></RequireRole>} />
        <Route path="/mood" element={<RequireRole roles={['patient']}><MoodPage /></RequireRole>} />
        <Route path="/bookings" element={<BookingsPage />} />
        <Route path="/followups" element={<FollowupsPage />} />
        <Route path="/timeline" element={<RequireRole roles={['patient']}><TimelinePage /></RequireRole>} />
        <Route path="/crisis" element={<RequireRole roles={['patient']}><CrisisPage /></RequireRole>} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/triage" element={<RequireRole roles={['psychologist']}><PsychTriagePage /></RequireRole>} />
        <Route path="/clinical-notes" element={<RequireRole roles={['psychologist']}><ClinicalNotesPage /></RequireRole>} />
        <Route path="/patient-insights" element={<RequireRole roles={['psychologist']}><PatientInsightsPage /></RequireRole>} />
        <Route path="/psych-journal" element={<RequireRole roles={['psychologist']}><PsychJournalPage /></RequireRole>} />
        <Route path="/export" element={<RequireRole roles={['psychologist']}><ExportPage /></RequireRole>} />
      </Route>
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}
