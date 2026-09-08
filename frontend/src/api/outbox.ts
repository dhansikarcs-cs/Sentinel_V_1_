// Offline outbox: queues journal + mood writes in IndexedDB when the server is
// unreachable, then flushes them to /sync/journals + /sync/moods once back online.
//
// Flow:
//   1. createJournal / logMood try the network first.
//   2. On network failure (fetch TypeError / !navigator.onLine) the write is
//      enqueued here with a client_id, and the UI shows it as "saved offline".
//   3. on 'online' (or an interval), flushOutbox() pushes queued entries to the
//      batched sync endpoints, which dedupe by (content, timestamp) / (date).

export type OutboxKind = 'journal' | 'mood'

export interface OutboxEntry {
  kind: OutboxKind
  client_id: string
  payload: Record<string, any>
  created_at: number
}

const DB_NAME = 'sentinel-outbox'
const DB_VERSION = 1
const STORE = 'pending'

let _db: IDBDatabase | null = null
let _listeners: Array<() => void> = []

function _notify() {
  _listeners.forEach((fn) => fn())
}

export function subscribeOutbox(fn: () => void) {
  _listeners.push(fn)
  return () => {
    _listeners = _listeners.filter((l) => l !== fn)
  }
}

function _open(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (_db) return resolve(_db)
    const req = indexedDB.open(DB_NAME, DB_VERSION)
    req.onupgradeneeded = () => {
      const db = req.result
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: 'client_id' })
      }
    }
    req.onsuccess = () => {
      _db = req.result
      resolve(_db)
    }
    req.onerror = () => reject(req.error)
  })
}

function _tx<T>(mode: IDBTransactionMode, fn: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  return _open().then(
    (db) =>
      new Promise<T>((resolve, reject) => {
        const tx = db.transaction(STORE, mode)
        const req = fn(tx.objectStore(STORE))
        req.onsuccess = () => resolve(req.result)
        req.onerror = () => reject(req.error)
      }),
  )
}

function _clientId(): string {
  try {
    return crypto.randomUUID()
  } catch {
    return `c-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
  }
}

export async function enqueueOutbox(kind: OutboxKind, payload: Record<string, any>, clientId?: string): Promise<string> {
  const client_id = clientId || _clientId()
  const entry: OutboxEntry = { kind, client_id, payload, created_at: Date.now() }
  try {
    await _tx('readwrite', (store) => store.put(entry))
  } catch {
    // IndexedDB unavailable (private mode etc.) — still return the id so the
    // caller can proceed; the entry is simply lost if the server was down.
  }
  _notify()
  return client_id
}

export async function getOutboxCount(kind?: OutboxKind): Promise<number> {
  try {
    const all = await _tx('readonly', (store) => store.getAll())
    if (kind) return all.filter((e) => e.kind === kind).length
    return all.length
  } catch {
    return 0
  }
}

export async function getOutboxAll(): Promise<OutboxEntry[]> {
  try {
    const all = await _tx('readonly', (store) => store.getAll())
    return all.sort((a, b) => a.created_at - b.created_at)
  } catch {
    return []
  }
}

export async function clearOutbox(kinds: OutboxKind[]) {
  try {
    await _open()
    const tx = _db!.transaction(STORE, 'readwrite')
    const store = tx.objectStore(STORE)
    const all = await _tx('readonly', (s) => s.getAll())
    for (const e of all) {
      if (kinds.includes(e.kind)) store.delete(e.client_id)
    }
    await new Promise<void>((resolve, reject) => {
      tx.oncomplete = () => resolve()
      tx.onerror = () => reject(tx.error)
    })
  } catch {}
  _notify()
}

export function isOffline(): boolean {
  return typeof navigator !== 'undefined' && navigator.onLine === false
}

export type FlushResult = { journalsSynced: number; moodsSynced: number; journalsFailed: number; moodsFailed: number }

// Pushes queued entries to the batched /sync endpoints. The server dedupes by
// (content, timestamp) / (date, patient), so re-syncing an already-applied
// entry is harmless — it returns "duplicate" and we drop it.
export async function flushOutbox(apiHooks: {
  syncOfflineJournals: (entries: any[]) => Promise<any>
  syncOfflineMoods: (entries: any[]) => Promise<any>
}): Promise<FlushResult> {
  if (isOffline()) {
    return { journalsSynced: 0, moodsSynced: 0, journalsFailed: 0, moodsFailed: 0 }
  }
  const all = await getOutboxAll()
  if (all.length === 0) return { journalsSynced: 0, moodsSynced: 0, journalsFailed: 0, moodsFailed: 0 }

  const journals = all.filter((e) => e.kind === 'journal').map((e) => e.payload)
  const moods = all.filter((e) => e.kind === 'mood').map((e) => e.payload)

  let journalsSynced = 0
  let moodsSynced = 0
  let journalsFailed = 0
  let moodsFailed = 0

  if (journals.length > 0) {
    try {
      const res = await apiHooks.syncOfflineJournals(journals)
      journalsSynced = res?.count ?? res?.synced?.length ?? journals.length
    } catch {
      journalsFailed = journals.length
    }
  }
  if (moods.length > 0) {
    try {
      const res = await apiHooks.syncOfflineMoods(moods)
      moodsSynced = res?.count ?? res?.synced?.length ?? moods.length
    } catch {
      moodsFailed = moods.length
    }
  }

  if (journalsSynced > 0 || moodsSynced > 0) {
    const toClear: OutboxKind[] = []
    if (journalsSynced > 0) toClear.push('journal')
    if (moodsSynced > 0) toClear.push('mood')
    await clearOutbox(toClear)
  }
  _notify()
  return { journalsSynced, moodsSynced, journalsFailed, moodsFailed }
}