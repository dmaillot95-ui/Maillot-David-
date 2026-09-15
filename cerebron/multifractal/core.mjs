const ROOT_RULES = `
CÉRÉBRON Ω — règles racines
REALITY > COHERENCE
EVIDENCE > CONFIDENCE
CLAIM <= EVIDENCE
SIMULATION != TEST
UNKNOWN REMAINS UNKNOWN
VERIFY BEFORE COMMIT
Ne jamais inventer source, calcul, test ou résultat.
Marquer FACT / HYPOTHESIS / UNKNOWN / CONTRADICTION / NOT EXECUTED.
`;

export const BASE_ROLES = [
  'Recherche & sources',
  'Benchmark & prior art',
  'Physique & calculs',
  'Architecture système',
  'Modèles & simulations',
  'Invention & différenciation',
  'IP & risques',
  'Industrialisation',
  'Red Team',
  'Audit Evidence'
];

export const FRACTAL_LENSES = [
  'voie directe indépendante',
  'contre-exemples et falsification',
  'formalisation minimale',
  'sensibilité aux hypothèses',
  'transfert vers cas voisins',
  'réduction par ablation',
  'vérification arithmétique ou numérique',
  'audit des dépendances et causalités',
  'recherche de mécanisme nouveau',
  'preuve la plus courte et testable',
  'approche constructive',
  'approche adversariale'
];

function clampInt(value, min, max, fallback) {
  const n = Number(value);
  return Number.isFinite(n) ? Math.max(min, Math.min(max, Math.trunc(n))) : fallback;
}

export function buildMultifractalPlan({ mission, agentCount = 20, swarmSize = 10 } = {}) {
  if (!mission || !String(mission).trim()) throw new Error('Mission requise.');
  agentCount = clampInt(agentCount, 1, 120, 20);
  swarmSize = clampInt(swarmSize, 1, 10, 10);
  const swarmCount = Math.ceil(agentCount / swarmSize);
  const agents = [];

  for (let i = 0; i < agentCount; i += 1) {
    const swarmIndex = Math.floor(i / swarmSize);
    const role = BASE_ROLES[i % BASE_ROLES.length];
    const lens = FRACTAL_LENSES[(i * 7 + swarmIndex * 3) % FRACTAL_LENSES.length];
    agents.push({
      id: `A${String(i + 1).padStart(3, '0')}`,
      index: i,
      swarmIndex,
      role,
      lens,
      independenceKey: `${role}::${lens}::S${swarmIndex + 1}`
    });
  }

  return {
    mission: String(mission).trim(),
    agentCount,
    swarmSize,
    swarmCount,
    agents,
    topology: `ROOT(1) -> SWARMS(${swarmCount}) -> AGENTS(${agentCount})`
  };
}

function agentPrompt(plan, agent) {
  return {
    system: `${ROOT_RULES}\nTu es ${agent.id}, agent feuille d'une ferme multifractale.\nRôle: ${agent.role}.\nLentille: ${agent.lens}.\nTravaille indépendamment; ne suppose aucun consensus.`,
    user: `MISSION GLOBALE:\n${plan.mission}\n\nProduis uniquement ton axe. Structure obligatoire:\n1. RESULTAT\n2. EVIDENCE\n3. HYPOTHESES\n4. CONTRADICTIONS\n5. UNKNOWN\n6. NEXT TEST\n7. CONFIDENCE [0..1] avec justification.\nTout claim doit rester <= à son evidence.`
  };
}

function swarmPrompt(plan, swarmIndex, results) {
  const payload = results.map((r) => `### ${r.agent.id} — ${r.agent.role} — ${r.agent.lens}\n${r.text}`).join('\n\n');
  return {
    system: `${ROOT_RULES}\nTu es le coordinateur du sous-essaim S${swarmIndex + 1}. Tu dois fusionner sans compter des sorties du même modèle comme preuves indépendantes.`,
    user: `MISSION:\n${plan.mission}\n\nRÉSULTATS FEUILLES:\n${payload}\n\nRetourne:\nROBUSTE / PLAUSIBLE / REJETE / CONTRADICTOIRE / OUVERT, puis les claims, preuves, inconnues, erreurs et prochains tests. Cite les IDs d'agents.`
  };
}

