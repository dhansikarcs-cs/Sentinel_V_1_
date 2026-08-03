interface PriorityItem {
  level: 'high' | 'medium' | 'low'
  title: string
  reason: string
  evidence: string
  action: string
}

const LEVEL_STYLE: Record<string, { color: string; border: string; bg: string; dot: string }> = {
  high: { color: '#fca5a5', border: '#ef444455', bg: '#2a0f1c', dot: '#ef4444' },
  medium: { color: '#fde68a', border: '#f59e0b44', bg: '#241b0e', dot: '#f59e0b' },
  low: { color: '#bbf7d0', border: '#22c55e44', bg: '#0d2316', dot: '#22c55e' },
}

// Shared, explainable "things needing attention" panel. Pure display of the
// backend-derived overview.priorities (reason/evidence/action).
export default function PrioritiesPanel({ priorities }: { priorities: PriorityItem[] | undefined }) {
  if (!priorities || priorities.length === 0) return null

  const items = priorities.slice(0, 3)
  return (
    <div style={{ marginBottom: '16px' }}>
      <div style={{ color: '#c49ea4', fontWeight: 600, fontSize: '0.75rem', marginBottom: '8px' }}>
        ⚡ TOP {items.length === 1 ? 'PRIORITY' : 'PRIORITIES'} · WHAT NEEDS YOUR ATTENTION
      </div>
      {items.map((p, i) => {
        const s = LEVEL_STYLE[p.level] || LEVEL_STYLE.low
        return (
          <div key={i} style={{ background: s.bg, border: `1px solid ${s.border}`, borderRadius: '8px', padding: '10px 14px', marginBottom: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: s.dot, flexShrink: 0 }} />
              <span style={{ color: s.color, fontWeight: 700, fontSize: '0.8125rem' }}>{p.title}</span>
              <span style={{ marginLeft: 'auto', color: s.dot, fontSize: '0.6rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{p.level}</span>
            </div>
            <div style={{ fontSize: '0.6875rem', color: '#9aa8c0', lineHeight: 1.6 }}>
              <div><strong style={{ color: '#c49ea4' }}>Reason: </strong>{p.reason}</div>
              <div><strong style={{ color: '#c49ea4' }}>Evidence: </strong>{p.evidence}</div>
              <div><strong style={{ color: '#c49ea4' }}>Action: </strong>{p.action}</div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
