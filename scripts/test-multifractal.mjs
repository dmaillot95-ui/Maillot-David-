import assert from 'node:assert/strict';
import { buildMultifractalPlan, runMultifractal } from '../cerebron/multifractal/core.mjs';

const plan = buildMultifractalPlan({ mission: 'Test de topologie', agentCount: 20, swarmSize: 10 });
assert.equal(plan.agentCount, 20);
assert.equal(plan.swarmCount, 2);
assert.equal(plan.agents.length, 20);
assert.equal(new Set(plan.agents.map((a) => a.id)).size, 20);

let calls = 0;
const fakeInfer = async (system, user, meta) => {
  calls += 1;
  if (meta.phase === 'leaf') return `RESULTAT ${meta.agent.id}\nEVIDENCE TEST\nUNKNOWN NONE\nNEXT TEST`; 
  if (meta.phase === 'swarm') return `SYNTHESIS S${meta.swarmIndex + 1}: ROBUSTE TEST`;
  if (meta.phase === 'root') return 'DECISION: KEEP — SELFTEST';
  return 'UNKNOWN';
};

const result = await runMultifractal({
  mission: 'Mission déterministe de validation du moteur',
  agentCount: 20,
  swarmSize: 10,
  concurrency: 4,
  infer: fakeInfer
});

assert.equal(result.metrics.requestedLeaves, 20);
assert.equal(result.metrics.successfulLeaves, 20);
assert.equal(result.metrics.failedLeaves, 0);
assert.equal(result.metrics.successfulSwarms, 2);
assert.equal(result.metrics.modelCallsPlanned, 23);
assert.equal(calls, 23);
assert.match(result.final, /KEEP/);

console.log(JSON.stringify({
  status: 'PASS',
  topology: result.plan.topology,
  calls,
  final: result.final
}, null, 2));