function rootPrompt(plan, swarmSummaries) {
  const payload = swarmSummaries.map((s) => `### ESSAIM S${s.swarmIndex + 1}\n${s.text}`).join('\n\n=====\n\n');
  return {
    system: `${ROOT_RULES}\nTu es le Méta-Coordinateur CÉRÉBRON Ω. Tu arbitres les synthèses de sous-essaims. Consensus != preuve.`,
    user: `MISSION:\n${plan.mission}\n\nSYNTHÈSES MULTIFRACTALES:\n${payload}\n\nProduis la décision finale avec:\n- CLAIM REGISTER\n- EVIDENCE MAP\n- CONTRADICTIONS\n- UNKNOWN CRITIQUES\n- RESULTATS REJETES\n- PROCHAIN TEST DISCRIMINANT\n- DECISION: KEEP / NARROW / HOLD / KILL / SCALE.`
  };
}

async function mapLimit(items, limit, fn, onProgress) {
  const output = new Array(items.length);
  let cursor = 0;
  let finished = 0;
  const workers = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (true) {
      const idx = cursor++;
      if (idx >= items.length) return;
      try {
        output[idx] = await fn(items[idx], idx);
      } catch (error) {
        output[idx] = { error: String(error?.message || error) };
      }
      finished += 1;
      onProgress?.({ finished, total: items.length, index: idx });
    }
  });
  await Promise.all(workers);
  return output;
}

export async function runMultifractal({
  mission,
  agentCount = 20,
  swarmSize = 10,
  concurrency = 4,
  infer,
  onProgress
} = {}) {
  if (typeof infer !== 'function') throw new Error('infer(system,user,meta) requis.');
  const plan = buildMultifractalPlan({ mission, agentCount, swarmSize });
  concurrency = clampInt(concurrency, 1, 20, 4);
  const startedAt = new Date().toISOString();

  const leafRaw = await mapLimit(plan.agents, concurrency, async (agent) => {
    const p = agentPrompt(plan, agent);
    const text = await infer(p.system, p.user, { phase: 'leaf', agent, plan });
    return { agent, status: 'done', text: String(text || '').trim() };
  }, (p) => onProgress?.({ phase: 'leaf', ...p }));

  const leaves = leafRaw.map((item, i) => item?.error
    ? { agent: plan.agents[i], status: 'error', text: '', error: item.error }
    : item);

  const swarmSummaries = [];
  for (let s = 0; s < plan.swarmCount; s += 1) {
    const members = leaves.filter((r) => r.agent.swarmIndex === s);
    const usable = members.filter((r) => r.status === 'done');
    if (!usable.length) {
      swarmSummaries.push({ swarmIndex: s, status: 'error', text: 'Aucun agent feuille réussi.' });
      continue;
    }
    const p = swarmPrompt(plan, s, usable);
    try {
      const text = await infer(p.system, p.user, { phase: 'swarm', swarmIndex: s, plan });
      swarmSummaries.push({ swarmIndex: s, status: 'done', text: String(text || '').trim() });
    } catch (error) {
      swarmSummaries.push({ swarmIndex: s, status: 'error', text: String(error?.message || error) });
    }
    onProgress?.({ phase: 'swarm', finished: s + 1, total: plan.swarmCount, index: s });
  }

  const usableSwarms = swarmSummaries.filter((s) => s.status === 'done');
  let final;
  if (!usableSwarms.length) {
    final = 'FUSION IMPOSSIBLE: aucun sous-essaim réussi.';
  } else {
    const p = rootPrompt(plan, usableSwarms);
    final = await infer(p.system, p.user, { phase: 'root', plan });
  }

  return {
    version: 'CEREBRON-MF-1.0',
    startedAt,
    finishedAt: new Date().toISOString(),
    plan,
    leaves,
    swarmSummaries,
    final: String(final || '').trim(),
    metrics: {
      requestedLeaves: plan.agentCount,
      successfulLeaves: leaves.filter((r) => r.status === 'done').length,
      failedLeaves: leaves.filter((r) => r.status === 'error').length,
      successfulSwarms: usableSwarms.length,
      modelCallsPlanned: plan.agentCount + plan.swarmCount + 1
    }
  };
}
