const EMOTION_COLORS: Record<string, string> = {
  admiration: '#B7791A', amusement: '#2E8B57', anger: '#C7463B', annoyance: '#C05A12',
  approval: '#2E8B57', caring: '#ec4899', confusion: '#8b5cf6', curiosity: '#3b82f6',
  desire: '#C7463B', disappointment: '#6b7280', disapproval: '#6b7280', disgust: '#84cc16',
  embarrassment: '#f472b6', excitement: '#B7791A', fear: '#C7463B', gratitude: '#2E8B57',
  grief: '#6b7280', joy: '#2E8B57', love: '#ec4899', nervousness: '#C05A12',
  optimism: '#2E8B57', pride: '#B7791A', realization: '#3b82f6', relief: '#2E8B57',
  remorse: '#6b7280', sadness: '#3b82f6', surprise: '#B7791A', neutral: '#6b7280',
}

interface EmotionBarProps {
  label: string
  probability: number
  maxProb?: number
}

export function EmotionBar({ label, probability, maxProb }: EmotionBarProps) {
  const color = EMOTION_COLORS[label] || '#6b7280'
  const pct = Math.round(probability * 100)
  const isMax = maxProb !== undefined && probability >= maxProb
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: '2px 0' }}>
      <span style={{
        width: '90px', fontSize: '0.6875rem', color: '#93A79E',
        fontWeight: isMax ? 700 : 400, textAlign: 'right',
      }}>
        {label}
      </span>
      <div style={{
        flex: 1, height: '14px', background: '#FFFFFF', borderRadius: '7px',
        overflow: 'hidden', position: 'relative',
      }}>
        <div style={{
          width: `${pct}%`, height: '100%', background: color,
          borderRadius: '7px', opacity: 0.7,
          transition: 'width 0.3s ease',
        }} />
      </div>
      <span style={{
        width: '36px', fontSize: '0.625rem', color: '#6E837A',
        fontVariantNumeric: 'tabular-nums',
      }}>
        {pct}%
      </span>
    </div>
  )
}

interface EmotionBarsProps {
  emotionProbabilities: Record<string, number> | string
  maxItems?: number
}

export function EmotionBars({ emotionProbabilities, maxItems = 5 }: EmotionBarsProps) {
  let probs: Record<string, number> = {}
  if (typeof emotionProbabilities === 'string') {
    try { probs = JSON.parse(emotionProbabilities || '{}') } catch { probs = {} }
  } else {
    probs = emotionProbabilities || {}
  }
  const entries = Object.entries(probs)
    .filter(([, p]) => p > 0.08)
    .sort(([, a], [, b]) => b - a)
    .slice(0, maxItems)
  const maxProb = entries.length > 0 ? entries[0][1] : 0
  return (
    <div style={{ padding: '4px 0' }}>
      {entries.map(([emotion, prob]) => (
        <EmotionBar key={emotion} label={emotion} probability={prob} maxProb={maxProb} />
      ))}
      {entries.length === 0 && (
        <div style={{ color: '#A8B9B1', fontSize: '0.6875rem' }}>No emotions detected.</div>
      )}
    </div>
  )
}
