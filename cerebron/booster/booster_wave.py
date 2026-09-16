#!/usr/bin/env python3
"""CEREBRON OMEGA — BOOSTER ZERO-EURO 432 research wave.

Generates a deterministic 432-task research campaign (36 shards x 12 tasks)
and executes each shard through the existing Worker Highway. This creates no
compute by itself: successful AI calls only count when a connected provider
actually returns a result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

TRIGGER_NONCE = "2026-09-16TBOOSTER-432-V1"

CORE = Path(__file__).resolve().parents[1] / "federation" / "core"
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))

import shard_worker  # noqa: E402
import worker_highway  # noqa: E402

MISSION_ID = "M-BOOST-ZERO-EURO-432"
MISSION = {
    "title": "BOOSTER ZERO-EURO OMEGA",
    "objective": (
        "Concevoir une infrastructure gratuite, legitime et auditable pour CEREBRON: "
        "site central, moteur d'orchestration, routeur multi-fournisseurs, calculateurs "
        "CPU/GPU/WebGPU/WASM, files d'attente, cache, stockage, self-hosted runners, "
        "edge/serverless, inference locale et connecteurs. Interdiction de contourner "
        "quotas, CGU ou facturation. Proposer code/tests/mesures et distinguer capacite "
        "logique, machine physique et inference IA reussie."
    ),
}

ROLES = list(shard_worker.ROLE_DIRECTIVES.keys())

THEMES = [
    "architecture du site central et API de controle",
    "routeur multi-fournisseurs zero-euro avec health scoring et circuit breakers",
    "ordonnancement de workers et work stealing sans doublons",
    "WebGPU navigateur pour calcul local cote client",
    "WebAssembly/WASI pour kernels de calcul portables",
    "calcul CPU distribue sur machines self-hosted autorisees",
    "GPU locaux ou gratuits legitimement accessibles",
    "GitHub Actions comme control plane et calcul deterministe",
    "self-hosted runners: enrollement, heartbeat, securite et autoscaling",
    "edge/serverless gratuit et limites de quotas",
    "stockage objet/KV gratuit avec preuves d'integrite",
    "file de messages gratuite ou embarquee",
    "cache de resultats et deduplication de prompts/calculs",
    "P2P/WebRTC volontaire entre navigateurs pour calcul cooperatif",
    "inference locale navigateur via petits modeles",
    "inference locale desktop CPU/GPU",
    "fournisseurs LLM gratuits legitimement connectables",
    "decouverte dynamique de modeles et provider registry",
    "backoff adaptatif et repartition de quota",
    "micro-batching et batching dynamique",
    "priorisation Evidence>Confidence",
    "pipeline claims/evidence/unknowns/contradictions",
    "audit reproductible des sorties d'agents",
    "federation de farms de calcul heterogenes",
    "protocoles de leasing de taches et anti-double-execution",
    "securite des tokens et secrets sans exposition aux workers",
    "sandboxing des calculateurs non fiables",
    "observabilite: traces, metriques, cout reel et taux de succes",
    "mode offline-first et reprise apres coupure",
    "base de donnees gratuite ou embarquee",
    "event sourcing et journal immuable",
    "compression des contextes et economie de tokens",
    "memoire partagee et seed bank transferables",
    "tests de charge realistes sans confondre simulation et production",
    "architecture mobile Android comme worker volontaire",
    "architecture PC personnel comme runner physique",
    "navigateur comme worker ephemere volontaire",
    "federation de calculateurs scientifiques Python",
    "execution de simulations numeriques CPU sans LLM",
    "separation inference IA / calcul numerique / orchestration",
    "fallback deterministe quand aucun LLM n'est disponible",
    "catalogue de capacites et scheduling par competence",
    "reputation des providers basee sur resultats mesures",
    "controle de concurrence par provider",
    "limitation de debit globale et locale",
    "checkpoint/restart des longues missions",
    "reduction hierarchique de centaines de sorties",
    "consensus sans confondre consensus et verite",
    "replication independante multi-modele",
    "benchmark automatique de nouveaux fournisseurs gratuits",
    "verification automatique des conditions zero-euro avant activation",
    "architecture plugin/connecteur pour ajouter un calculateur externe",
    "API universelle task/result/evidence",
    "schema de passeport de worker et de calculateur",
    "identite cryptographique des workers",
    "verification des artefacts et hashes",
    "deduplication cross-farm",
    "allocation adaptative CPU/RAM/GPU",
    "isolation des jobs et limites ressources",
    "frontend dashboard temps reel",
    "mode degradation gracieuse",
    "autotests permanents des routes gratuites",
    "strategie d'expansion de 1 a 432 runners physiques",
    "inventaire de sources de compute gratuites legitimes",
    "analyse des goulots provider versus compute",
    "architecture de federation multi-depots sans evasion de quotas",
    "controle des couts avec spend_limit_eur=0",
    "plan de validation E0 a E8 de l'infrastructure",
    "red-team de l'hypothese compute illimite gratuit",
    "alternatives au besoin de 432 machines simultanees",
    "optimisation par densite de travail EFFERVESCENCE",
    "partage volontaire de compute par utilisateurs du site",
]


def make_task(index: int, shard: int) -> dict:
    role = ROLES[index % len(ROLES)]
    theme = THEMES[index % len(THEMES)]
    variant = index // len(THEMES)
    tid = "BZ-" + hashlib.sha256(f"{index}|{role}|{theme}".encode()).hexdigest()[:18].upper()
    return {
        "task_id": tid,
        "mission_id": MISSION_ID,
        "cycle": 1,
        "civilization": "C03",
        "team": 1 + (index % 10),
        "role": role,
        "shard": shard,
        "priority": 900 - (index % 100),
        "status": "PENDING",
        "booster_theme": theme,
        "variant": variant,
    }


def booster_prompt(task, mission, civilization_mission: str):
    base = shard_worker.role_prompt(task, mission, civilization_mission)
    return base + f"\nTHEME DE RECHERCHE: {task['booster_theme']}\nVARIANTE: {task['variant']}\n" \
        "Cherche une solution concrete, zero-euro par defaut, conforme aux CGU, " \
        "avec architecture, limites, test falsifiable et prochaine action.\n"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--shard", type=int, required=True)
    p.add_argument("--shards", type=int, default=36)
    p.add_argument("--tasks-per-shard", type=int, default=12)
    p.add_argument("--lanes", type=int, default=4)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    if not 0 <= args.shard < args.shards:
        raise SystemExit("invalid shard")

    start = args.shard * args.tasks_per_shard
    tasks = [make_task(start + i, args.shard) for i in range(args.tasks_per_shard)]
    missions = {MISSION_ID: MISSION}
    civ_map = {"C03": "Infrastructure, software, compute et validation."}

    original_prompt = shard_worker.role_prompt
    shard_worker.role_prompt = booster_prompt
    try:
        results = worker_highway.execute_highway(tasks, missions, civ_map, args.lanes)
    finally:
        shard_worker.role_prompt = original_prompt

    by_id = {t["task_id"]: t for t in tasks}
    for r in results:
        t = by_id.get(r.get("task_id"), {})
        r["booster_theme"] = t.get("booster_theme")
        r["booster_variant"] = t.get("variant")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(json.dumps({
        "engine": "CEREBRON_BOOSTER_ZERO_EURO_432_V1",
        "shard": args.shard,
        "selected": len(tasks),
        "results": len(results),
        "ok": sum(bool(r.get("ok")) for r in results),
        "paid_fallback": False,
        "trigger_nonce": TRIGGER_NONCE,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
