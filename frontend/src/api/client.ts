const BASE = '/api'

let _token: string | null = localStorage.getItem('token')

export function setToken(t: string | null) {
  _token = t
  if (t) localStorage.setItem('token', t)
  else localStorage.removeItem('token')
}

export function getToken() {
  return _token
}

async function request(path: string, options: RequestInit = {}): Promise<any> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  if (_token) headers['Authorization'] = `Bearer ${_token}`

  const res = await fetch(`${BASE}${path}`, { ...options, headers })

  if (res.status === 401) {
    setToken(null)
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }

  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || 'Request failed')
  return data
}

function buildBody(data: any): string | undefined {
  if (data === undefined || data === null) return undefined
  if (typeof data === 'string') return data
  return JSON.stringify(data)
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
  getPatientProfile: (username: string) => request(`/patients/${username}/profile`),
  getPatientSummary: (username: string) => request(`/patients/${username}/summary`),

  // Psychologists
  getPsychPatients: () => request('/psychologists/patients'),
  getAvailablePsychs: (clinic?: string) => request(`/psychologists/available${clinic ? `?clinic=${clinic}` : ''}`),

  // Journal
  createJournal: (raw: string) => request('/journal', { method: 'POST', body: JSON.stringify({ raw_content: raw }) }),
  getJournals: () => request('/journal'),
  getPatientJournals: (username: string) => request(`/journal/${username}`),
  getPatientSummaries: (username: string) => request(`/journal/${username}/summaries`),

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

  // Bookings
  createBooking: (data: any) => request('/bookings', { method: 'POST', body: JSON.stringify(data) }),
  getBookings: () => request('/bookings'),
  updateBookingStatus: (id: number, status: string) =>
    request(`/bookings/${id}/status`, { method: 'PUT', body: JSON.stringify({ status }) }),

  // Followups
  createFollowup: (data: any) => request('/followups', { method: 'POST', body: JSON.stringify(data) }),
  getFollowups: () => request('/followups'),
  updateFollowup: (id: string, data: any) => request(`/followups/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  // Ring
  pushSensorData: (data: any) => request('/ring/data', { method: 'POST', body: JSON.stringify(data) }),
  getSensorData: () => request('/ring/data'),

  // Timeline
  getTimeline: (username: string, days: number = 30) => request(`/timeline/${username}?days=${days}`),
  getMetrics: (username: string) => request(`/timeline/${username}/metrics`),
}
