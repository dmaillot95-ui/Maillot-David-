#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[0]
CONFIG_PATH = HERE / "config.json"
QUEUE_PATH = HERE / "state" / "queue.json"
LATEST_PATH = HERE / "state" / "latest.json"
SHARD_WORKER_PATH = ROOT / "federation" / "core" / "shard_worker.py"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load_shard_worker():
    spec = importlib.util.spec_from_file_location("cerebron_hub_shard_worker", SHARD_WORKER_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def task_id(mission_id: str, agent_id: str, prompt: str) -> str:
    digest = hashlib.sha256(f"{mission_id}|{agent_id}|{prompt}".encode()).hexdigest()[:16]
    return f"HUB-{digest}"


def ensure_queue():
    q = load(QUEUE_PATH, None)
    if q is None:
        q = {"schema": "cerebron-inference-hub-queue-v1", "updated_at": now_iso(), "tasks": {}}
        atomic_write(QUEUE_PATH, q)
    return q


def enqueue(mission_id: str, prompt: str, agents: int):
    cfg = load(CONFIG_PATH)
    max_agents = int(cfg.get("max_logical_agents", 10000))
    agents = max(1, min(int(agents), max_agents))
    q = ensure_queue()
    created = []
    for n in range(1, agents + 1):
        aid = f"A{n:04d}"
        tid = task_id(mission_id, aid, prompt)
        if tid not in q["tasks"]:
            q["tasks"][tid] = {
                "task_id": tid,
                "mission_id": mission_id,
                "agent_id": aid,
                "prompt": prompt,
                "status": "PENDING",
                "attempts": 0,
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "result": None,
            }
            created.append(tid)
    q["updated_at"] = now_iso()
    atomic_write(QUEUE_PATH, q)
    return created


def provider_task(t):
    return {"task_id": t["task_id"], "role": "DECOMPOSER"}


def run_external(t, sw, cfg):
    candidates = sw.model_candidates(provider_task(t))
    max_attempts = int(cfg.get("max_attempts_per_task", 3))
    attempts = []
    for model in candidates[:max_attempts]:
        prompt = (
            "CÉRÉBRON INFERENCE HUB — AGENT LOGIQUE\n"
            f"AGENT: {t['agent_id']}\nMISSION: {t['mission_id']}\n"
            f"QUESTION: {t['prompt']}\n\n"
            "RÈGLES: REALITY>COHERENCE; EVIDENCE>CONFIDENCE; CLAIM<=EVIDENCE. "
            "Sépare résultat, hypothèse, inconnue et contradiction."
        )
        ok, response, meta = sw.invoke(model, prompt)
        attempts.append({
            "model_id": model.get("model_id"),
            "family": model.get("family"),
            "ok": bool(ok),
            "error_type": meta.get("error_type"),
            "endpoint": meta.get("endpoint"),
        })
        if ok:
            return {
                "ok": True,
                "status": "COMPLETED",
                "provider": "huggingface_spaces",
                "model_id": model.get("model_id"),
                "model_family": model.get("family"),
                "response": response,
                "response_sha256": hashlib.sha256(response.encode()).hexdigest() if response else None,
                "attempts": attempts,
                "evidence_status": "UNREVIEWED_EXTERNAL_AGENT_OUTPUT",
            }
        delay = 2.0 if meta.get("error_type") == "QUOTA" else 0.5
        time.sleep(delay + random.uniform(0.0, 0.8))
    all_quota = bool(attempts) and all(a.get("error_type") == "QUOTA" for a in attempts)
    return {
        "ok": False,
        "status": "HOLD_QUOTA_BACKOFF" if all_quota else "FAILED_RETRYABLE",
        "provider": "huggingface_spaces",
        "model_id": attempts[-1].get("model_id") if attempts else None,
        "model_family": attempts[-1].get("family") if attempts else None,
        "response": "",
        "response_sha256": None,
        "attempts": attempts,
        "evidence_status": "NO_EVIDENCE",
    }


def execute_pending(limit=None):
    cfg = load(CONFIG_PATH)
    q = ensure_queue()
    pending = [t for t in q["tasks"].values() if t.get("status") in {"PENDING", "FAILED_RETRYABLE", "HOLD_QUOTA_BACKOFF"}]
    pending.sort(key=lambda x: (x.get("created_at", ""), x["task_id"]))
    if limit:
        pending = pending[:int(limit)]
    if not pending:
        return {"selected": 0, "completed": 0, "held": 0, "failed": 0, "results": []}

    micro = max(1, int(cfg.get("micro_batch_size", 4)))
    max_workers = max(1, min(int(cfg.get("max_parallel_workers", 4)), micro))
    wave_delay = max(0.0, float(cfg.get("wave_delay_seconds", 8)))
    sw = load_shard_worker()
    results = []

    for start in range(0, len(pending), micro):
        wave = pending[start:start + micro]
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(max_workers, len(wave))) as pool:
            futs = {pool.submit(run_external, t, sw, cfg): t for t in wave}
            for fut in concurrent.futures.as_completed(futs):
                t = futs[fut]
                try:
                    r = fut.result()
                except Exception as exc:
                    r = {
                        "ok": False,
                        "status": "FAILED_RETRYABLE",
                        "provider": None,
                        "response": "",
                        "response_sha256": None,
                        "attempts": [],
                        "evidence_status": "NO_EVIDENCE",
                        "error": repr(exc),
                    }
                current = q["tasks"][t["task_id"]]
                current["status"] = r["status"]
                current["attempts"] = int(current.get("attempts", 0)) + max(1, len(r.get("attempts", [])))
                current["updated_at"] = now_iso()
                current["result"] = {k: v for k, v in r.items() if k != "response"}
                if r.get("ok"):
                    current["result"]["response_excerpt"] = (r.get("response") or "")[:700]
                results.append({"task_id": t["task_id"], "agent_id": t["agent_id"], **r})
        atomic_write(QUEUE_PATH, q)
        if start + micro < len(pending):
            time.sleep(wave_delay + random.uniform(0.0, min(3.0, wave_delay / 2 if wave_delay else 0.0)))

    completed = sum(1 for r in results if r.get("status") == "COMPLETED")
    held = sum(1 for r in results if r.get("status") == "HOLD_QUOTA_BACKOFF")
    failed = len(results) - completed - held
    latest = {
        "schema": "cerebron-inference-hub-state-v1",
        "updated_at": now_iso(),
        "selected": len(results),
        "completed": completed,
        "held": held,
        "failed": failed,
        "max_parallel_workers": max_workers,
        "micro_batch_size": micro,
        "zero_euro": True,
        "results": [{k: v for k, v in r.items() if k != "response"} for r in results],
    }
    atomic_write(LATEST_PATH, latest)
    return latest


def status():
    q = ensure_queue()
    counts = {}
    for t in q["tasks"].values():
        counts[t.get("status", "UNKNOWN")] = counts.get(t.get("status", "UNKNOWN"), 0) + 1
    return {"updated_at": q.get("updated_at"), "tasks": len(q["tasks"]), "status": counts}


def main():
    p = argparse.ArgumentParser(description="CEREBRON Inference Hub v1")
    sub = p.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("enqueue")
    e.add_argument("--mission-id", required=True)
    e.add_argument("--prompt", required=True)
    e.add_argument("--agents", type=int, default=20)

    r = sub.add_parser("run")
    r.add_argument("--limit", type=int)

    sub.add_parser("status")
    args = p.parse_args()

    if args.cmd == "enqueue":
        created = enqueue(args.mission_id, args.prompt, args.agents)
        print(json.dumps({"created": len(created), "task_ids": created}, ensure_ascii=False, indent=2))
    elif args.cmd == "run":
        print(json.dumps(execute_pending(args.limit), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(status(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
