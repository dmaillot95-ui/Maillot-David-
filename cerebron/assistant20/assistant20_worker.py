#!/usr/bin/env python3
"""CÉRÉBRON Ω Assistant-20.

Twenty persistent logical agents are multiplexed through one GitHub runner so the
Collatz 20-shard campaign keeps priority over runner concurrency. External calls
stay zero-euro. Agents execute in configurable micro-waves with quota-aware
fallback across compatible model candidates.
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import importlib.util
import json
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS_PATH = ROOT / "assistant20" / "agents.json"
CONTROL_PATH = ROOT / "assistant20" / "control" / "mission.json"
STATE_PATH = ROOT / "assistant20" / "state" / "latest.json"
SHARD_WORKER_PATH = ROOT / "federation" / "core" / "shard_worker.py"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write(path: Path, obj):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load_shard_worker():
    spec = importlib.util.spec_from_file_location("cerebron_shard_worker", SHARD_WORKER_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def route_role(base_role: str) -> str:
    return "DECOMPOSER" if base_role == "COMPUTE_CHECKER" else base_role


def make_prompt(agent, control):
    return f"""CÉRÉBRON Ω — ASSISTANT PERMANENT {agent['id']}
SPÉCIALITÉ: {agent['role']}
MISSION PERMANENTE: {agent['mission']}
MISSION ACTUELLE: {control['objective']}
CONTEXTE FOURNI PAR GPT-5.6 SOL: {control.get('context','')}

RÈGLES:
- REALITY > COHERENCE
- EVIDENCE > CONFIDENCE
- CLAIM <= EVIDENCE
- ne jamais inventer une source, un calcul, un test ou un résultat
- distinguer PROUVÉ / CALCULÉ / HYPOTHÈSE / INCONNU / CONTRADICTION
- si une vérification externe ou déterministe manque, le signaler explicitement
- produire une contribution différente et utile au coordinateur principal

