// Shared frontend constants — single source of truth (Phase 5).
// Constitution #6: these were duplicated across 4+ pages; define once here.

export interface MoodDef {
  label: string
  emoji: string
  score: number
  color: string
}

// Canonical vocabulary. Must match the backend scoring set
// (services/timeline_service.py `_mood_val`): lowercase labels only,
// so logged moods are scored correctly.
export const MOODS: MoodDef[] = [
  { label: 'great', emoji: '🤩', score: 5, color: '#22c55e' },
  { label: 'good', emoji: '😊', score: 4, color: '#86efac' },
  { label: 'okay', emoji: '😐', score: 3, color: '#fbbf24' },
  { label: 'bad', emoji: '😞', score: 2, color: '#fb923c' },
  { label: 'awful', emoji: '😰', score: 1, color: '#ef4444' },
  { label: 'terrible', emoji: '💩', score: 0, color: '#7f1d1d' },
]

const MOOD_BY_LOWER: Record<string, MoodDef> = Object.fromEntries(MOODS.map(m => [m.label, m]))

// Case-insensitive lookups so legacy/display labels ("Great", "Down") still resolve.
export function moodIcon(label?: string | null): string {
  return MOOD_BY_LOWER[(label || '').toLowerCase()]?.emoji || '❓'
}

export function moodColor(label?: string | null): string {
  return MOOD_BY_LOWER[(label || '').toLowerCase()]?.color || '#888'
}

export function moodScore(label?: string | null): number {
  return MOOD_BY_LOWER[(label || '').toLowerCase()]?.score ?? 3
}

// AI source badge palette (ollama/groq/rule/ai) — was duplicated across 4 pages.
export const SOURCE_COLORS: Record<string, string> = {
  ollama: '#c49ea4',
  groq: '#22c55e',
  rule: '#f59e0b',
  ai: '#60a5fa',
}

export function sourceColor(src?: string | null): string {
  return SOURCE_COLORS[(src || '').toLowerCase()] || '#888'
}

// Time/date helpers — was re-implemented ~15 times.
export function formatTime(ts?: string | null): string {
  if (!ts) return ''
  try {
    return new Date(ts).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch {
    return ts
  }
}

export function formatDateTime(ts?: string | null): string {
  if (!ts) return ''
  try {
    return new Date(ts).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch {
    return ts
  }
}

export function formatDate(ts?: string | null): string {
  if (!ts) return ''
  try {
    return new Date(ts).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  } catch {
    return ts
  }
}

export function todayStr(): string {
  return new Date().toISOString().slice(0, 10)
}

// Placeholder sensor-series generator (was duplicated: Dashboard + PsychJournal).
export function mockHistory(base: number, variance: number, len = 24): number[] {
  return Array.from({ length: len }, (_, i) => Math.round(base + (Math.sin(i * 0.6) * variance) + (Math.random() - 0.5) * variance * 0.5))
}

// ── Crisis stage machine (was duplicated: Layout.tsx:167-184 ≈ CrisisPage.tsx:83-91) ──

export const TRUSTED_DELAY = 30
export const HELPLINE_DELAY = 60

export interface CrisisStageDef {
  key: string
  label: string
  sec: number
}

export const CRISIS_STAGES: CrisisStageDef[] = [
  { key: 'triggered', label: '🚨 Triggered', sec: 0 },
  { key: 'trustee_notified', label: '👤 Trusted Contact', sec: TRUSTED_DELAY },
  { key: 'helpline_escalated', label: '🏥 Helpline', sec: HELPLINE_DELAY },
]

export const CRISIS_STAGE_MESSAGES: Record<string, { text: string; color: string }> = {
  acknowledged: { text: '✅ Crisis acknowledged. Support team is with you.', color: '#22c55e' },
  trustee_coming: { text: '🟢 Trusted contact is on the way.', color: '#4ade80' },
  trustee_clicked: { text: '🟢 Trusted contact has been notified.', color: '#6ee7a7' },
  helpline_escalated: { text: '🚨 Crisis escalated to helpline. Professional help dispatched.', color: '#ef4444' },
  trustee_notified: { text: '👤 Trusted contact notified.', color: '#f59e0b' },
  triggered: { text: '🔴 Crisis active — help is on the way.', color: '#ef4444' },
}

export function computeCrisisStage(cs: any, elapsed: number): string {
  if (!cs?.active) return 'none'
  if (cs.acknowledged) return 'acknowledged'
  if (cs.trustee_acknowledged) return 'trustee_coming'
  if (cs.trustee_clicked) return 'trustee_clicked'
  if (elapsed >= HELPLINE_DELAY) return 'helpline_escalated'
  if (elapsed >= TRUSTED_DELAY) return 'trustee_notified'
  return 'triggered'
}
