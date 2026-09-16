#!/usr/bin/env python3
"""CÉRÉBRON Ω Assistant-20.

Twenty persistent logical agents are multiplexed through one GitHub runner so the
Collatz 20-shard campaign keeps priority over runner concurrency. Each active
agent performs at most one zero-euro external Hugging Face inference per mission.
Outputs are immutable artifacts; only hashes/excerpts enter persistent state.
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import importlib.util
import json
import os
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
    # COMPUTE_CHECKER is intentionally deterministic-only in the Collatz worker.
    # Here the generalist agent may reason about calculations, but its output stays
    # UNREVIEWED and is never promoted as a deterministic verification.
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
                "error": "No zero-euro compatible model"}
    model = candidates[0]
    prompt = make_prompt(agent, control)
    ok, response, meta = sw.invoke(model, prompt)
    return {
        **base,
        "ok": bool(ok),
        "status": "COMPLETED" if ok else ("HOLD_QUOTA_BACKOFF" if meta.get("error_type") == "QUOTA" else "FAILED_RETRYABLE"),
        "model_id": model["model_id"],
        "model_family": model["family"],
        "space": model["space"],
        "endpoint": meta.get("endpoint"),
        "response": response if ok else "",
        "response_sha256": hashlib.sha256(response.encode()).hexdigest() if ok and response else None,
        "error_type": meta.get("error_type"),
        "error": meta.get("error"),
        "evidence_status": "UNREVIEWED_EXTERNAL_AGENT_OUTPUT" if ok else "NO_EVIDENCE",
    }


def main():
    agents_doc = load(AGENTS_PATH)
    control = load(CONTROL_PATH)
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    out_dir = Path(os.environ.get("ASSISTANT20_OUT", "assistant20-out"))
    out_dir.mkdir(parents=True, exist_ok=True)

    if not control.get("enabled", False):
        summary = {"schema":"cerebron-assistant20-run-v1","run_id":run_id,"at":now_iso(),"enabled":False,"selected":0,"completed":0,"failed":0,"results":[]}
        atomic_write(out_dir / "summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    active = set(control.get("active_agents") or [])
    selected = [a for a in agents_doc.get("agents", []) if a["id"] in active]
    max_workers = min(int(control.get("max_parallel_external_calls", 20)), 20, max(1, len(selected)))
    sw = load_shard_worker()

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futs = {pool.submit(execute_agent, a, control, sw): a["id"] for a in selected}
        for fut in concurrent.futures.as_completed(futs):
            aid = futs[fut]
            try:
                result = fut.result()
            except Exception as exc:
                result = {"agent_id":aid,"ok":False,"status":"FAILED_RETRYABLE","response":"","response_sha256":None,"error":repr(exc),"evidence_status":"NO_EVIDENCE"}
            results.append(result)
            print(json.dumps({k:result.get(k) for k in ("agent_id","specialty","ok","status","model_id","model_family")}, ensure_ascii=False))

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
        }

    completed = sum(1 for r in results if r.get("ok"))
    failed = len(results) - completed
    state = {
        "schema":"cerebron-assistant20-state-v1",
        "updated_at":now_iso(),
        "last_run_id":run_id,
        "mission_nonce":control.get("nonce"),
        "mission_objective":control.get("objective"),
        "active_agents":[r["agent_id"] for r in results],
        "completed_agents":completed,
        "failed_agents":failed,
        "results":persistent_results,
    }
    atomic_write(STATE_PATH, state)
    summary = {"schema":"cerebron-assistant20-run-v1","run_id":run_id,"at":now_iso(),"enabled":True,"selected":len(results),"completed":completed,"failed":failed,"model_families":sorted({r.get('model_family') for r in results if r.get('model_family')}),"results":[{"agent_id":r['agent_id'],"status":r.get('status'),"ok":bool(r.get('ok')),"model_id":r.get('model_id'),"model_family":r.get('model_family'),"response_sha256":r.get('response_sha256')} for r in results]}
    atomic_write(out_dir / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
