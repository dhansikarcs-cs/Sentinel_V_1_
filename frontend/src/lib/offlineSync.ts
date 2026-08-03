const OFFLINE_KEY = 'sentinel_offline_queue'
const SYNC_STATUS_KEY = 'sentinel_sync_status'

export interface OfflineEntry {
  id: string
  type: 'journal' | 'mood'
  data: any
  timestamp: string
  synced: boolean
}

export function queueOffline(entry: Omit<OfflineEntry, 'id' | 'synced'>) {
  const queue = getOfflineQueue()
  const id = `${entry.type}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
  queue.push({ ...entry, id, synced: false })
  localStorage.setItem(OFFLINE_KEY, JSON.stringify(queue))
}

export function getOfflineQueue(): OfflineEntry[] {
  try {
    return JSON.parse(localStorage.getItem(OFFLINE_KEY) || '[]')
  } catch {
    return []
  }
}

export function clearSynced() {
  const queue = getOfflineQueue().filter(e => !e.synced)
  localStorage.setItem(OFFLINE_KEY, JSON.stringify(queue))
}

export function markSynced(id: string) {
  const queue = getOfflineQueue()
  const entry = queue.find(e => e.id === id)
  if (entry) entry.synced = true
  localStorage.setItem(OFFLINE_KEY, JSON.stringify(queue))
}

export async function syncPending(api: any): Promise<{ synced: number; failed: number }> {
  const queue = getOfflineQueue().filter(e => !e.synced)
  let synced = 0
  let failed = 0

  for (const entry of queue) {
    try {
      if (entry.type === 'journal') {
        await api.createJournal(entry.data.raw_content)
        markSynced(entry.id)
        synced++
      } else if (entry.type === 'mood') {
        await api.logMood(entry.data.date, entry.data.emoji, entry.data.label)
        markSynced(entry.id)
        synced++
      }
    } catch {
      failed++
    }
  }

  clearSynced()
  return { synced, failed }
}

export function getSyncStatus(): { pending: number; lastSync: string | null } {
  try {
    const status = JSON.parse(localStorage.getItem(SYNC_STATUS_KEY) || '{}')
    return {
      pending: getOfflineQueue().filter(e => !e.synced).length,
      lastSync: status.lastSync || null,
    }
  } catch {
    return { pending: 0, lastSync: null }
  }
}

export function updateSyncStatus() {
  localStorage.setItem(SYNC_STATUS_KEY, JSON.stringify({ lastSync: new Date().toISOString() }))
}
