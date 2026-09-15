import { loadBaseConfig, proposeCandidate, runABCycle, getLabState } from './cerebron/core/lab.js';

const $ = (id) => document.getElementById(id);

const ROLE_TEMPLATES = [
  "Recherche & sources : faits, hypothèses, données manquantes, vérifiabilité.",
  "Benchmark & prior art : alternatives, antériorité, meilleures approches connues.",
  "Physique & calculs : équations, unités, ordres de grandeur, calculs reproductibles.",
  "Architecture système : sous-systèmes, interfaces, trade-offs, dépendances.",
  "Modèles & simulations : modèles nécessaires, scénarios, limites, tests numériques.",
  "Invention & différenciation : mécanismes nouveaux, effets techniques, tests discriminants.",
  "IP & risques : brevetabilité potentielle, prior art, design-around, points non démontrés.",
  "Industrialisation : fabrication, supply-chain, maintenance, coûts et contraintes.",
  "Red Team : chercher activement erreurs, contradictions, faux positifs et causes d'échec.",
  "Audit Evidence : CLAIM <= EVIDENCE, statut des preuves, inconnues et prochaine expérience."
];

const ROOT_RULES = `
Tu es un agent CÉRÉBRON Ω. Travaille uniquement sur la mission donnée.
Règles absolues : REALITY > COHERENCE ; EVIDENCE > CONFIDENCE ; CLAIM <= EVIDENCE ;
SIMULATION != TEST ; UNKNOWN REMAINS UNKNOWN ; ne jamais inventer source, calcul, résultat ou preuve.
Marque clairement FACT, HYPOTHESIS, UNKNOWN, CONTRADICTION et NOT EXECUTED lorsque nécessaire.
Réponse compacte, technique, actionnable, avec conclusions falsifiables.
`;

let webllm = null;
let engine = null;
let engineModel = null;
let stopRequested = false;
let activeCampaign = null;
let state = loadState();
let evoBaseline = null;
let evoCandidate = null;
let evoBusy = false;

function loadState() {
  try {
    return JSON.parse(localStorage.getItem("cerebron_state_v1")) || { campaigns: [], activeId: null };
  } catch {
    return { campaigns: [], activeId: null };
  }
}

function saveState() {
  localStorage.setItem("cerebron_state_v1", JSON.stringify(state));
}

function persistCampaign(campaign) {
  const idx = state.campaigns.findIndex((c) => c.id === campaign.id);
  if (idx >= 0) state.campaigns[idx] = campaign;
  else state.campaigns.unshift(campaign);
  state.campaigns = state.campaigns.slice(0, 12);
  state.activeId = campaign.id;
  saveState();
}

function getSavedActive() {
  return state.campaigns.find((c) => c.id === state.activeId) || state.campaigns[0] || null;
}

function makeId() {
  return `CΩ-${new Date().toISOString().replace(/[-:TZ.]/g, "").slice(0, 14)}-${Math.random().toString(36).slice(2, 6).toUpperCase()}`;
}

