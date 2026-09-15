import { normalizeWeights } from './evolution.js';

const ROLE_PROMPTS = {
  research: 'Recherche et verifie les faits. Distingue FACT, HYPOTHESIS et UNKNOWN.',
  benchmark: 'Compare a des alternatives et cherche les limites ou precedents pertinents.',
  physics: 'Controle calculs, unites, ordres de grandeur et reproductibilite.',
  architecture: 'Analyse architecture, interfaces, dependances et trade-offs.',
  simulation: 'Distingue modele, simulation executee, test physique et limites de validation.',
  invention: 'Cherche une solution differenciee mais falsifiable, sans inventer de preuve.',
  ip: 'Analyse nouveaute potentielle, prior art et zones non demontrees.',
  industrialization: 'Analyse transfert, fabrication, maintenance, couts et dependances.',
  red_team: 'Cherche activement erreurs, contradictions, surclaims et causes d echec.',
  evidence_audit: 'Applique CLAIM <= EVIDENCE et exige une prochaine preuve discriminante.'
};

function hash01(text) {
  let h = 2166136261;
  for (let i = 0; i < text.length; i += 1) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return ((h >>> 0) % 1000000) / 1000000;
}

function chooseRole(weights, seed) {
  const normalized = normalizeWeights(weights || {});
  const entries = Object.entries(normalized);
  if (!entries.length) return 'evidence_audit';
  const r = hash01(seed);
  let acc = 0;
  for (const [role, w] of entries) {
    acc += w;
    if (r <= acc) return role;
  }
  return entries.at(-1)[0];
}

function fractionPresent(text, terms = []) {
  if (!terms.length) return 1;
  const hay = String(text || '').toLowerCase();
  let n = 0;
  for (const term of terms) if (hay.includes(String(term).toLowerCase())) n += 1;
  return n / terms.length;
}

function scoreOutput(text, testCase) {
  const s = String(text || '');
  const len = s.length;
  const termScore = fractionPresent(s, testCase.required_terms || []);
  const markerScore = fractionPresent(s, testCase.required_markers || []);
  const hasUnknown = /UNKNOWN|inconnu|incertain/i.test(s);
  const hasTest = /NEXT TEST|test|essai|verification/i.test(s);
  const hasEvidence = /EVIDENCE|preuve|source|calcu/i.test(s);
  const hasPassFail = /PASS|FAIL|falsifi/i.test(s);
  const reasonableLength = len >= 120 && len <= 2400 ? 1 : len > 0 ? 0.5 : 0;
  const noFakeExecution = !/simulation executee|test execute|mesure effectuee/i.test(s) || /source|resultat|valeur|fichier/i.test(s);

  return {
    accuracy: termScore,
    evidence_quality: Math.min(1, (markerScore + (hasEvidence ? 1 : 0)) / 2),
    reproducibility: Math.min(1, (termScore + (hasEvidence ? 1 : 0)) / 2),
    falsifiability: hasPassFail ? 1 : hasTest ? 0.75 : 0.25,
    efficiency: reasonableLength,
    novelty: 0.5,
    transfer: /NEXT TEST|prochaine action|fichier|transfert|livrable/i.test(s) ? 1 : 0.4,
    safety: noFakeExecution && (hasUnknown || /non|pas|limite/i.test(s)) ? 1 : 0.65
  };
}

function averageMetrics(items) {
  const keys = [...new Set(items.flatMap((x) => Object.keys(x || {})))];
  const out = {};
  for (const key of keys) {
    const values = items.map((x) => Number(x?.[key])).filter(Number.isFinite);
    if (values.length) out[key] = values.reduce((a, b) => a + b, 0) / values.length;
  }
  return out;
}

export async function loadBenchmarkSuite(url = './cerebron/benchmarks/suite-v1.json') {
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) throw new Error(`Benchmark introuvable: ${res.status}`);
  return res.json();
}

export async function runBenchmarkConfig({ config, suite, inferFn, repetitions = 1, agentsPerCase = 4, onProgress }) {
  if (typeof inferFn !== 'function') throw new Error('inferFn manquant');
  const runs = [];

  for (let rep = 0; rep < repetitions; rep += 1) {
    const scored = [];
    const raw = [];

    for (let c = 0; c < suite.cases.length; c += 1) {
      const testCase = suite.cases[c];
      for (let a = 0; a < agentsPerCase; a += 1) {
        const seed = `${suite.id}|${rep}|${testCase.id}|${a}`;
        const role = chooseRole(config.weights, seed);
        const system = `Tu es un agent CEREBRON OMEGA en benchmark controle.\nRôle: ${ROLE_PROMPTS[role] || role}\nRegles: CLAIM <= EVIDENCE; UNKNOWN REMAINS UNKNOWN; ne jamais inventer un test ou une source executee.\nTermine par CONCLUSION, EVIDENCE, UNKNOWN, NEXT TEST.`;
        const user = `CAS BENCHMARK ${testCase.id}:\n${testCase.prompt}`;
        let text = '';
        let status = 'EXECUTED';
        try {
          text = await inferFn(system, user, 340);
        } catch (error) {
          status = 'ERROR';
          text = String(error?.message || error);
        }
        const metrics = status === 'EXECUTED' ? scoreOutput(text, testCase) : {};
        if (status === 'EXECUTED') scored.push(metrics);
        raw.push({ testCase: testCase.id, role, status, metrics, text });
        onProgress?.({ rep, caseIndex: c, agentIndex: a, testCase: testCase.id, role, status });
      }
    }

    runs.push({
      status: scored.length ? 'EXECUTED' : 'ERROR',
      repetition: rep + 1,
      metrics: averageMetrics(scored),
      details: raw
    });
  }

  return runs;
}
