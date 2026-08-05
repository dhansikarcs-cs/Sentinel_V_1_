import { MOODS } from '../constants'

interface MoodPickerProps {
  selected?: string | null
  locked?: boolean
  onSelect?: (label: string) => void
}

// Shared, professional mood selector. One entry per day; shows a uniform
// segmented chip row with the mood label as the primary signal and a small
// icon as support (Constitution #6: single source of truth via MOODS).
export default function MoodPicker({ selected, locked, onSelect }: MoodPickerProps) {
  return (
    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', justifyContent: 'center' }}>
      {MOODS.map(m => {
        const isSel = selected === m.label
        return (
          <button
            key={m.label}
            disabled={locked}
            onClick={() => onSelect?.(m.label)}
            title={`${m.label} · ${m.score}/5`}
            style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px',
              padding: '10px 14px', minWidth: '88px',
              background: isSel ? `${m.color}1f` : 'var(--surface)',
              border: isSel ? `1px solid ${m.color}` : '1px solid var(--border)',
              borderRadius: '10px', cursor: locked ? 'not-allowed' : 'pointer',
              opacity: locked && !isSel ? 0.45 : 1,
              transition: 'all 0.15s ease',
            }}
          >
            <span style={{ fontSize: '1.1rem', lineHeight: 1, opacity: 0.95 }}>{m.emoji}</span>
            <span style={{ fontSize: '0.65rem', fontWeight: 600, textTransform: 'capitalize', letterSpacing: '0.02em', color: isSel ? m.color : 'var(--soft)' }}>{m.label}</span>
          </button>
        )
      })}
    </div>
  )
}
