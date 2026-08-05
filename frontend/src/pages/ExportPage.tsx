import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { getUser } from '../stores/auth'

export default function ExportPage() {
  const user = getUser()
  const isPsych = user?.role === 'psychologist'
  const [mode, setMode] = useState<'patients' | 'myself'>('patients')
  const [patients, setPatients] = useState<any[]>([])
  const [selectedPatient, setSelectedPatient] = useState('')
  const [entries, setEntries] = useState<any[]>([])
  const [notes, setNotes] = useState<any[]>([])
  const [ownJournals, setOwnJournals] = useState<any[]>([])
  const [expandedEntries, setExpandedEntries] = useState<Record<string, boolean>>({})
  const [expandedNotes, setExpandedNotes] = useState<Record<string, boolean>>({})
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  useEffect(() => {
    if (isPsych) {
      api.getPsychPatients().then(setPatients).catch(() => {})
    }
    if (mode === 'myself') {
      api.getPsychJournals().then(setOwnJournals).catch(() => setOwnJournals([]))
    }
  }, [mode, isPsych])

  useEffect(() => {
    if (!selectedPatient) { setEntries([]); setNotes([]); return }
    api.getPatientSummaries(selectedPatient).then((d: any) => setEntries(Array.isArray(d) ? d : [])).catch(() => setEntries([]))
    api.get(`/psychologists/notes?patient=${selectedPatient}`).then((d: any) => setNotes(Array.isArray(d) ? d : [])).catch(() => setNotes([]))
  }, [selectedPatient])

  function downloadCsv(filename: string, rows: string[][]) {
    const csv = rows.map(r => r.map(c => `"${c.replace(/"/g, '""')}"`).join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = filename; a.click()
    URL.revokeObjectURL(url)
  }

  function filterByDate(items: any[]): any[] {
    if (!dateFrom && !dateTo) return items
    return items.filter((e: any) => {
      const ts = (e.timestamp || '').slice(0, 10)
      if (!ts) return true
      if (dateFrom && ts < dateFrom) return false
      if (dateTo && ts > dateTo) return false
      return true
    })
  }

  const filteredEntries = filterByDate(entries)
  const filteredNotes = filterByDate(notes)
  const filteredOwn = filterByDate(ownJournals)

  function toggleExpand(setter: any, key: string) {
    setter((prev: any) => ({ ...prev, [key]: !prev[key] }))
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <h1>ðŸ“¦ Export Center</h1>

      <div className="card" style={{ padding: '16px' }}>
        <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
          {['patients', 'myself'].map(m => (
            <button key={m} onClick={() => setMode(m as any)}
              style={{
                flex: 1, padding: '10px', borderRadius: '8px', border: `1px solid ${mode === m ? '#17796E' : '#D9E7E3'}`,
                background: mode === m ? '#E3F1EE' : '#FFFFFF', color: mode === m ? '#17796E' : '#3A4F52',
                fontSize: '0.875rem', fontWeight: mode === m ? 600 : 400, cursor: 'pointer',
              }}>
              {m === 'patients' ? 'ðŸ‘¥ Patients' : 'ðŸ§‘ Me'}
            </button>
          ))}
        </div>

        <div style={{ display: 'flex', gap: '12px', marginBottom: '16px', alignItems: 'center' }}>
          <span style={{ color: '#6E837A', fontSize: '0.8125rem' }}>ðŸ“… Filter by date:</span>
          <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)}
            style={{ padding: '6px 10px', fontSize: '0.8rem', background: '#FFFFFF', border: '1px solid #D9E7E3', borderRadius: '6px', color: '#7E948C' }} />
          <span style={{ color: '#90A79F', fontSize: '0.75rem' }}>to</span>
          <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)}
            style={{ padding: '6px 10px', fontSize: '0.8rem', background: '#FFFFFF', border: '1px solid #D9E7E3', borderRadius: '6px', color: '#7E948C' }} />
          {(dateFrom || dateTo) && (
            <button onClick={() => { setDateFrom(''); setDateTo('') }}
              style={{ padding: '6px 12px', fontSize: '0.75rem', background: '#FFFFFF', border: '1px solid #D9E7E3', borderRadius: '6px', color: '#6E837A', cursor: 'pointer' }}>
              Clear
            </button>
          )}
        </div>

        {mode === 'patients' ? (
          <>
            {patients.length === 0 ? (
              <div style={{ color: '#6E837A', fontSize: '0.8125rem' }}>No patients assigned.</div>
            ) : (
              <>
                <div style={{ fontSize: '0.8125rem', color: '#7C9188', fontWeight: 600, marginBottom: '8px' }}>Select a patient</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '16px' }}>
                  {patients.map((p: any) => (
                    <button key={p.username || p} onClick={() => setSelectedPatient(p.username || p)}
                      style={{
                        padding: '8px 16px', borderRadius: '8px', border: `1px solid ${selectedPatient === (p.username || p) ? '#17796E' : '#D9E7E3'}`,
                        background: selectedPatient === (p.username || p) ? '#E3F1EE' : '#FFFFFF',
                        color: selectedPatient === (p.username || p) ? '#17796E' : '#3A4F52', fontSize: '0.8125rem', cursor: 'pointer',
                      }}>
                      {p.name || p.username || p}
                    </button>
                  ))}
                </div>

                {selectedPatient && (
                  <>
                    <h3 style={{ fontSize: '0.9rem', margin: '0 0 8px 0', color: '#17796E' }}>
                      {patients.find((p: any) => (p.username || p) === selectedPatient)?.name || selectedPatient}
                    </h3>

                    <div style={{ fontSize: '0.8125rem', color: '#7C9188', fontWeight: 600, marginBottom: '8px' }}>Journal Entries {dateFrom || dateTo ? `(${filteredEntries.length} shown)` : ''}</div>
                    {filteredEntries.length === 0 ? (
                      <div style={{ color: '#6E837A', fontSize: '0.8125rem', marginBottom: '16px' }}>No journal entries.</div>
                    ) : (
                      entries.map((e: any, i: number) => {
                        const key = `j_${selectedPatient}_${i}`
                        const open = expandedEntries[key]
                        const ts = e.timestamp ? new Date(e.timestamp).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : ''
                        return (
                          <div key={key} style={{ marginBottom: '6px' }}>
                            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                              <button onClick={() => toggleExpand(setExpandedEntries, key)}
                                style={{
                                  flex: 1, padding: '6px 10px', background: '#FFFFFF',
                                  border: '1px solid #D9E7E3', borderRadius: '6px',
                                  color: '#3A4F52', fontSize: '0.8125rem', cursor: 'pointer', textAlign: 'left',
                                }}>
                                ðŸ“„ {ts} {open ? 'â–²' : 'â–¼'}
                              </button>
                              <button onClick={() => downloadCsv(`${selectedPatient}_journal_${i}.csv`, [['Timestamp', 'Summary'], [ts, e.summary || '']])}
                                style={{ padding: '6px 10px', background: '#FFFFFF', border: '1px solid #D9E7E3', borderRadius: '6px', color: '#7C9188', cursor: 'pointer', fontSize: '0.75rem' }}>
                                â¬‡
                              </button>
                            </div>
                            {open && (
                              <div style={{ background: '#F4F9F8', border: '1px solid #D9E7E3', borderRadius: '8px', padding: '12px', margin: '4px 0 0 0' }}>
                                <div style={{ color: '#3A4F52', fontSize: '0.8125rem', lineHeight: 1.6 }}>{e.summary}</div>
                                {e.emotions && <div style={{ color: '#6E837A', fontSize: '0.6875rem', marginTop: '4px' }}>Emotions: {e.emotions}</div>}
                              </div>
                            )}
                          </div>
                        )
                      })
                    )}

                    {filteredNotes.length > 0 && (
                      <>
                        <div style={{ fontSize: '0.8125rem', color: '#7C9188', fontWeight: 600, margin: '12px 0 8px 0' }}>Clinical Notes {dateFrom || dateTo ? `(${filteredNotes.length} shown)` : ''}</div>
                        {filteredNotes.map((n: any, i: number) => {
                          const key = `c_${selectedPatient}_${i}`
                          const open = expandedNotes[key]
                          const ts = n.timestamp ? new Date(n.timestamp).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : ''
                          return (
                            <div key={key} style={{ marginBottom: '6px' }}>
                              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                <button onClick={() => toggleExpand(setExpandedNotes, key)}
                                  style={{
                                    flex: 1, padding: '6px 10px', background: '#FFFFFF',
                                    border: '1px solid #D9E7E3', borderRadius: '6px',
                                    color: '#3A4F52', fontSize: '0.8125rem', cursor: 'pointer', textAlign: 'left',
                                  }}>
                                  ðŸ“‹ {ts} {open ? 'â–²' : 'â–¼'}
                                </button>
                                <button onClick={() => downloadCsv(`${selectedPatient}_clinical_${i}.csv`, [['Timestamp', 'Note'], [ts, n.ai_synthesis || n.raw_notes || '']])}
                                  style={{ padding: '6px 10px', background: '#FFFFFF', border: '1px solid #D9E7E3', borderRadius: '6px', color: '#7C9188', cursor: 'pointer', fontSize: '0.75rem' }}>
                                  â¬‡
                                </button>
                              </div>
                              {open && (
                                <div style={{ background: '#F4F9F8', border: '1px solid #D9E7E3', borderRadius: '8px', padding: '12px', margin: '4px 0 0 0' }}>
                                  <div style={{ color: '#3A4F52', fontSize: '0.8125rem', lineHeight: 1.6 }}>{n.ai_synthesis || n.raw_notes}</div>
                                </div>
                              )}
                            </div>
                          )
                        })}
                      </>
                    )}
                  </>
                )}
              </>
            )}
          </>
        ) : (
          <div>
            <div style={{ fontSize: '0.8125rem', color: '#7C9188', fontWeight: 600, marginBottom: '12px' }}>My Journal Entries {dateFrom || dateTo ? `(${filteredOwn.length} shown)` : ''}</div>
            {filteredOwn.length === 0 ? (
              <div style={{ color: '#6E837A', fontSize: '0.8125rem' }}>No journal entries yet.</div>
            ) : (
              filteredOwn.map((e: any, i: number) => {
                const key = `j_self_${i}`
                const open = expandedEntries[key]
                const ts = e.timestamp ? new Date(e.timestamp).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : ''
                return (
                  <div key={key} style={{ marginBottom: '6px' }}>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <button onClick={() => toggleExpand(setExpandedEntries, key)}
                        style={{
                          flex: 1, padding: '6px 10px', background: '#FFFFFF',
                          border: '1px solid #D9E7E3', borderRadius: '6px',
                          color: '#3A4F52', fontSize: '0.8125rem', cursor: 'pointer', textAlign: 'left',
                        }}>
                        ðŸ“„ {ts} {open ? 'â–²' : 'â–¼'}
                      </button>
                      <button onClick={() => downloadCsv(`journal_${i}.csv`, [['Timestamp', 'Summary'], [ts, e.summary || '']])}
                        style={{ padding: '6px 10px', background: '#FFFFFF', border: '1px solid #D9E7E3', borderRadius: '6px', color: '#7C9188', cursor: 'pointer', fontSize: '0.75rem' }}>
                        â¬‡
                      </button>
                    </div>
                    {open && (
                      <div style={{ background: '#F4F9F8', border: '1px solid #D9E7E3', borderRadius: '8px', padding: '12px', margin: '4px 0 0 0' }}>
                        <div style={{ color: '#3A4F52', fontSize: '0.8125rem', lineHeight: 1.6 }}>{e.summary}</div>
                        {e.emotions && <div style={{ color: '#6E837A', fontSize: '0.6875rem', marginTop: '4px' }}>Emotions: {e.emotions}</div>}
                      </div>
                    )}
                  </div>
                )
              })
            )}
          </div>
        )}
      </div>
    </div>
  )
}