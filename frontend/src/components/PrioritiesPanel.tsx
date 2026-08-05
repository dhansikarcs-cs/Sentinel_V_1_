interface PriorityItem {
  level: 'high' | 'medium' | 'low'
  title: string
  reason: string
  evidence: string
  action: string
}

const LEVEL_STYLE: Record<string, { dot: string; label: string }> = {
  high: { dot: 'var(--danger)', label: 'var(--danger-deep)' },
  medium: { dot: 'var(--warn)', label: '#9A6A00' },
  low: { dot: 'var(--ok)', label: '#2E7D4F' },
}

// Shared, explainable "things needing attention" panel. Pure display of the
// backend-derived overview.priorities (reason/evidence/action).
export default function PrioritiesPanel({ priorities }: { priorities: PriorityItem[] | undefined }) {
  if (!priorities || priorities.length === 0) return null

  const items = priorities.slice(0, 3)
  return (
    <div style={{ marginBottom: '16px' }}>
      <div style={{ color: 'var(--accent)', fontWeight: 600, fontSize: '0.75rem', marginBottom: '8px' }}>
        ⚡ TOP {items.length === 1 ? 'PRIORITY' : 'PRIORITIES'} · WHAT NEEDS YOUR ATTENTION
      </div>
      {items.map((p, i) => {
        const s = LEVEL_STYLE[p.level] || LEVEL_STYLE.low
        return (
          <div key={i} style={{ background: 'linear-gradient(135deg, var(--surface), var(--surface))', border: '1px solid var(--border)', borderRadius: '8px', padding: '10px 14px', marginBottom: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: s.dot, flexShrink: 0 }} />
              <span style={{ color: 'var(--strong)', fontWeight: 700, fontSize: '0.8125rem' }}>{p.title}</span>
              <span style={{ marginLeft: 'auto', color: s.label, fontSize: '0.6rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{p.level}</span>
            </div>
            <div style={{ fontSize: '0.6875rem', color: 'var(--soft)', lineHeight: 1.6 }}>
              <div><strong style={{ color: 'var(--label)' }}>Reason: </strong>{p.reason}</div>
              <div><strong style={{ color: 'var(--label)' }}>Evidence: </strong>{p.evidence}</div>
              <div><strong style={{ color: 'var(--label)' }}>Action: </strong>{p.action}</div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
