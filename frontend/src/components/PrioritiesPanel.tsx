interface PriorityItem {
  level: 'high' | 'medium' | 'low'
  title: string
  reason: string
  evidence: string
  action: string
}

const LEVEL_STYLE: Record<string, { dot: string; label: string }> = {
  high: { dot: '#ef4444', label: '#fca5a5' },
  medium: { dot: '#f59e0b', label: '#fde68a' },
  low: { dot: '#22c55e', label: '#bbf7d0' },
}

// Shared, explainable "things needing attention" panel. Pure display of the
// backend-derived overview.priorities (reason/evidence/action).
export default function PrioritiesPanel({ priorities }: { priorities: PriorityItem[] | undefined }) {
  if (!priorities || priorities.length === 0) return null

  const items = priorities.slice(0, 3)
  return (
    <div style={{ marginBottom: '16px' }}>
      <div style={{ color: '#8fcbb1', fontWeight: 600, fontSize: '0.75rem', marginBottom: '8px' }}>
        ⚡ TOP {items.length === 1 ? 'PRIORITY' : 'PRIORITIES'} · WHAT NEEDS YOUR ATTENTION
      </div>
      {items.map((p, i) => {
        const s = LEVEL_STYLE[p.level] || LEVEL_STYLE.low
        return (
          <div key={i} style={{ background: 'linear-gradient(135deg, #1d2623, #19211e)', border: '1px solid #31423a', borderRadius: '8px', padding: '10px 14px', marginBottom: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: s.dot, flexShrink: 0 }} />
              <span style={{ color: '#f0f2e8', fontWeight: 700, fontSize: '0.8125rem' }}>{p.title}</span>
              <span style={{ marginLeft: 'auto', color: s.label, fontSize: '0.6rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{p.level}</span>
            </div>
            <div style={{ fontSize: '0.6875rem', color: '#9dada4', lineHeight: 1.6 }}>
              <div><strong style={{ color: '#8f86a0' }}>Reason: </strong>{p.reason}</div>
              <div><strong style={{ color: '#8f86a0' }}>Evidence: </strong>{p.evidence}</div>
              <div><strong style={{ color: '#8f86a0' }}>Action: </strong>{p.action}</div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