Réponse technique compacte, vérifiable, directement exploitable par le coordinateur.
"""


def execute_agent(agent, control, sw):
    role = route_role(agent["base_role"])
    task = {"task_id": f"A20-{control['nonce']}-{agent['id']}", "role": role}
    candidates = sw.model_candidates(task)
    base = {
        "agent_id": agent["id"],
        "specialty": agent["role"],
        "base_role": agent["base_role"],
        "route_role": role,
    }
    if not candidates:
        return {**base, "ok": False, "status": "HOLD_NO_COMPATIBLE_MODEL", "model_id": None,
                "model_family": None, "response": "", "response_sha256": None,
                "error": "No zero-euro compatible model", "error_type": "NO_MODEL",
                "attempted_models": [], "evidence_status": "NO_EVIDENCE"}

    prompt = make_prompt(agent, control)
    attempt_limit = max(1, min(int(control.get("per_agent_model_attempts", 3)), len(candidates)))
    base_backoff = max(0.0, float(control.get("quota_backoff_seconds", 4.0)))
    jitter = max(0.0, float(control.get("quota_jitter_seconds", 1.5)))
    attempts = []
    last_model = candidates[0]
    last_meta = {}

    for idx, model in enumerate(candidates[:attempt_limit]):
        last_model = model
        ok, response, meta = sw.invoke(model, prompt)
        last_meta = meta
        attempts.append({
            "model_id": model["model_id"],
            "model_family": model["family"],
            "space": model.get("space"),
            "ok": bool(ok),
            "endpoint": meta.get("endpoint"),
            "error_type": meta.get("error_type"),
        })
        if ok:
            return {
                **base,
                "ok": True,
                "status": "COMPLETED",
                "model_id": model["model_id"],
                "model_family": model["family"],
                "space": model.get("space"),
                "endpoint": meta.get("endpoint"),
                "response": response,
                "response_sha256": hashlib.sha256(response.encode()).hexdigest() if response else None,
                "error_type": None,
                "error": None,
                "attempted_models": attempts,
                "evidence_status": "UNREVIEWED_EXTERNAL_AGENT_OUTPUT",
            }

        if idx + 1 < attempt_limit:
            if meta.get("error_type") == "QUOTA":
                delay = base_backoff * (2 ** idx) + random.uniform(0.0, jitter)
            else:
                delay = min(1.0 + idx, 3.0)
            time.sleep(delay)

    all_quota = bool(attempts) and all(a.get("error_type") == "QUOTA" for a in attempts)
    return {
        **base,
        "ok": False,
        "status": "HOLD_QUOTA_BACKOFF" if all_quota else "FAILED_RETRYABLE",
        "model_id": last_model.get("model_id"),
        "model_family": last_model.get("family"),
        "space": last_model.get("space"),
        "endpoint": last_meta.get("endpoint"),
        "response": "",
        "response_sha256": None,
        "error_type": "QUOTA" if all_quota else last_meta.get("error_type"),
        "error": last_meta.get("error"),
        "attempted_models": attempts,
        "evidence_status": "NO_EVIDENCE",
    }


def run_micro_batch(batch, control, sw, max_parallel):
    results = []
    workers = max(1, min(max_parallel, len(batch)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(execute_agent, a, control, sw): a["id"] for a in batch}
        for fut in concurrent.futures.as_completed(futs):
            aid = futs[fut]
            try:
                result = fut.result()
            except Exception as exc:
                result = {"agent_id": aid, "ok": False, "status": "FAILED_RETRYABLE",
                          "response": "", "response_sha256": None, "error": repr(exc),
                          "error_type": "EXCEPTION", "attempted_models": [],
                          "evidence_status": "NO_EVIDENCE"}
            results.append(result)
            print(json.dumps({k: result.get(k) for k in
                              ("agent_id", "specialty", "ok", "status", "model_id", "model_family")},
                             ensure_ascii=False))
    return results


def main():
    agents_doc = load(AGENTS_PATH)
    control = load(CONTROL_PATH)
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    out_dir = Path(os.environ.get("ASSISTANT20_OUT", "assistant20-out"))
    out_dir.mkdir(parents=True, exist_ok=True)

    if not control.get("enabled", False):
        summary = {"schema": "cerebron-assistant20-run-v2", "run_id": run_id, "at": now_iso(),
                   "enabled": False, "selected": 0, "completed": 0, "failed": 0, "results": []}
        atomic_write(out_dir / "summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    active = set(control.get("active_agents") or [])
    selected = [a for a in agents_doc.get("agents", []) if a["id"] in active]
    micro_batch_size = max(1, min(int(control.get("micro_batch_size", 4)), 20))
    max_parallel = max(1, min(int(control.get("max_parallel_external_calls", micro_batch_size)), micro_batch_size))
    pause_seconds = max(0.0, float(control.get("micro_batch_pause_seconds", 8.0)))
    pause_jitter = max(0.0, float(control.get("micro_batch_jitter_seconds", 2.0)))
    sw = load_shard_worker()

    results = []
    batches = [selected[i:i + micro_batch_size] for i in range(0, len(selected), micro_batch_size)]
    for batch_index, batch in enumerate(batches, start=1):
        print(json.dumps({"event": "MICRO_BATCH_START", "batch": batch_index,
                          "total_batches": len(batches), "agents": [a["id"] for a in batch]}, ensure_ascii=False))
        results.extend(run_micro_batch(batch, control, sw, max_parallel))
        if batch_index < len(batches) and pause_seconds > 0:
            delay = pause_seconds + random.uniform(0.0, pause_jitter)
            print(json.dumps({"event": "MICRO_BATCH_BACKOFF", "seconds": round(delay, 2)}, ensure_ascii=False))
            time.sleep(delay)

    results.sort(key=lambda r: r["agent_id"])
    with (out_dir / "results.jsonl").open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    persistent_results = {}
    for r in results:
        persistent_results[r["agent_id"]] = {
            "specialty": r.get("specialty"),
            "status": r.get("status"),
            "ok": bool(r.get("ok")),
            "model_id": r.get("model_id"),
            "model_family": r.get("model_family"),
            "response_sha256": r.get("response_sha256"),
            "response_excerpt": (r.get("response") or "")[:500],
            "evidence_status": r.get("evidence_status"),
            "error_type": r.get("error_type"),
            "attempt_count": len(r.get("attempted_models") or []),
        }

    completed = sum(1 for r in results if r.get("ok"))
    failed = len(results) - completed
    state = {
        "schema": "cerebron-assistant20-state-v2",
        "updated_at": now_iso(),
        "last_run_id": run_id,
        "mission_nonce": control.get("nonce"),
        "mission_objective": control.get("objective"),
        "execution_policy": {
            "micro_batch_size": micro_batch_size,
            "max_parallel_external_calls": max_parallel,
            "micro_batch_pause_seconds": pause_seconds,
            "per_agent_model_attempts": int(control.get("per_agent_model_attempts", 3)),
        },
        "active_agents": [r["agent_id"] for r in results],
        "completed_agents": completed,
        "failed_agents": failed,
        "results": persistent_results,
    }
    atomic_write(STATE_PATH, state)
    summary = {
        "schema": "cerebron-assistant20-run-v2",
        "run_id": run_id,
        "at": now_iso(),
        "enabled": True,
        "selected": len(results),
        "completed": completed,
        "failed": failed,
        "micro_batches": len(batches),
        "micro_batch_size": micro_batch_size,
        "max_parallel_external_calls": max_parallel,
        "model_families": sorted({r.get("model_family") for r in results if r.get("model_family")}),
        "results": [{"agent_id": r["agent_id"], "status": r.get("status"), "ok": bool(r.get("ok")),
                     "model_id": r.get("model_id"), "model_family": r.get("model_family"),
                     "attempt_count": len(r.get("attempted_models") or []),
                     "response_sha256": r.get("response_sha256")} for r in results],
    }
    atomic_write(out_dir / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
