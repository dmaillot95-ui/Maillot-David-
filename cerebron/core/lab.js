import { mutateConfig, evaluateCandidate, buildAuditRecord, aggregateRuns } from './evolution.js';
import { loadBenchmarkSuite, runBenchmarkConfig } from './benchmark.js';

const KEY = 'cerebron_evolution_lab_v1';

function readState() {
  try { return JSON.parse(localStorage.getItem(KEY)) || { history: [] }; }
  catch { return { history: [] }; }
}

function writeState(state) {
  localStorage.setItem(KEY, JSON.stringify(state));
}

function saveRecord(record) {
  const state = readState();
  state.active = record;
  state.history = (state.history || []).filter((r) => r.cycleId !== record.cycleId);
  state.history.unshift(record);
  state.history = state.history.slice(0, 20);
  writeState(state);
  return record;
}

export async function loadBaseConfig() {
  const state = readState();
  if (state.promoted) return structuredClone(state.promoted);
  const res = await fetch('./cerebron/config/default.json', { cache: 'no-store' });
  if (!res.ok) throw new Error(`Config introuvable: ${res.status}`);
  return res.json();
}

export function proposeCandidate(baseConfig) {
  return mutateConfig(baseConfig);
}

export async function runABCycle({ baselineConfig, candidateConfig, inferFn, mode = 'quick', onProgress }) {
  const suite = await loadBenchmarkSuite();
  const repetitions = mode === 'full' ? 3 : 1;
  const agentsPerCase = mode === 'full' ? 6 : 2;

  const baselineRuns = await runBenchmarkConfig({
    config: baselineConfig,
    suite,
    inferFn,
    repetitions,
    agentsPerCase,
    onProgress: (p) => onProgress?.({ side: 'BASELINE', ...p })
  });

  const candidateRuns = await runBenchmarkConfig({
    config: candidateConfig,
    suite,
    inferFn,
    repetitions,
    agentsPerCase,
    onProgress: (p) => onProgress?.({ side: 'CANDIDATE', ...p })
  });

  const evaluation = evaluateCandidate({
    baselineRuns,
    candidateRuns,
    config: baselineConfig,
    ablationPassed: false,
    redTeamPassed: false
  });

  const audit = buildAuditRecord({
    baselineConfig,
    candidateConfig,
    evaluation,
    benchmarkId: suite.id
  });
  audit.mode = mode;
  audit.ablation = 'NOT_EXECUTED';
  audit.redTeam = 'NOT_EXECUTED';

  const record = {
    cycleId: `EV-${Date.now()}`,
    timestamp: new Date().toISOString(),
    baselineConfig,
    candidateConfig,
    baselineRuns,
    candidateRuns,
    evaluation,
    ablation: null,
    redTeam: null,
    audit
  };

  return saveRecord(record);
}

function uniqueMutationKeys(record) {
  return [...new Set((record?.candidateConfig?.mutations || []).map((m) => m.key).filter(Boolean))];
}

export async function runAblationGate({ record, inferFn, onProgress }) {
  if (!record?.candidateConfig || !record?.baselineConfig) throw new Error('Cycle A/B absent.');
  const keys = uniqueMutationKeys(record);
  if (!keys.length) {
    record.ablation = { status: 'FAILED', passed: false, reason: 'Aucune mutation identifiable.' };
    record.audit.ablation = 'FAILED';
    return saveRecord(record);
  }

  const suite = await loadBenchmarkSuite();
  const repetitions = 1;
  const agentsPerCase = 2;
  const controlRuns = await runBenchmarkConfig({
    config: record.candidateConfig,
    suite,
    inferFn,
    repetitions,
    agentsPerCase,
    onProgress: (p) => onProgress?.({ side: 'ABLATION_CONTROL', ...p })
  });
  const control = aggregateRuns(controlRuns, record.baselineConfig.scoring);
  const variants = [];

  for (const key of keys) {
    const variant = structuredClone(record.candidateConfig);
    variant.weights[key] = record.baselineConfig.weights[key];
    variant.version = `${record.candidateConfig.version}-ABLATE-${key}`;
    const runs = await runBenchmarkConfig({
      config: variant,
      suite,
      inferFn,
      repetitions,
      agentsPerCase,
      onProgress: (p) => onProgress?.({ side: `ABLATE_${key}`, ...p })
    });
    const summary = aggregateRuns(runs, record.baselineConfig.scoring);
    const contribution = Number.isFinite(control.globalScore) && Number.isFinite(summary.globalScore)
      ? control.globalScore - summary.globalScore
      : null;
    variants.push({ key, revertedTo: record.baselineConfig.weights[key], summary, contribution });
  }

  const minimumContribution = 0.001;
  const valid = variants.every((v) => Number.isFinite(v.contribution));
  const allUseful = valid && variants.every((v) => v.contribution >= minimumContribution);
  record.ablation = {
    status: allUseful ? 'PASSED' : 'FAILED',
    passed: allUseful,
    minimumContribution,
    control,
    variants,
    note: 'Ablation interne sur le même modèle local et les mêmes cas; elle mesure la contribution logicielle, pas une preuve scientifique indépendante.'
  };
  record.audit.ablation = record.ablation.status;
  return saveRecord(record);
}

