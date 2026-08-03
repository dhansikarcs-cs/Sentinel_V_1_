const BASE = '/api'

let _token: string | null = localStorage.getItem('token')
let _refreshToken: string | null = localStorage.getItem('refresh_token')
let _isRefreshing = false

export function setToken(t: string | null) {
  _token = t
  if (t) localStorage.setItem('token', t)
  else localStorage.removeItem('token')
}

export function setRefreshToken(t: string | null) {
  _refreshToken = t
  if (t) localStorage.setItem('refresh_token', t)
  else localStorage.removeItem('refresh_token')
}

export function getToken() {
  return _token
}

async function tryRefresh(): Promise<boolean> {
  if (!_refreshToken || _isRefreshing) return false
  _isRefreshing = true
  try {
    const res = await fetch(`${BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: _refreshToken }),
    })
    if (res.ok) {
      const data = await res.json()
      setToken(data.access_token)
      if (data.refresh_token) setRefreshToken(data.refresh_token)
      _isRefreshing = false
      return true
    }
    setToken(null)
    setRefreshToken(null)
    _isRefreshing = false
    return false
  } catch {
    _isRefreshing = false
    return false
  }
}

async function request(path: string, options: RequestInit = {}, isRetry = false): Promise<any> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  if (_token) headers['Authorization'] = `Bearer ${_token}`

  const res = await fetch(`${BASE}${path}`, { ...options, headers })

  if (res.status === 401 && !isRetry && path !== '/auth/refresh') {
    const refreshed = await tryRefresh()
    if (refreshed) return request(path, options, true)
    setToken(null)
    setRefreshToken(null)
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }

  let data: any = {}
  try {
    const text = await res.text()
    try { data = JSON.parse(text) } catch { data = { detail: text || 'Request failed' } }
  } catch { data = { detail: 'Request failed' } }
  if (!res.ok) throw new Error(data.detail || data.message || 'Request failed')
  if (data?.success === true && data?.data !== undefined) return data.data
  return data
}

function buildBody(data: any): string | undefined {
  if (data === undefined || data === null) return undefined
  if (typeof data === 'string') return data
  return JSON.stringify(data)
}

// Multipart upload that goes through the same auth/refresh path as request()
// but without forcing a JSON Content-Type (the browser sets the boundary).
async function upload(path: string, file: File, isRetry = false): Promise<any> {
  const headers: Record<string, string> = {}
  if (_token) headers['Authorization'] = `Bearer ${_token}`

  const body = new FormData()
  body.append('file', file)

  const res = await fetch(`${BASE}${path}`, { method: 'POST', headers, body })

  if (res.status === 401 && !isRetry && path !== '/auth/refresh') {
    const refreshed = await tryRefresh()
    if (refreshed) return upload(path, file, true)
    setToken(null)
    setRefreshToken(null)
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }

  let data: any = {}
  try {
    const text = await res.text()
    try { data = JSON.parse(text) } catch { data = { detail: text || 'Request failed' } }
  } catch { data = { detail: 'Request failed' } }
  if (!res.ok) throw new Error(data.detail || data.message || 'Request failed')
  if (data?.success === true && data?.data !== undefined) return data.data
  return data
}

export const api = {
  get: (path: string) => request(path),
  post: (path: string, data?: any) => request(path, { method: 'POST', body: buildBody(data) }),
  put: (path: string, data?: any) => request(path, { method: 'PUT', body: buildBody(data) }),
  delete: (path: string) => request(path, { method: 'DELETE' }),

  // Auth
  login: (username: string, password: string) =>
    request('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }),
  register: (data: any) =>
    request('/auth/register', { method: 'POST', body: JSON.stringify(data) }),
  unlock: (passphrase: string) =>
    request('/auth/unlock', { method: 'POST', body: JSON.stringify({ passphrase }) }),
  encryptionStatus: () => request('/auth/encryption-status'),

  // Patients
  getMe: () => request('/patients/me'),
  updateContact: (data: any) => request('/patients/me/contact', { method: 'PUT', body: JSON.stringify(data) }),
  getPatientProfile: (username: string) => request(`/patients/${username}/profile`),
  getPatientSummary: (username: string) => request(`/patients/${username}/summary`),
  getPatientOverview: (username: string) => request(`/patients/${username}/overview`),
  uploadConsentForm: (file: File) => upload('/patients/me/consent', file),
  getWellness: () => request('/patients/me/wellness'),
  updateOnboarding: (step: number) => request('/patients/me/onboarding', { method: 'PUT', body: JSON.stringify({ step }) }),
  assignPsychologist: (username: string, psychUsername: string) =>
    request(`/patients/${username}/assign-psych`, { method: 'POST', body: JSON.stringify({ psych_username: psychUsername }) }),

  // Psychologists
  getPsychPatients: () => request('/psychologists/patients'),
  getAvailablePsychs: (clinic?: string) => request(`/psychologists/available${clinic ? `?clinic=${clinic}` : ''}`),
  getPsychNotes: () => request('/psychologists/notes'),
  createPsychNote: (data: any) => request('/psychologists/notes', { method: 'POST', body: JSON.stringify(data) }),

  // Journal
  createJournal: (raw: string) => request('/journal', { method: 'POST', body: JSON.stringify({ raw_content: raw }) }),
  getJournals: () => request('/journal'),
  getPatientJournals: (username: string) => request(`/journal/${username}`),
  getPatientSummaries: (username: string) => request(`/journal/${username}/summaries`),
  resummarizeJournal: (journalId: number) => request(`/journal/${journalId}/resummarize`, { method: 'POST' }),
  synthesizeNote: (journalText: string, clinicalSummary?: string) =>
    request('/journal/synthesize-note', { method: 'POST', body: JSON.stringify({ journal_text: journalText, clinical_summary: clinicalSummary || '' }) }),

  // Mood
  logMood: (date: string, emoji: string, label: string) =>
    request('/mood', { method: 'POST', body: JSON.stringify({ date, emoji, label }) }),
  getMoods: () => request('/mood'),
  getPatientMoods: (username: string) => request(`/mood/${username}`),
  checkTodayMood: () => request('/mood/today/check'),

  // Crisis
  getCrisisState: () => request('/crisis/state'),
  triggerCrisis: () => request('/crisis/trigger', { method: 'POST' }),
  acknowledgeCrisis: () => request('/crisis/acknowledge', { method: 'POST' }),
  resolveCrisis: () => request('/crisis/resolve', { method: 'POST' }),
  assessRisk: (text: string) => request('/crisis/assess-risk', { method: 'POST', body: JSON.stringify({ text }) }),
  getCrisisElapsed: () => request('/crisis/elapsed'),
  notifyTrustedContact: () => request('/crisis/notify-trusted-contact', { method: 'POST' }),
  trusteeAcknowledge: () => request('/crisis/trustee-acknowledge', { method: 'POST' }),
  trusteeClicked: () => request('/crisis/trustee-clicked', { method: 'POST' }),

  // Bookings
  createBooking: (data: any) => request('/bookings', { method: 'POST', body: JSON.stringify(data) }),
  getBookings: () => request('/bookings'),
  updateBookingStatus: (id: number, status: string) =>
    request(`/bookings/${id}/status`, { method: 'PUT', body: JSON.stringify({ status }) }),
  setAvailability: (data: any) => request('/bookings/availability', { method: 'POST', body: JSON.stringify(data) }),
  getMyAvailability: () => request(`/bookings/availability/me`),
  deleteAvailability: (slotId: number) => request(`/bookings/availability/${slotId}`, { method: 'DELETE' }),

  // Followups
  createFollowup: (data: any) => request('/followups', { method: 'POST', body: JSON.stringify(data) }),
  getFollowups: () => request('/followups'),
  updateFollowup: (id: string, data: any) => request(`/followups/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  uploadFollowupAttachment: (id: string, file: File) => upload(`/followups/${id}/upload`, file),
  uploadFollowupProof: (id: string, file: File) => upload(`/followups/${id}/upload-proof`, file),

  // Ring
  pushSensorData: (data: any) => request('/ring/data', { method: 'POST', body: JSON.stringify(data) }),
  getSensorData: () => request('/ring/data'),

  // Timeline
  getTimeline: (username: string, days: number = 30) => request(`/timeline/${username}?days=${days}`),
  getMetrics: (username: string) => request(`/timeline/${username}/metrics`),

  // Agents
  triageSummary: (patientUsername: string) =>
    request('/agents/triage-summary', { method: 'POST', body: JSON.stringify({ patient_username: patientUsername }) }),
  suggestSlots: (patientUsername: string) =>
    request('/agents/suggest-slots', { method: 'POST', body: JSON.stringify({ patient_username: patientUsername }) }),
  draftFollowup: (patientUsername: string) =>
    request('/agents/draft-followup', { method: 'POST', body: JSON.stringify({ patient_username: patientUsername }) }),
  journalToNote: (patientUsername: string, journalText: string, clinicalSummary?: string) =>
    request('/agents/journal-to-note', { method: 'POST', body: JSON.stringify({ patient_username: patientUsername, journal_text: journalText, clinical_summary: clinicalSummary || '' }) }),
  preSessionBrief: (patientUsername: string) =>
    request('/agents/pre-session-brief', { method: 'POST', body: JSON.stringify({ patient_username: patientUsername }) }),
  complianceRadar: () => request('/agents/compliance-radar', { method: 'POST' }),
  silentPeriodWatch: () => request('/agents/silent-period-watch', { method: 'POST' }),
  relapseIndicators: () => request('/agents/relapse-indicators', { method: 'POST' }),
  crossPatientPatterns: () => request('/agents/cross-patient-patterns', { method: 'POST' }),
  ringVitalsRisk: () => request('/agents/ring-vitals-risk', { method: 'POST' }),

  // Triage
  createTriage: (patientUsername: string) =>
    request('/triage', { method: 'POST', body: JSON.stringify({ patient_username: patientUsername }) }),
  getTriage: () => request('/triage'),
  getPatientTriage: (patientUsername: string) => request(`/triage/${patientUsername}`),
  updateTriage: (entryId: string, data: any) => request(`/triage/${entryId}`, { method: 'PUT', body: JSON.stringify(data) }),

  // Emotions (timeline)
  getEmotionTimeline: (username: string, days: number = 30) => request(`/emotions/timeline/${username}?days=${days}`),
  getEmotionSummary: (username: string, days: number = 30) => request(`/emotions/summary/${username}?days=${days}`),

  // Event Store
  getEvents: (eventType?: string, limit: number = 50) => request(`/events?limit=${limit}${eventType ? `&event_type=${eventType}` : ''}`),
  getPatientEvents: (username: string, limit: number = 50) => request(`/events/patient/${username}?limit=${limit}`),
  replayEvents: (fromSequence: number = 0) => request(`/events/replay?from_sequence=${fromSequence}`),

  // ML Registry
  getMLModels: () => request('/ml/models'),
  getMLModel: (name: string) => request(`/ml/models/${name}`),
  getFeatureStoreStats: () => request('/ml/feature-store/stats'),

  // Psych Journal
  createPsychJournal: (raw: string) => request('/psych-journal', { method: 'POST', body: JSON.stringify({ raw_content: raw }) }),
  getPsychJournals: () => request('/psych-journal'),

  // Activity
  getActivityFeed: (days?: number) => request(`/activity?days=${days || 7}`),

  // Emotion Results (structured table)
  getEmotionResultByJournal: (journalId: number) => request(`/emotion-results/journal/${journalId}`),
  getEmotionResultsForPatient: (username: string) => request(`/emotion-results/patient/${username}`),

  // AI Analyses (structured table)
  getAIAnalysisByJournal: (journalId: number) => request(`/ai-analyses/journal/${journalId}`),
  getAIAnalysesForPatient: (username: string) => request(`/ai-analyses/patient/${username}`),

  // Sensor Readings (structured table)
  createSensorReading: (data: any) => request('/sensor-readings', { method: 'POST', body: JSON.stringify(data) }),
  getSensorReadings: () => request('/sensor-readings'),
  getPatientSensorReadings: (username: string) => request(`/sensor-readings/patient/${username}`),

  // Risk Assessments (structured table)
  getRiskAssessmentByJournal: (journalId: number) => request(`/risk-assessments/journal/${journalId}`),
  getRiskAssessmentsForPatient: (username: string) => request(`/risk-assessments/patient/${username}`),

  // Notifications
  getNotifications: () => request('/notifications'),
  getUnreadNotifications: () => request('/notifications/unread'),
  markNotificationRead: (id: number) => request(`/notifications/${id}/read`, { method: 'PUT', body: JSON.stringify({ read: true }) }),
  markAllNotificationsRead: () => request('/notifications/read-all', { method: 'PUT' }),

  // Search
  searchJournals: (query: string, patientUsername?: string) =>
    request(`/search/journals?q=${encodeURIComponent(query)}${patientUsername ? `&patient_username=${patientUsername}` : ''}`),

  // Offline Sync
  syncOfflineJournals: (entries: any[]) => request('/sync/journals', { method: 'POST', body: JSON.stringify(entries) }),
  syncOfflineMoods: (entries: any[]) => request('/sync/moods', { method: 'POST', body: JSON.stringify(entries) }),

  // Feature Flags
  getFeatureFlags: () => request('/feature-flags'),
  updateFeatureFlag: (name: string, enabled: boolean, rolloutPct: number = 100) =>
    request(`/feature-flags/${name}?enabled=${enabled}&rollout_pct=${rolloutPct}`, { method: 'PUT' }),

  // Export
  exportJournalSummaries: (days?: number) => `${BASE}/export/journal-summaries?days=${days || 30}&token=${_token || ''}`,
  exportClinicalNotes: (days?: number) => `${BASE}/export/clinical-notes?days=${days || 30}&token=${_token || ''}`,
  exportPatientData: () => `${BASE}/export/patient-data?token=${_token || ''}`,
}
