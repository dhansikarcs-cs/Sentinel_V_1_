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

  if (loading) return <div className="animate-fade-in"><h2>🚨 Emergency</h2><div className="card"><span style={{ color: '#6a6474' }}>Loading...</span></div></div>

  const displayTime = elapsed >= 60 ? '60+' : String(elapsed)

  const stages = CRISIS_STAGES

  function stageStyle(key: string) {
    const isActive = key === stage || (terminal && ['helpline_escalated', 'acknowledged'].includes(stage) && key === 'helpline_escalated')
    const found = stages.find(s => s.key === key)
    const passed = found ? elapsed >= found.sec : false
    if (isActive) return { color: '#ef4444', background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.4)' }
    if (passed) return { color: '#22c55e', background: 'rgba(34,197,94,0.12)', border: '1px solid rgba(34,197,94,0.3)' }
    return { color: '#3a4a5a', background: 'rgba(26,34,56,0.6)', border: '1px solid #1e2940' }
  }

  const helplineNumber = '📞 National Helpline: 988 (Suicide & Crisis Lifeline)'

  return (
    <div className="animate-fade-in">
      <h2>🚨 Emergency</h2>

      <div style={{ background: '#1a2844', border: '1px solid rgba(59,130,246,0.3)', borderRadius: '8px', padding: '8px 14px', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span style={{ fontSize: '1.1rem' }}>📞</span>
        <span style={{ color: '#93bbfc', fontSize: '0.875rem', fontWeight: 600 }}>
          {helplineNumber}
        </span>
        <span style={{ color: '#5a7aaa', fontSize: '0.75rem', marginLeft: 'auto' }}>24/7 — Free & Confidential</span>
      </div>

      {!active ? (
        <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
          {isPsych ? (
            <button onClick={trigger} className="btn-primary" style={{ flex: 1, padding: '14px', fontSize: '1rem', background: 'linear-gradient(135deg, #ef4444, #dc2626)' }}>
              🔥 Trigger Crisis for Patient
            </button>
          ) : (
            <button onClick={trigger} className="btn-primary" style={{ flex: 1, padding: '14px', fontSize: '1rem', background: 'linear-gradient(135deg, #ef4444, #dc2626)' }}>
              🔥 Crisis? I need help now
            </button>
          )}
        </div>
      ) : (
        <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {error && (
            <div style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: '8px', padding: '10px 14px', color: '#fca5a5', fontSize: '0.8125rem' }}>
              {error}
            </div>
          )}
          {triggeredBy === 'psychologist' && (
            <div className="card" style={{ borderColor: '#ef4444', color: '#fca5a5' }}>
              <strong>🔴 Crisis triggered by your psychologist</strong> — Elevated vitals detected + journal analysis indicated high risk.
            </div>
          )}
          {stage === 'acknowledged' && (
            <div style={{ color: CRISIS_STAGE_MESSAGES.acknowledged.color, fontWeight: 600 }}><strong>{CRISIS_STAGE_MESSAGES.acknowledged.text}</strong></div>
          )}
          {stage === 'helpline_escalated' && (
            <div className="card" style={{ borderColor: '#ef4444', color: '#f87171' }}>
              <strong>{CRISIS_STAGE_MESSAGES.helpline_escalated.text}</strong>
            </div>
          )}
          {['trustee_coming', 'trustee_clicked'].includes(stage) && (
            <div style={{ color: '#f59e0b' }}><strong>{CRISIS_STAGE_MESSAGES[stage].text}</strong></div>
          )}
          {!terminal && stage !== 'helpline_escalated' && triggeredBy !== 'psychologist' && (
            <div className="card" style={{ borderColor: '#ef4444', color: '#fca5a5' }}>
              <strong>⚠️ You are in crisis and need of help.</strong>
            </div>
          )}

          <div className="card-dark" style={{ padding: '12px', borderColor: '#1e2940' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
              <span style={{ color: '#fca5a5', fontSize: '1.125rem' }}>⏱️ Timer</span>
              <span style={{ color: '#f0f4ff', fontSize: '1.25rem', fontWeight: 700 }}>{displayTime}s</span>
              <span style={{ color: '#7a8aaa', fontSize: '0.8125rem' }}>elapsed</span>
              <div style={{ marginLeft: 'auto' }}>
                {stage === 'helpline_escalated' && <span style={{ color: '#f87171', fontWeight: 600, fontSize: '0.8125rem' }}>Helpline contacted</span>}
                {stage === 'trustee_coming' && <span style={{ color: '#4ade80', fontWeight: 600, fontSize: '0.8125rem' }}>Trusted contact on the way</span>}
                {stage === 'trustee_clicked' && <span style={{ color: '#6ee7a7', fontWeight: 600, fontSize: '0.8125rem' }}>Trusted contact notified</span>}
                {stage === 'acknowledged' && <span style={{ color: '#4ade80', fontWeight: 600, fontSize: '0.8125rem' }}>Psychologist acknowledged</span>}
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
            <button onClick={handleCancel} disabled={cancelling} className="btn-primary" style={{ padding: '12px', background: '#6b2020', border: '1px solid #ef4444' }}>
              {cancelling ? 'Cancelling...' : '✅ Cancel Crisis'}
            </button>
          )}
          {isPsych && !terminal && (
            <button onClick={handleResolve} disabled={cancelling} className="btn-primary" style={{ padding: '12px', background: '#1b4a1b', border: '1px solid #22c55e' }}>
              {cancelling ? 'Resolving...' : '🗑 Resolve Crisis'}
            </button>
          )}
          {triggeredBy === 'psychologist' && !isPsych && (
            <div style={{ color: '#6a6474', fontSize: '0.8125rem' }}>⚠️ This crisis was triggered by your psychologist. Only they can resolve it.</div>
          )}

          <div style={{ display: 'flex', gap: '8px' }}>
            {!cs.acknowledged && isPsych && (
              <button onClick={acknowledge} className="btn-primary" style={{ flex: 1, padding: '10px' }}>✓ Acknowledge Crisis</button>
            )}
            {triggeredBy === 'patient' && (
              <button onClick={notifyTC} style={{ flex: 1, padding: '10px' }}>👤 Notify Trusted Contact</button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