function compactRunSummary(record) {
  const baseline = aggregateRuns(record.baselineRuns, record.baselineConfig.scoring);
  const candidate = aggregateRuns(record.candidateRuns, record.baselineConfig.scoring);
  return {
    baseline: { score: baseline.globalScore, metrics: baseline.metricMeans, repetitions: baseline.repetitions },
    candidate: { score: candidate.globalScore, metrics: candidate.metricMeans, repetitions: candidate.repetitions },
    mutations: record.candidateConfig.mutations || [],
    ablation: record.ablation ? {
      status: record.ablation.status,
      variants: (record.ablation.variants || []).map((v) => ({ key: v.key, contribution: v.contribution }))
    } : null
  };
}

export async function runInternalRedTeamGate({ record, inferFn }) {
  if (!record?.candidateRuns?.length) throw new Error('Benchmark A/B absent.');
  const payload = JSON.stringify(compactRunSummary(record), null, 2);
  const system = `Tu es la Red Team INTERNE de CEREBRON OMEGA. Tu n'es PAS une preuve independante: meme modele possible, meme environnement. Cherche uniquement des raisons logicielles de bloquer la promotion: regression cachee, score fragile, mutation inutile, manque de repetitions, metrique non couverte, surinterpretation. Reponds exactement avec une premiere ligne VERDICT: PASS, VERDICT: HOLD ou VERDICT: REJECT, puis justification concise.`;
  const text = await inferFn(system, `AUDIT DU CANDIDAT:\n${payload}`, 520, 0.0);
  const match = String(text).match(/VERDICT\s*:\s*(PASS|HOLD|REJECT)/i);
  const verdict = match ? match[1].toUpperCase() : 'HOLD';
  const passed = verdict === 'PASS';
  record.redTeam = {
    status: passed ? 'PASSED' : verdict,
    passed,
    verdict,
    text,
    independence: 'INTERNAL_MODEL_RED_TEAM_NOT_INDEPENDENT'
  };
  record.audit.redTeam = record.redTeam.status;
  return saveRecord(record);
}

export function finalizeGates(record) {
  if (!record) throw new Error('Cycle absent.');
  const evaluation = evaluateCandidate({
    baselineRuns: record.baselineRuns,
    candidateRuns: record.candidateRuns,
    config: record.baselineConfig,
    ablationPassed: Boolean(record.ablation?.passed),
    redTeamPassed: Boolean(record.redTeam?.passed)
  });
  record.evaluation = evaluation;
  record.audit = {
    ...buildAuditRecord({
      baselineConfig: record.baselineConfig,
      candidateConfig: record.candidateConfig,
      evaluation,
      benchmarkId: record.audit?.benchmarkId || 'CEREBRON-BENCH-V1'
    }),
    mode: record.audit?.mode || 'unknown',
    ablation: record.ablation?.status || 'NOT_EXECUTED',
    redTeam: record.redTeam?.status || 'NOT_EXECUTED'
  };
  return saveRecord(record);
}

export function promoteCandidate(record) {
  if (!record?.evaluation || record.evaluation.decision !== 'PROMOTE') {
    return { promoted: false, reason: 'PROMOTION INTERDITE: benchmark/gates insuffisants.' };
  }
  const state = readState();
  state.promoted = structuredClone(record.candidateConfig);
  state.promotedAt = new Date().toISOString();
  state.active = record;
  writeState(state);
  return { promoted: true, config: state.promoted, promotedAt: state.promotedAt };
}

export function getLabState() {
  return readState();
}
