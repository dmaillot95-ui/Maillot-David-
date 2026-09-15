import fs from 'node:fs/promises';
import path from 'node:path';
import { runMultifractal } from '../cerebron/multifractal/core.mjs';
import { createGeminiInfer } from '../cerebron/multifractal/provider-gemini.mjs';

const missionPath = process.env.CEREBRON_MISSION_FILE || 'cerebron/missions/current.json';
const outputDir = process.env.CEREBRON_OUTPUT_DIR || 'cerebron/results';

const raw = await fs.readFile(missionPath, 'utf8');
const missionConfig = JSON.parse(raw);

if (missionConfig.enabled === false) {
  console.log('CEREBRON_MISSION_DISABLED');
  process.exit(0);
}

if (!missionConfig.mission || !String(missionConfig.mission).trim()) {
  throw new Error('MISSION_REQUIRED');
}

const infer = createGeminiInfer({
  model: missionConfig.model || process.env.GEMINI_MODEL || 'gemini-3.1-flash-lite'
});

console.log(JSON.stringify({
  event: 'CEREBRON_START',
  missionId: missionConfig.id || null,
  agentCount: missionConfig.agentCount || 20,
  swarmSize: missionConfig.swarmSize || 10,
  concurrency: missionConfig.concurrency || 3,
  model: missionConfig.model || process.env.GEMINI_MODEL || 'gemini-3.1-flash-lite'
}));

const result = await runMultifractal({
  mission: missionConfig.mission,
  agentCount: missionConfig.agentCount || 20,
  swarmSize: missionConfig.swarmSize || 10,
  concurrency: missionConfig.concurrency || 3,
  infer,
  onProgress: (p) => console.log(JSON.stringify({ event: 'PROGRESS', ...p }))
});

await fs.mkdir(outputDir, { recursive: true });
const safeId = String(missionConfig.id || new Date().toISOString()).replace(/[^a-zA-Z0-9_.-]+/g, '_');
const stampedPath = path.join(outputDir, `${safeId}.json`);
const latestPath = path.join(outputDir, 'latest.json');
const payload = JSON.stringify({ missionConfig, result }, null, 2);
await fs.writeFile(stampedPath, payload, 'utf8');
await fs.writeFile(latestPath, payload, 'utf8');

console.log('CEREBRON_FINAL_BEGIN');
console.log(result.final);
console.log('CEREBRON_FINAL_END');
console.log(JSON.stringify({ event: 'CEREBRON_DONE', metrics: result.metrics, resultFile: stampedPath }));
