interface PriorityItem {
  level: 'high' | 'medium' | 'low'
  title: string
  reason: string
  evidence: string
  action: string
}

const LEVEL_STYLE: Record<string, { dot: string; label: string }> = {
  high: { dot: '#C7463B', label: '#B5453D' },
  medium: { dot: '#B7791A', label: '#9A6A00' },
  low: { dot: '#2E8B57', label: '#2E7D4F' },
}

// Shared, explainable "things needing attention" panel. Pure display of the
// backend-derived overview.priorities (reason/evidence/action).
export default function PrioritiesPanel({ priorities }: { priorities: PriorityItem[] | undefined }) {
  if (!priorities || priorities.length === 0) return null

  const items = priorities.slice(0, 3)
  return (
    <div style={{ marginBottom: '16px' }}>
      <div style={{ color: '#17796E', fontWeight: 600, fontSize: '0.75rem', marginBottom: '8px' }}>
        ⚡ TOP {items.length === 1 ? 'PRIORITY' : 'PRIORITIES'} · WHAT NEEDS YOUR ATTENTION
      </div>
      {items.map((p, i) => {
        const s = LEVEL_STYLE[p.level] || LEVEL_STYLE.low
        return (
          <div key={i} style={{ background: 'linear-gradient(135deg, #FFFFFF, #FFFFFF)', border: '1px solid #D9E7E3', borderRadius: '8px', padding: '10px 14px', marginBottom: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: s.dot, flexShrink: 0 }} />
              <span style={{ color: '#20363C', fontWeight: 700, fontSize: '0.8125rem' }}>{p.title}</span>
              <span style={{ marginLeft: 'auto', color: s.label, fontSize: '0.6rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{p.level}</span>
            </div>
            <div style={{ fontSize: '0.6875rem', color: '#93A79E', lineHeight: 1.6 }}>
              <div><strong style={{ color: '#6B8179' }}>Reason: </strong>{p.reason}</div>
              <div><strong style={{ color: '#6B8179' }}>Evidence: </strong>{p.evidence}</div>
              <div><strong style={{ color: '#6B8179' }}>Action: </strong>{p.action}</div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
