'use client'

import { useState } from 'react'

const roles = [
  'Recherche', 'Benchmark', 'Physique & calculs', 'Architecture',
  'Modeles & simulations', 'Invention', 'IP & prior art',
  'Industrialisation', 'Red Team', 'Audit evidence'
]

export default function Home() {
  const [mission, setMission] = useState('')
  const [agents, setAgents] = useState(10)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  async function runMission() {
    setLoading(true)
    setResult(null)
    try {
      const response = await fetch('/api/orchestrate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mission, agents })
      })
      const data = await response.json()
      setResult(data)
    } catch (error) {
      setResult({ ok: false, error: String(error) })
    } finally {
      setLoading(false)
    }
  }

  return (
    <main style={{ maxWidth: 980, margin: '0 auto', padding: 24 }}>
      <h1 style={{ marginBottom: 6 }}>CEREBRON OMEGA</h1>
      <p style={{ marginTop: 0 }}>Orchestrateur multi-agents experimental</p>

      <section style={card}>
        <h2>Mission</h2>
        <textarea
          value={mission}
          onChange={e => setMission(e.target.value)}
          placeholder="Decris la mission a executer..."
          rows={7}
          style={{ width: '100%', padding: 12, boxSizing: 'border-box' }}
        />
        <div style={{ marginTop: 12 }}>
          <label>Agents logiques : </label>
          <input
            type="number"
            min="1"
            max="100"
            value={agents}
            onChange={e => setAgents(Number(e.target.value))}
            style={{ width: 90, padding: 8 }}
          />
        </div>
        <button
          onClick={runMission}
          disabled={loading || !mission.trim()}
          style={{ marginTop: 14, padding: '10px 16px', cursor: 'pointer' }}
        >
          {loading ? 'Execution...' : 'Lancer la mission'}
        </button>
      </section>

      <section style={card}>
        <h2>10 roles de base</h2>
        <ol>
          {roles.map(role => <li key={role}>{role}</li>)}
        </ol>
      </section>

      <section style={card}>
        <h2>Regles racines</h2>
        <pre style={{ whiteSpace: 'pre-wrap' }}>{`REALITY > COHERENCE\nEVIDENCE > CONFIDENCE\nCLAIM <= EVIDENCE\nSIMULATION != TEST\nUNKNOWN REMAINS UNKNOWN\nVERIFY BEFORE COMMIT`}</pre>
      </section>

      {result && (
        <section style={card}>
          <h2>Resultat</h2>
          <pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{JSON.stringify(result, null, 2)}</pre>
        </section>
      )}
    </main>
  )
}

const card = {
  background: '#fff',
  border: '1px solid #ddd',
  borderRadius: 12,
  padding: 18,
  marginTop: 18
}
