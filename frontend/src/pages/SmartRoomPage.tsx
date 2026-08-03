import { useState } from 'react'

export default function SmartRoomPage() {
  const [calm, setCalm] = useState(true)

  return (
    <div className="animate-fade-in space-y-6" style={{ textAlign: 'center' }}>
      <h1>🧠 Smart Room</h1>

      <button
        onClick={() => setCalm(!calm)}
        className="btn-primary"
        style={{ maxWidth: '200px', margin: '0 auto', padding: '10px 24px' }}
      >
        {calm ? '⚡ Intense Mode' : '🌙 Calm Mode'}
      </button>

      <div style={{ display: 'flex', justifyContent: 'center', padding: '20px' }}>
        {calm ? <CalmMode /> : <IntenseMode />}
      </div>

      <p style={{ color: '#6a6474', fontSize: '0.8125rem' }}>Smart room responds to emotional state</p>
    </div>
  )
}

function CalmMode() {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{
        width: '180px', height: '180px', borderRadius: '50%', margin: '0 auto',
        background: 'radial-gradient(circle at 35% 35%, #ffd700, #b8860b)',
        boxShadow: '0 0 80px rgba(255,215,0,0.25), 0 0 160px rgba(255,215,0,0.08)',
        transition: 'all 0.5s ease',
      }} />
      <div style={{ marginTop: '16px' }}>
        <div style={{ color: '#e8e4ec', fontSize: '1.1rem', fontWeight: 600 }}>Calming Mode</div>
        <div style={{ color: '#6a6474', fontSize: '0.8rem', marginTop: '4px' }}>Ambient lighting — Low stimulus — Relaxed atmosphere</div>
      </div>
      <div style={{ display: 'flex', gap: '24px', justifyContent: 'center', marginTop: '24px' }}>
        <div style={{ color: '#5a4a5a', fontSize: '0.75rem' }}>💧 Humidifier</div>
        <div style={{ color: '#5a4a5a', fontSize: '0.75rem' }}>🔊 Sound scan</div>
        <div style={{ color: '#5a4a5a', fontSize: '0.75rem' }}>📡 Full sensor array</div>
      </div>
    </div>
  )
}

function IntenseMode() {
  return (
    <div style={{ textAlign: 'center', position: 'relative' }}>
      {[200, 250, 300].map((size, i) => (
        <div key={i} style={{
          position: 'absolute', top: '50%', left: '50%',
          width: `${size}px`, height: `${size}px`,
          marginLeft: `-${size / 2}px`, marginTop: `-${size / 2}px`,
          borderRadius: '50%',
          border: `1px solid rgba(0,100,255,${0.15 - i * 0.04})`,
          animation: i === 0 ? 'pulseRing 3s infinite' : 'none',
        }} />
      ))}
      <div style={{
        width: '150px', height: '150px', borderRadius: '50%', margin: '75px auto',
        background: 'radial-gradient(circle at 35% 35%, #5599ff, #0033aa)',
        boxShadow: '0 0 60px rgba(0,100,255,0.3), 0 0 120px rgba(0,100,255,0.08)',
        transition: 'all 0.5s ease',
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px',
      }}>
        {[38, 48, 52, 58, 65, 58, 48].map((h, i) => (
          <div key={i} style={{
            width: '4px', height: `${h}px`,
            background: 'rgba(255,255,255,0.7)',
            borderRadius: '2px',
            animation: `barGrow 0.8s ease-out ${i * 0.1}s`,
          }} />
        ))}
      </div>
      <div style={{ marginTop: '180px' }}>
        <div style={{ color: '#e8e4ec', fontSize: '1.1rem', fontWeight: 600 }}>Focused Mode</div>
        <div style={{ color: '#6a6474', fontSize: '0.8rem', marginTop: '4px' }}>Active monitoring — Diffuser engaged — High awareness</div>
      </div>
      <div style={{ display: 'flex', gap: '24px', justifyContent: 'center', marginTop: '24px' }}>
        <div style={{ color: '#5a4a5a', fontSize: '0.75rem' }}>💧 Humidifier active</div>
        <div style={{ color: '#5a4a5a', fontSize: '0.75rem' }}>🔊 Sound scan running</div>
        <div style={{ color: '#5a4a5a', fontSize: '0.75rem' }}>📡 Array online</div>
      </div>
    </div>
  )
}
