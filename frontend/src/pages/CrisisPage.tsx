import { useEffect, useState, useRef, useCallback } from 'react'
import { api } from '../api/client'
import { getUser } from '../stores/auth'
import { computeCrisisStage, CRISIS_STAGES, CRISIS_STAGE_MESSAGES } from '../constants'

function playAlertAudio() {
  try {
    const ctx = new (window.AudioContext || (window as any).webkitAudioContext)()
    const d = 1.5
    const sr = ctx.sampleRate
    const len = sr * d
    const buf = ctx.createBuffer(1, len, sr)
    const ch = buf.getChannelData(0)
    for (let i = 0; i < len; i++) {
      const t = i / sr
      const sweep = 440 + 220 * Math.sin(2 * Math.PI * 3 * t)
      const pulse = 0.4 + 0.3 * Math.sin(2 * Math.PI * 2 * t)
      ch[i] = pulse * Math.sin(2 * Math.PI * sweep * t) * 0.5
    }
    const src = ctx.createBufferSource()
    src.buffer = buf
    src.loop = true
    src.connect(ctx.destination)
    src.start()
    return () => { try { src.stop(); ctx.close() } catch {} }
  } catch { return () => {} }
}

export default function CrisisPage() {
  const user = getUser()
  const [cs, setCs] = useState<any>({})
  const [elapsed, setElapsed] = useState(0)
  const [loading, setLoading] = useState(true)
  const [cancelling, setCancelling] = useState(false)
  const [error, setError] = useState('')
  const intervalRef = useRef<any>(null)
  const stopAudioRef = useRef<(() => void) | null>(null)
  const prevActiveRef = useRef(false)

  async function load() {
    try {
      const [state, el] = await Promise.all([
        api.getCrisisState(),
        api.getCrisisElapsed()
      ])
      setCs(state || {})
      setElapsed(el?.elapsed || 0)
    } catch {}
    setLoading(false)
  }

  useEffect(() => {
    load()
    intervalRef.current = setInterval(load, 3000)
    return () => clearInterval(intervalRef.current)
  }, [])

  useEffect(() => {
    if (cs.active && !prevActiveRef.current) {
      stopAudioRef.current = playAlertAudio()
    } else if (!cs.active && prevActiveRef.current) {
      if (stopAudioRef.current) { stopAudioRef.current(); stopAudioRef.current = null }
    }
    prevActiveRef.current = cs.active
    return () => {
      if (stopAudioRef.current) { stopAudioRef.current(); stopAudioRef.current = null }
    }
  }, [cs.active])

  useEffect(() => {
    if (cs.active) {
      const tick = setInterval(() => setElapsed(e => e + 1), 1000)
      return () => clearInterval(tick)
    }
  }, [cs.active])

  const isPsych = user?.role === 'psychologist'
  const active = cs.active
  const triggeredBy = cs.triggered_by || 'patient'

  const stage = computeCrisisStage(cs, elapsed)

  const terminal = stage === 'acknowledged'

  async function trigger() {
    try { await api.triggerCrisis(); await load() } catch (err: any) { alert(err.message) }
  }

  async function handleCancel() {
    setCancelling(true)
    setError('')
    try { await api.resolveCrisis(); await load() } catch (e: any) { setError('Failed to cancel crisis. Please try again.') }
    setCancelling(false)
  }

  async function handleResolve() {
    setCancelling(true)
    setError('')
    try { await api.resolveCrisis(); await load() } catch (e: any) { setError('Failed to resolve crisis. Please try again.') }
    setCancelling(false)
  }

  async function acknowledge() {
    setError('')
    try { await api.acknowledgeCrisis(); await load() } catch (e: any) { setError('Failed to acknowledge. Please try again.') }
  }

  async function notifyTC() {
    setError('')
    try { await api.notifyTrustedContact(); await load() } catch (e: any) { setError('Failed to notify. Please try again.') }
  }

  if (loading) return <div className="animate-fade-in"><h2>ðŸš¨ Emergency</h2><div className="card"><span style={{ color: '#6E837A' }}>Loading...</span></div></div>

  const displayTime = elapsed >= 60 ? '60+' : String(elapsed)

  const stages = CRISIS_STAGES

  function stageStyle(key: string) {
    const isActive = key === stage || (terminal && ['helpline_escalated', 'acknowledged'].includes(stage) && key === 'helpline_escalated')
    const found = stages.find(s => s.key === key)
    const passed = found ? elapsed >= found.sec : false
    if (isActive) return { color: '#C7463B', background: 'rgba(199,70,59,0.15)', border: '1px solid rgba(199,70,59,0.4)' }
    if (passed) return { color: '#2E8B57', background: 'rgba(46,139,87,0.12)', border: '1px solid rgba(46,139,87,0.3)' }
    return { color: '#90A79F', background: 'rgba(232,242,240,0.6)', border: '1px solid #DFECE8' }
  }

  const helplineNumber = 'ðŸ“ž National Helpline: 988 (Suicide & Crisis Lifeline)'

  return (
    <div className="animate-fade-in">
      <h2>ðŸš¨ Emergency</h2>

      <div style={{ background: '#EAF3FC', border: '1px solid rgba(59,130,246,0.3)', borderRadius: '8px', padding: '8px 14px', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span style={{ fontSize: '1.1rem' }}>ðŸ“ž</span>
        <span style={{ color: '#2E7DB8', fontSize: '0.875rem', fontWeight: 600 }}>
          {helplineNumber}
        </span>
        <span style={{ color: '#5F7A70', fontSize: '0.75rem', marginLeft: 'auto' }}>24/7 â€” Free & Confidential</span>
      </div>

      {!active ? (
        <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
          {isPsych ? (
            <button onClick={trigger} className="btn-primary" style={{ flex: 1, padding: '14px', fontSize: '1rem', background: 'linear-gradient(135deg, #C7463B, #dc2626)' }}>
              ðŸ”¥ Trigger Crisis for Patient
            </button>
          ) : (
            <button onClick={trigger} className="btn-primary" style={{ flex: 1, padding: '14px', fontSize: '1rem', background: 'linear-gradient(135deg, #C7463B, #dc2626)' }}>
              ðŸ”¥ Crisis? I need help now
            </button>
          )}
        </div>
      ) : (
        <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {error && (
            <div style={{ background: 'rgba(199,70,59,0.1)', border: '1px solid rgba(199,70,59,0.3)', borderRadius: '8px', padding: '10px 14px', color: '#B5453D', fontSize: '0.8125rem' }}>
              {error}
            </div>
          )}
          {triggeredBy === 'psychologist' && (
            <div className="card" style={{ borderColor: '#C7463B', color: '#B5453D' }}>
              <strong>ðŸ”´ Crisis triggered by your psychologist</strong> â€” Elevated vitals detected + journal analysis indicated high risk.
            </div>
          )}
          {stage === 'acknowledged' && (
            <div style={{ color: CRISIS_STAGE_MESSAGES.acknowledged.color, fontWeight: 600 }}><strong>{CRISIS_STAGE_MESSAGES.acknowledged.text}</strong></div>
          )}
          {stage === 'helpline_escalated' && (
            <div className="card" style={{ borderColor: '#C7463B', color: '#C7463B' }}>
              <strong>{CRISIS_STAGE_MESSAGES.helpline_escalated.text}</strong>
            </div>
          )}
          {['trustee_coming', 'trustee_clicked'].includes(stage) && (
            <div style={{ color: '#B7791A' }}><strong>{CRISIS_STAGE_MESSAGES[stage].text}</strong></div>
          )}
          {!terminal && stage !== 'helpline_escalated' && triggeredBy !== 'psychologist' && (
            <div className="card" style={{ borderColor: '#C7463B', color: '#B5453D' }}>
              <strong>âš ï¸ You are in crisis and need of help.</strong>
            </div>
          )}

          <div className="card-dark" style={{ padding: '12px', borderColor: '#DFECE8' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
              <span style={{ color: '#B5453D', fontSize: '1.125rem' }}>â±ï¸ Timer</span>
              <span style={{ color: '#20363C', fontSize: '1.25rem', fontWeight: 700 }}>{displayTime}s</span>
              <span style={{ color: '#5F7A70', fontSize: '0.8125rem' }}>elapsed</span>
              <div style={{ marginLeft: 'auto' }}>
                {stage === 'helpline_escalated' && <span style={{ color: '#C7463B', fontWeight: 600, fontSize: '0.8125rem' }}>Helpline contacted</span>}
                {stage === 'trustee_coming' && <span style={{ color: '#2FA05C', fontWeight: 600, fontSize: '0.8125rem' }}>Trusted contact on the way</span>}
                {stage === 'trustee_clicked' && <span style={{ color: '#35A36A', fontWeight: 600, fontSize: '0.8125rem' }}>Trusted contact notified</span>}
                {stage === 'acknowledged' && <span style={{ color: '#2FA05C', fontWeight: 600, fontSize: '0.8125rem' }}>Psychologist acknowledged</span>}
              </div>
            </div>
            <div style={{ display: 'flex' }}>
              {stages.map(s => {
                const ss = stageStyle(s.key)
                return (
                  <div key={s.key} style={{ flex: 1, textAlign: 'center', padding: '8px', margin: '0 4px', borderRadius: '8px', background: ss.background, border: ss.border, color: ss.color, fontSize: '0.8125rem', fontWeight: 600 }}>
                    {s.label}<br /><span style={{ fontSize: '0.6875rem', fontWeight: 400 }}>{s.sec}s</span>
                  </div>
                )
              })}
            </div>
          </div>

          {triggeredBy === 'patient' && !terminal && (
            <button onClick={handleCancel} disabled={cancelling} className="btn-primary" style={{ padding: '12px', background: '#B5453D', border: '1px solid #C7463B' }}>
              {cancelling ? 'Cancelling...' : 'âœ… Cancel Crisis'}
            </button>
          )}
          {isPsych && !terminal && (
            <button onClick={handleResolve} disabled={cancelling} className="btn-primary" style={{ padding: '12px', background: '#2E8B57', border: '1px solid #2E8B57' }}>
              {cancelling ? 'Resolving...' : 'ðŸ—‘ Resolve Crisis'}
            </button>
          )}
          {triggeredBy === 'psychologist' && !isPsych && (
            <div style={{ color: '#6E837A', fontSize: '0.8125rem' }}>âš ï¸ This crisis was triggered by your psychologist. Only they can resolve it.</div>
          )}

          <div style={{ display: 'flex', gap: '8px' }}>
            {!cs.acknowledged && isPsych && (
              <button onClick={acknowledge} className="btn-primary" style={{ flex: 1, padding: '10px' }}>âœ“ Acknowledge Crisis</button>
            )}
            {triggeredBy === 'patient' && (
              <button onClick={notifyTC} style={{ flex: 1, padding: '10px' }}>ðŸ‘¤ Notify Trusted Contact</button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
