import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { EmotionBars } from '../components/EmotionBar'

export default function EmotionTimelinePage() {
  const [data, setData] = useState<any>(null)
  const [selectedPatient, setSelectedPatient] = useState<string>('')

  useEffect(() => {
    if (!selectedPatient) return
    api.getEmotionTimeline(selectedPatient, 30).then(setData).catch(() => {})
  }, [selectedPatient])

  return (
    <div className="animate-fade-in">
      <h2>Emotion Timeline</h2>
      <p style={{ color: '#6a6474', fontSize: '0.75rem', marginBottom: '16px' }}>
        View emotion probability trends across journal entries.
      </p>

      <PatientSelector value={selectedPatient} onChange={setSelectedPatient} />

      {data && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '10px', marginBottom: '20px' }}>
            {Object.entries(data.emotion_summary || {}).slice(0, 8).map(([emotion, info]: [string, any]) => (
              <div key={emotion} className="card" style={{ padding: '10px' }}>
                <div style={{ color: '#c49ea4', fontSize: '0.6875rem', fontWeight: 600 }}>{emotion}</div>
                <div style={{ color: '#f0f4ff', fontSize: '1rem', fontWeight: 700 }}>{info.average}%</div>
                <div style={{ color: '#6a6474', fontSize: '0.625rem' }}>
                  peak {info.max}% &middot; {info.count}x
                </div>
              </div>
            ))}
          </div>

          <h3>Journal Entry Timeline ({data.entries_count ?? 0} entries)</h3>
          {(data.timeline?.length ?? 0) === 0 ? (
            <div className="card" style={{ color: '#6a6474', textAlign: 'center', padding: '20px' }}>
              No analyzed entries in this period.
            </div>
          ) : (
            data.timeline.map((point: any) => (
              <div key={point.journal_id} className="expander" style={{ cursor: 'default' }}>
                <div className="expander-header">
                  <span>{point.timestamp?.slice(0, 10)} &middot; {point.emotions}</span>
                </div>
                <div className="expander-body">
                  <EmotionBars emotionProbabilities={point.emotion_probabilities} />
                </div>
              </div>
            ))
          )}
        </>
      )}
    </div>
  )
}

function PatientSelector({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [patients, setPatients] = useState<any[]>([])
  useEffect(() => {
    api.getPsychPatients().then(setPatients).catch(() => {})
  }, [])
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      style={{
        width: '100%', padding: '8px 12px', borderRadius: '8px',
        background: '#1e2336', border: '1px solid #2d2d44', color: '#e0e8f0',
        fontSize: '0.8125rem', marginBottom: '16px',
      }}
    >
      <option value="">-- Select patient --</option>
      {patients.map((p: any) => (
        <option key={p.username || p} value={p.username || p}>{p.name || p}</option>
      ))}
    </select>
  )
}
