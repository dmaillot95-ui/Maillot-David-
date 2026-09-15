const DEFAULT_ROLES = [
  'Recherche & sources',
  'Benchmark & prior art',
  'Physique & calculs',
  'Architecture systeme',
  'Modeles & simulations',
  'Invention & differenciation',
  'IP & risques',
  'Industrialisation',
  'Red Team',
  'Audit evidence'
]

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value))
}

async function callProvider({ role, mission }) {
  const base = process.env.CEREBRON_API_BASE
  const key = process.env.CEREBRON_API_KEY
  const model = process.env.CEREBRON_MODEL || 'local-model'

  if (!base) {
    return {
      status: 'NOT_EXECUTED',
      role,
      reason: 'CEREBRON_API_BASE non configure',
      planned_prompt: `ROLE: ${role}\nMISSION: ${mission}`
    }
  }

  const url = `${base.replace(/\/$/, '')}/chat/completions`
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(key ? { Authorization: `Bearer ${key}` } : {})
    },
    body: JSON.stringify({
      model,
      messages: [
        {
          role: 'system',
          content: `Tu es l'agent ${role} de CEREBRON OMEGA. Ne presente jamais comme execute ce qui ne l'est pas. Distingue FACT, HYPOTHESIS, UNKNOWN et CONTRADICTION.`
        },
        { role: 'user', content: mission }
      ],
      temperature: 0.2
    })
  })

  if (!response.ok) {
    return {
      status: 'ERROR',
      role,
      http_status: response.status,
      error: await response.text()
    }
  }

  const data = await response.json()
  return {
    status: 'EXECUTED',
    role,
    output: data?.choices?.[0]?.message?.content ?? null
  }
}

export async function POST(request) {
  try {
    const body = await request.json()
    const mission = String(body?.mission || '').trim()
    const requestedAgents = clamp(Number(body?.agents || 10), 1, 100)

    if (!mission) {
      return Response.json({ ok: false, error: 'Mission vide' }, { status: 400 })
    }

    const maxConcurrency = clamp(Number(process.env.CEREBRON_MAX_CONCURRENCY || 4), 1, 20)
    const tasks = Array.from({ length: requestedAgents }, (_, i) => ({
      id: i + 1,
      role: DEFAULT_ROLES[i % DEFAULT_ROLES.length]
    }))

    const results = new Array(tasks.length)
    let cursor = 0

    async function worker() {
      while (true) {
        const index = cursor++
        if (index >= tasks.length) return
        const task = tasks[index]
        results[index] = await callProvider({ role: task.role, mission })
      }
    }

    const workers = Array.from(
      { length: Math.min(maxConcurrency, tasks.length) },
      () => worker()
    )
    await Promise.all(workers)

    const executed = results.filter(r => r?.status === 'EXECUTED').length
    const errors = results.filter(r => r?.status === 'ERROR').length
    const notExecuted = results.filter(r => r?.status === 'NOT_EXECUTED').length

    return Response.json({
      ok: true,
      mission,
      requested_agents: requestedAgents,
      max_concurrency: maxConcurrency,
      executed_agents: executed,
      failed_agents: errors,
      not_executed_agents: notExecuted,
      provider_configured: Boolean(process.env.CEREBRON_API_BASE),
      results
    })
  } catch (error) {
    return Response.json({ ok: false, error: String(error) }, { status: 500 })
  }
}
