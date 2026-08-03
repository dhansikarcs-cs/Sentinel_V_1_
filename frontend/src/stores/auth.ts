import { api, setToken, setRefreshToken, getToken } from '../api/client'

export interface User {
  username: string
  name: string
  role: string
  clinic: string
  contact_info?: string
  trusted_contact?: string
  assigned_psych?: string
  onboarding_step?: number
}

let _user: User | null = null
let _listeners: Array<() => void> = []

export function subscribe(fn: () => void) {
  _listeners.push(fn)
  return () => { _listeners = _listeners.filter(l => l !== fn) }
}

function notify() { _listeners.forEach(fn => fn()) }

export async function login(username: string, password: string) {
  const res = await api.login(username, password)
  setToken(res.access_token)
  if (res.refresh_token) setRefreshToken(res.refresh_token)
  await fetchMe()
  return res
}

export function logout() {
  setToken(null)
  setRefreshToken(null)
  _user = null
  notify()
}

export async function fetchMe() {
  try {
    _user = await api.getMe()
    notify()
    return _user
  } catch {
    _user = null
    notify()
    return null
  }
}

export function getUser() { return _user }
export function isAuthenticated() { return !!getToken() }
