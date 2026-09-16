#!/usr/bin/env python3
"""CEREBRON OMEGA Worker Factory.

Creates logical workers on demand, but never pretends that logical workers are
physical compute. Physical execution capacity is taken only from the verified
runner-farm status produced by GitHub's self-hosted runner API.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROLES = [
    "SCOUT", "DECOMPOSER", "PROOF_A", "PROOF_B", "COMPUTE_CHECKER",
    "ALTERNATIVE_ROUTE", "FALSIFIER", "RED_TEAM", "COUNTER_AUDITOR",
    "REPLICATOR", "SYNTHESIZER", "JUDGE",
]


def load(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def stable_id(mission_id: str, index: int, role: str) -> str:
    raw = f"{mission_id}|{index}|{role}".encode("utf-8")
    return "W-" + hashlib.sha256(raw).hexdigest()[:20].upper()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--mission-id", required=True)
    p.add_argument("--count", type=int, required=True)
    p.add_argument("--runner-status", default="cerebron/runner_farm/state/runner-farm-status.json")
    p.add_argument("--output", default="cerebron/worker_factory/state/worker-plan.json")
    p.add_argument("--max-logical-workers", type=int, default=10000)
    args = p.parse_args()

    if args.count < 1:
        raise SystemExit("count must be >= 1")
    if args.count > args.max_logical_workers:
        raise SystemExit(f"count exceeds max-logical-workers={args.max_logical_workers}")

    status = load(Path(args.runner_status), {})
    verified_source = status.get("source") == "github-self-hosted-runners-api"
    online_ids = list(status.get("online_runner_ids", [])) if verified_source else []
    physical_online = len(online_ids)

    workers = []
    for i in range(args.count):
        role = ROLES[i % len(ROLES)]
        runner_id = online_ids[i % physical_online] if physical_online else None
        workers.append({
            "worker_id": stable_id(args.mission_id, i, role),
            "mission_id": args.mission_id,
            "index": i,
            "role": role,
            "physical_runner_id": runner_id,
            "execution_state": "READY" if runner_id else "WAITING_FOR_PHYSICAL_CAPACITY",
            "evidence_class": "LOGICAL_WORKER_ONLY" if not runner_id else "BOUND_TO_VERIFIED_PHYSICAL_RUNNER",
        })

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    bound = sum(1 for w in workers if w["physical_runner_id"] is not None)
    plan = {
        "schema": "cerebron-worker-factory-plan-v1",
        "created_at": now,
        "mission_id": args.mission_id,
        "requested_logical_workers": args.count,
        "created_logical_workers": len(workers),
        "verified_online_physical_runners": physical_online,
        "workers_bound_to_physical_capacity": bound,
        "workers_waiting_for_physical_capacity": len(workers) - bound,
        "claim_rule": "logical worker != physical runner != successful AI inference",
        "workers": workers,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: plan[k] for k in (
        "requested_logical_workers", "created_logical_workers",
        "verified_online_physical_runners", "workers_bound_to_physical_capacity",
        "workers_waiting_for_physical_capacity"
    )}, ensure_ascii=False))


if __name__ == "__main__":
    main()
