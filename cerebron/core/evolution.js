export function normalizeWeights(weights) {
  const entries = Object.entries(weights).map(([key, value]) => [key, Math.max(0, Number(value) || 0)]);
  const total = entries.reduce((sum, [, value]) => sum + value, 0) || 1;
  return Object.fromEntries(entries.map(([key, value]) => [key, value / total]));
}

export function allocateAgents(config, totalAgents) {
  const normalized = normalizeWeights(config.weights || {});
  const roles = Object.keys(normalized);
  if (!roles.length || totalAgents < 1) return {};

  const raw = roles.map((role) => ({
    role,
    exact: normalized[role] * totalAgents,
    count: Math.floor(normalized[role] * totalAgents)
  }));

  let assigned = raw.reduce((sum, item) => sum + item.count, 0);
  const remainder = totalAgents - assigned;
  raw.sort((a, b) => (b.exact - b.count) - (a.exact - a.count));
  for (let i = 0; i < remainder; i += 1) raw[i % raw.length].count += 1;

  return Object.fromEntries(raw.map(({ role, count }) => [role, count]));
}

export function mutateConfig(baseConfig, rng = Math.random) {
  const candidate = structuredClone(baseConfig);
  const limits = candidate.limits || {};
  const minWeight = limits.min_weight ?? 0.25;
  const maxWeight = limits.max_weight ?? 3.0;
  const step = limits.mutation_step ?? 0.15;
  const maxMutations = limits.max_mutations_per_candidate ?? 3;
  const keys = Object.keys(candidate.weights || {});
  if (!keys.length) return candidate;

  const mutationCount = 1 + Math.floor(rng() * Math.max(1, maxMutations));
  const changed = [];

  for (let i = 0; i < mutationCount; i += 1) {
    const key = keys[Math.floor(rng() * keys.length)];
    const direction = rng() < 0.5 ? -1 : 1;
    const before = candidate.weights[key];
    const after = Math.min(maxWeight, Math.max(minWeight, before + direction * step));
    candidate.weights[key] = Number(after.toFixed(4));
    changed.push({ key, before, after: candidate.weights[key] });
  }

  candidate.generation = (baseConfig.generation || 0) + 1;
  candidate.parent_version = baseConfig.version || null;
  candidate.version = `CEREBRON-ORCH-${candidate.generation}-${Date.now()}`;
  candidate.mutations = changed;
  return candidate;
}

export function weightedScore(metrics, scoring) {
  let numerator = 0;
  let denominator = 0;
  for (const [metric, weight] of Object.entries(scoring || {})) {
    const value = Number(metrics?.[metric]);
    if (!Number.isFinite(value)) continue;
    numerator += value * weight;
    denominator += weight;
  }
  return denominator ? numerator / denominator : 0;
}

export function aggregateRuns(runs, scoring) {
  const valid = (runs || []).filter((run) => run && run.status === 'EXECUTED');
  if (!valid.length) {
    return { repetitions: 0, globalScore: null, metricMeans: {}, status: 'NOT_EXECUTED' };
  }

  const metricKeys = [...new Set(valid.flatMap((run) => Object.keys(run.metrics || {})))];
  const metricMeans = {};
  for (const key of metricKeys) {
    const values = valid.map((run) => Number(run.metrics?.[key])).filter(Number.isFinite);
    if (values.length) metricMeans[key] = values.reduce((a, b) => a + b, 0) / values.length;
  }

  return {
    repetitions: valid.length,
    globalScore: weightedScore(metricMeans, scoring),
    metricMeans,
    status: 'EXECUTED'
  };
}

export function evaluateCandidate({ baselineRuns, candidateRuns, config, ablationPassed, redTeamPassed }) {
  const baseline = aggregateRuns(baselineRuns, config.scoring);
  const candidate = aggregateRuns(candidateRuns, config.scoring);
  const gate = config.promotion || {};

  if (baseline.status !== 'EXECUTED' || candidate.status !== 'EXECUTED') {
    return { decision: 'HOLD', reason: 'Benchmark non exécuté ou incomplet.', baseline, candidate };
  }

  if (candidate.repetitions < (gate.minimum_repetitions ?? 1)) {
    return { decision: 'HOLD', reason: 'Répétitions insuffisantes.', baseline, candidate };
  }

  const gain = candidate.globalScore - baseline.globalScore;
  const regressions = [];
  const maxRegression = gate.maximum_critical_regression ?? 0.02;
  for (const [metric, baselineValue] of Object.entries(baseline.metricMeans)) {
    const candidateValue = candidate.metricMeans[metric];
    if (!Number.isFinite(candidateValue)) continue;
    const delta = candidateValue - baselineValue;
    if (delta < -maxRegression) regressions.push({ metric, delta });
  }

  if (regressions.length) {
    return { decision: 'REJECT', reason: 'Régression critique détectée.', gain, regressions, baseline, candidate };
  }

  if ((gate.require_ablation ?? true) && !ablationPassed) {
    return { decision: 'HOLD', reason: 'Ablation non confirmée.', gain, baseline, candidate };
  }

  if ((gate.require_red_team ?? true) && !redTeamPassed) {
    return { decision: 'HOLD', reason: 'Red Team non validée.', gain, baseline, candidate };
  }

  if (gain >= (gate.minimum_global_gain ?? 0.03)) {
    return { decision: 'PROMOTE', reason: 'Gain mesuré au-dessus du seuil sans régression critique.', gain, baseline, candidate };
  }

  return { decision: 'KEEP', reason: 'Pas assez de gain pour promouvoir.', gain, baseline, candidate };
}

export function buildAuditRecord({ baselineConfig, candidateConfig, evaluation, benchmarkId }) {
  return {
    timestamp: new Date().toISOString(),
    benchmarkId,
    baselineVersion: baselineConfig?.version || null,
    candidateVersion: candidateConfig?.version || null,
    mutations: candidateConfig?.mutations || [],
    decision: evaluation?.decision || 'HOLD',
    reason: evaluation?.reason || 'UNKNOWN',
    gain: Number.isFinite(evaluation?.gain) ? evaluation.gain : null,
    regressions: evaluation?.regressions || [],
    evidence: {
      baselineRuns: evaluation?.baseline?.repetitions || 0,
      candidateRuns: evaluation?.candidate?.repetitions || 0
    }
  };
}