function escapeHtml(str = "") {
  return str.replace(/[&<>'"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[c]));
}

function updateUI(campaign = activeCampaign) {
  if (!campaign) {
    $("runStatus").textContent = "Inactif";
    return;
  }
  const done = campaign.results.filter((r) => r.status === "done").length;
  const errors = campaign.results.filter((r) => r.status === "error").length;
  const total = campaign.workerCount;
  const pct = total ? Math.round((done + errors) / total * 100) : 0;
  $("runStatus").textContent = campaign.status;
  $("doneCount").textContent = `${done}/${total}`;
  $("swarmCount").textContent = `${campaign.summaries.length}/${Math.ceil(total / campaign.groupSize)}`;
  $("errorCount").textContent = String(errors);
  $("runProgressBar").style.width = `${pct}%`;
  $("runProgressText").textContent = `${pct}% · ${done + errors} appels agents terminés`;
  $("campaignId").textContent = campaign.id;
  $("finalOutput").textContent = campaign.meta || campaign.summaries.at(-1)?.text || "Synthèse non encore produite.";

  $("results").innerHTML = campaign.results.map((r) => `
    <article class="result-card">
      <div class="result-head"><strong>Agent ${r.index + 1}</strong><span>${escapeHtml(r.role)}</span></div>
      <pre>${escapeHtml(r.text || r.error || r.status)}</pre>
    </article>
  `).join("");
}

async function ensureWebLLM() {
  if (!webllm) {
    webllm = await import("https://esm.run/@mlc-ai/web-llm");
  }
  return webllm;
}

async function populateModels() {
  const mod = await ensureWebLLM();
  const all = mod.prebuiltAppConfig?.model_list || [];
  const models = all.map((m) => m.model_id).filter(Boolean);
  const light = models.filter((id) => /(0\.5B|1B|1\.5B|2B|3B)/i.test(id));
  const ordered = [...new Set([...(light.length ? light : models.slice(0, 20)), ...models])];
  $("modelSelect").innerHTML = ordered.map((id) => `<option value="${escapeHtml(id)}">${escapeHtml(id)}</option>`).join("");

  const preferred = ordered.find((id) => /Llama-3\.2-1B-Instruct/i.test(id))
    || ordered.find((id) => /Qwen.*1\.5B.*Instruct/i.test(id))
    || ordered[0];
  if (preferred) $("modelSelect").value = preferred;
}

async function loadModel() {
  if (!navigator.gpu) throw new Error("WebGPU indisponible dans ce navigateur. Essaie Chrome/Edge récent sur le portable.");
  const mod = await ensureWebLLM();
  const modelId = $("modelSelect").value;
  if (!modelId) throw new Error("Aucun modèle disponible.");
  $("loadModelBtn").disabled = true;
  $("modelProgressText").textContent = "Chargement… le premier téléchargement peut être long.";
  try {
    engine = await mod.CreateMLCEngine(modelId, {
      initProgressCallback: (p) => {
        const frac = typeof p.progress === "number" ? p.progress : 0;
        $("modelProgressBar").style.width = `${Math.round(frac * 100)}%`;
        $("modelProgressText").textContent = p.text || `Chargement ${Math.round(frac * 100)}%`;
      }
    });
    engineModel = modelId;
    $("modelProgressBar").style.width = "100%";
    $("modelProgressText").textContent = `Prêt : ${modelId}`;
  } finally {
    $("loadModelBtn").disabled = false;
  }
}

async function infer(system, user, maxTokens = 420) {
  if (!engine) throw new Error("Charge d'abord un modèle local.");
  const out = await engine.chat.completions.create({
    messages: [
      { role: "system", content: system },
      { role: "user", content: user }
    ],
    temperature: 0.35,
    max_tokens: maxTokens
  });
  return out?.choices?.[0]?.message?.content?.trim() || "[AUCUN TEXTE RETOURNÉ]";
}

function clip(text, max = 1100) {
  if (!text) return "";
  return text.length > max ? `${text.slice(0, max)}\n[…tronqué…]` : text;
}

async function summarizeSwarm(campaign, swarmIndex, members) {
  const payload = members.map((r) => `AGENT ${r.index + 1} — ${r.role}\n${clip(r.text || r.error, 950)}`).join("\n\n---\n\n");
  const system = `${ROOT_RULES}\nTu es le coordinateur local de l'essaim ${swarmIndex + 1}. Fusionne sans transformer un consensus en preuve indépendante.`;
  const user = `MISSION GLOBALE:\n${campaign.mission}\n\nRÉSULTATS DE L'ESSAIM:\n${payload}\n\nProduis : résultats robustes, contradictions, inconnues, claims soutenus, claims rejetés, prochaines actions.`;
  return infer(system, user, Math.max(520, campaign.workerTokens));
}

async function finalFusion(campaign) {
  const payload = campaign.summaries.map((s, i) => `ESSAIM ${i + 1}\n${clip(s.text, 1600)}`).join("\n\n=====\n\n");
  const system = `${ROOT_RULES}\nTu es le Méta-Coordinateur CÉRÉBRON Ω. Les essaims ne comptent pas comme preuves indépendantes s'ils utilisent le même modèle ou les mêmes données.`;
  const user = `MISSION:\n${campaign.mission}\n\nSYNTHÈSES DES ESSAIMS:\n${payload}\n\nFais la synthèse finale : PROUVÉ/ROBUSTE/PLAUSIBLE/OUVERT/CONTRADICTOIRE, erreurs détectées, inconnues critiques, décision, prochain test discriminant.`;
  return infer(system, user, Math.max(700, campaign.workerTokens + 220));
}

async function runCampaign(campaign) {
  if (!engine) throw new Error("Charge d'abord le modèle local.");
  if (engineModel !== campaign.modelId) throw new Error(`Le modèle chargé (${engineModel}) ne correspond pas à la campagne (${campaign.modelId}).`);

  stopRequested = false;
  activeCampaign = campaign;
  campaign.status = "RUNNING";
  campaign.updatedAt = new Date().toISOString();
  $("startBtn").disabled = true;
  $("stopBtn").disabled = false;
  persistCampaign(campaign);
  updateUI(campaign);

  for (let i = 0; i < campaign.workerCount; i++) {
    if (stopRequested) break;
    const existing = campaign.results[i];
    if (existing?.status === "done") continue;

    const role = ROLE_TEMPLATES[i % ROLE_TEMPLATES.length];
    campaign.results[i] = { index: i, role, status: "running", text: "" };
    updateUI(campaign);
    persistCampaign(campaign);

    try {
      const system = `${ROOT_RULES}\nRÔLE SPÉCIFIQUE : ${role}\nTu es l'agent ${i + 1}/${campaign.workerCount}. Ton contexte est indépendant des autres agents.`;
      const user = `MISSION:\n${campaign.mission}\n\nTraite uniquement ton axe. Termine par : CONCLUSION, EVIDENCE, UNKNOWN, NEXT TEST.`;
      const text = await infer(system, user, campaign.workerTokens);
      campaign.results[i] = { index: i, role, status: "done", text };
    } catch (err) {
      campaign.results[i] = { index: i, role, status: "error", error: String(err?.message || err) };
    }

    campaign.updatedAt = new Date().toISOString();
    persistCampaign(campaign);
    updateUI(campaign);

    const endOfGroup = ((i + 1) % campaign.groupSize === 0) || i === campaign.workerCount - 1;
    if (endOfGroup && !stopRequested) {
      const swarmIndex = Math.floor(i / campaign.groupSize);
      if (!campaign.summaries[swarmIndex]) {
        const start = swarmIndex * campaign.groupSize;
        const members = campaign.results.slice(start, i + 1);
        try {
          const text = await summarizeSwarm(campaign, swarmIndex, members);
          campaign.summaries[swarmIndex] = { swarmIndex, status: "done", text };
        } catch (err) {
          campaign.summaries[swarmIndex] = { swarmIndex, status: "error", text: String(err?.message || err) };
        }
        persistCampaign(campaign);
        updateUI(campaign);
      }
    }
  }

  if (stopRequested) {
    campaign.status = "PAUSED";
  } else {
    campaign.status = "FUSION";
    persistCampaign(campaign);
    updateUI(campaign);
    try {
      campaign.meta = await finalFusion(campaign);
      campaign.status = "DONE";
    } catch (err) {
      campaign.meta = `ERREUR FUSION FINALE: ${String(err?.message || err)}`;
      campaign.status = "DONE_WITH_ERROR";
    }
  }

  campaign.updatedAt = new Date().toISOString();
  persistCampaign(campaign);
  updateUI(campaign);
  $("startBtn").disabled = false;
  $("stopBtn").disabled = true;
}

function newCampaign() {
  const mission = $("mission").value.trim();
  if (!mission) throw new Error("Entre une mission.");
  const workerCount = Math.max(1, Math.min(120, Number($("workerCount").value) || 10));
  const groupSize = Math.max(1, Math.min(10, Number($("groupSize").value) || 10));
  const workerTokens = Math.max(128, Math.min(1200, Number($("workerTokens").value) || 420));
  const modelId = $("modelSelect").value;
  return {
    id: makeId(), mission, workerCount, groupSize, workerTokens, modelId,
    status: "READY", results: [], summaries: [], meta: "",
    createdAt: new Date().toISOString(), updatedAt: new Date().toISOString()
  };
}

async function start() {
  try {
    const campaign = newCampaign();
    activeCampaign = campaign;
    persistCampaign(campaign);
    updateUI(campaign);
    await runCampaign(campaign);
  } catch (err) {
    alert(String(err?.message || err));
    $("startBtn").disabled = false;
    $("stopBtn").disabled = true;
  }
}

async function resume() {
  const campaign = getSavedActive();
  if (!campaign) return alert("Aucune campagne sauvegardée.");
  if (!engine) return alert("Charge d'abord le modèle utilisé par la campagne.");
  activeCampaign = campaign;
  $("mission").value = campaign.mission;
  $("workerCount").value = campaign.workerCount;
  $("groupSize").value = campaign.groupSize;
  $("workerTokens").value = campaign.workerTokens;
  if (["DONE", "DONE_WITH_ERROR"].includes(campaign.status)) return updateUI(campaign);
  await runCampaign(campaign);
}

function stop() {
  stopRequested = true;
  try { engine?.interruptGenerate?.(); } catch {}
  if (activeCampaign) activeCampaign.status = "STOPPING";
  updateUI(activeCampaign);
}

function exportState() {
  const data = JSON.stringify(activeCampaign || state, null, 2);
  const blob = new Blob([data], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${activeCampaign?.id || "cerebron-state"}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

function clearMemory() {
  if (!confirm("Effacer les campagnes CÉRÉBRON sauvegardées dans ce navigateur ?")) return;
  localStorage.removeItem("cerebron_state_v1");
  state = { campaigns: [], activeId: null };
  activeCampaign = null;
  $("results").innerHTML = "";
  $("finalOutput").textContent = "Aucun résultat.";
  $("runProgressBar").style.width = "0%";
  $("runProgressText").textContent = "Aucune campagne active";
  $("campaignId").textContent = "—";
  $("doneCount").textContent = "0";
  $("swarmCount").textContent = "0";
  $("errorCount").textContent = "0";
  $("runStatus").textContent = "Inactif";
}

function renderCandidate() {
  if (!evoCandidate) {
    $("evoMutation").textContent = "—";
    return;
  }
  $("evoGeneration").textContent = `G${evoCandidate.generation ?? 0}`;
  $("evoMutation").textContent = JSON.stringify(evoCandidate.mutations || [], null, 2);
}

async function evoInit() {
  evoBaseline = await loadBaseConfig();
  evoCandidate = null;
  $("evoGeneration").textContent = `G${evoBaseline.generation ?? 0}`;
  $("evoMutation").textContent = "Baseline chargée. Propose un candidat.";
  $("evoDecision").textContent = "NOT EXECUTED";
  $("evoAudit").textContent = "Aucun audit.";
  $("evoProgressBar").style.width = "0%";
  $("evoProgressText").textContent = `Baseline ${evoBaseline.version}`;
}

function evoMutate() {
  if (!evoBaseline) throw new Error("Charge d'abord la baseline.");
  evoCandidate = proposeCandidate(evoBaseline);
  renderCandidate();
  $("evoDecision").textContent = "CANDIDATE READY — benchmark requis";
}

async function evoRun(mode) {
  if (evoBusy) return;
  if (!engine) throw new Error("Charge d'abord un modèle local.");
  if (!evoBaseline) await evoInit();
  if (!evoCandidate) evoMutate();

  evoBusy = true;
  const total = mode === 'full' ? 216 : 24;
  let done = 0;
  $("evoQuickBtn").disabled = true;
  $("evoFullBtn").disabled = true;
  $("evoDecision").textContent = "RUNNING";
  $("evoProgressBar").style.width = "0%";

  try {
    const record = await runABCycle({
      baselineConfig: evoBaseline,
      candidateConfig: evoCandidate,
      inferFn: infer,
      mode,
      onProgress: (p) => {
        done += 1;
        const pct = Math.min(100, Math.round(done / total * 100));
        $("evoProgressBar").style.width = `${pct}%`;
        $("evoProgressText").textContent = `${p.side} · ${p.testCase} · ${done}/${total}`;
      }
    });

    const ev = record.evaluation;
    const gain = Number.isFinite(ev?.gain) ? `${(ev.gain * 100).toFixed(2)}%` : "n/a";
    $("evoDecision").textContent = `${ev?.decision || 'HOLD'}\n${ev?.reason || ''}\nGain: ${gain}\nAblation: NOT EXECUTED\nRed Team: NOT EXECUTED`;
    $("evoAudit").textContent = JSON.stringify(record.audit, null, 2);
    $("evoProgressBar").style.width = "100%";
    $("evoProgressText").textContent = `Benchmark ${mode} terminé · décision ${ev?.decision || 'HOLD'}`;
  } finally {
    evoBusy = false;
    $("evoQuickBtn").disabled = false;
    $("evoFullBtn").disabled = false;
  }
}

function restoreEvolutionView() {
  const lab = getLabState();
  const record = lab?.active;
  if (!record) return;
  evoBaseline = record.baselineConfig || null;
  evoCandidate = record.candidateConfig || null;
  renderCandidate();
  const ev = record.evaluation || {};
  const gain = Number.isFinite(ev.gain) ? `${(ev.gain * 100).toFixed(2)}%` : "n/a";
  $("evoDecision").textContent = `${ev.decision || 'HOLD'}\n${ev.reason || ''}\nGain: ${gain}`;
  $("evoAudit").textContent = JSON.stringify(record.audit || {}, null, 2);
  $("evoProgressText").textContent = "Dernier cycle restauré depuis la mémoire locale";
}

function wire() {
  $("loadModelBtn").addEventListener("click", () => loadModel().catch((e) => alert(e.message)));
  $("refreshModelsBtn").addEventListener("click", () => populateModels().catch((e) => alert(e.message)));
  $("startBtn").addEventListener("click", start);
  $("stopBtn").addEventListener("click", stop);
  $("resumeBtn").addEventListener("click", () => resume().catch((e) => alert(e.message)));
  $("exportBtn").addEventListener("click", exportState);
  $("clearBtn").addEventListener("click", clearMemory);
  $("evoInitBtn").addEventListener("click", () => evoInit().catch((e) => alert(e.message)));
  $("evoMutateBtn").addEventListener("click", () => { try { evoMutate(); } catch (e) { alert(e.message); } });
  $("evoQuickBtn").addEventListener("click", () => evoRun('quick').catch((e) => alert(e.message)));
  $("evoFullBtn").addEventListener("click", () => evoRun('full').catch((e) => alert(e.message)));
  document.querySelectorAll("[data-count]").forEach((b) => b.addEventListener("click", () => $("workerCount").value = b.dataset.count));
}

async function init() {
  $("webgpuStatus").textContent = navigator.gpu ? "WebGPU disponible" : "WebGPU indisponible";
  $("webgpuStatus").classList.toggle("bad", !navigator.gpu);
  wire();
  restoreEvolutionView();
  try {
    await populateModels();
  } catch (e) {
    $("modelProgressText").textContent = `Erreur chargement WebLLM : ${e.message}`;
  }
  const saved = getSavedActive();
  if (saved) {
    activeCampaign = saved;
    $("mission").value = saved.mission || "";
    $("workerCount").value = saved.workerCount || 10;
    $("groupSize").value = saved.groupSize || 10;
    $("workerTokens").value = saved.workerTokens || 420;
    if ([...$("modelSelect").options].some((o) => o.value === saved.modelId)) $("modelSelect").value = saved.modelId;
    updateUI(saved);
  }
}

init();
