import { mutateConfig, evaluateCandidate, buildAuditRecord } from './evolution.js';
import { loadBenchmarkSuite, runBenchmarkConfig } from './benchmark.js';

const KEY = 'cerebron_evolution_lab_v1';

function readState() {
  try { return JSON.parse(localStorage.getItem(KEY)) || { history: [] }; }
  catch { return { history: [] }; }
}

function writeState(state) {
  localStorage.setItem(KEY, JSON.stringify(state));
}

export async function loadBaseConfig() {
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
    timestamp: new Date().toISOString(),
    baselineConfig,
    candidateConfig,
    baselineRuns,
    candidateRuns,
    evaluation,
    audit
  };

  const state = readState();
  state.active = record;
  state.history.unshift(record);
  state.history = state.history.slice(0, 20);
  writeState(state);
  return record;
}

export function getLabState() {
  return readState();
}
