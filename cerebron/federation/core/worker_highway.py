#!/usr/bin/env python3
"""CEREBRON OMEGA Worker Highway.

Turns one GitHub shard runner into a small pool of network-bound execution lanes.
The lanes share a task queue (ThreadPoolExecutor work stealing) while each lane keeps
its own provider circuit breakers. Only routes already exposed by the adaptive
zero-euro router are used. This module does not create quota, bypass limits, or add
paid fallback.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock, local

CORE = Path(__file__).resolve().parent
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))

# Importing adaptive_shard_worker patches shard_worker with the expanded adaptive
# provider registry/order before any task is executed.
import adaptive_shard_worker as adaptive  # noqa: E402,F401
import shard_worker  # noqa: E402

_thread = local()
_lane_lock = Lock()
_lane_counter = 0


def _lane_state() -> tuple[int, set[str]]:
    """Return stable lane id and lane-local provider circuit breakers."""
    global _lane_counter
    if not hasattr(_thread, "lane_id"):
        with _lane_lock:
            lane_id = _lane_counter
            _lane_counter += 1
        _thread.lane_id = lane_id
        _thread.blocked_routes = set()
    return _thread.lane_id, _thread.blocked_routes


def _execute_task(task: dict, missions: dict, civ_map: dict) -> dict:
    lane_id, blocked_routes = _lane_state()
    mission = missions.get(task.get("mission_id"))
    if not mission:
        result = {
            "task_id": task["task_id"],
            "execution_status": "FAILED_RETRYABLE",
            "ok": False,
            "error": "Mission missing",
            "attempted_models": [],
        }
    elif task.get("role") == "COMPUTE_CHECKER":
        result = {
            "task_id": task["task_id"],
            "mission_id": task.get("mission_id"),
            "cycle": task.get("cycle"),
            "civilization": task.get("civilization"),
            "team": task.get("team"),
            "role": task.get("role"),
            "shard": task.get("shard"),
            "execution_status": "HOLD_DETERMINISTIC_CHECK",
            "ok": False,
            "provider": "github_actions_cpu",
            "model_id": None,
            "model_family": None,
            "response": "HOLD_DETERMINISTIC_CHECK",
            "error": None,
            "attempted_models": [],
            "evidence_status": "DETERMINISTIC_CHECK_REQUIRED",
        }
    else:
        result = shard_worker.execute_one(task, mission, civ_map, blocked_routes)
    result["highway_lane"] = lane_id
    return result


def execute_highway(tasks: list[dict], missions: dict, civ_map: dict, lanes: int) -> list[dict]:
    """Execute a shared queue across bounded lanes; idle lanes steal next work."""
    lanes = max(1, min(int(lanes), 16))
    if not tasks:
        return []
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=min(lanes, len(tasks)), thread_name_prefix="cerebron-lane") as pool:
        future_map = {pool.submit(_execute_task, task, missions, civ_map): task for task in tasks}
        for future in as_completed(future_map):
            task = future_map[future]
            try:
                result = future.result()
            except Exception as exc:
                result = {
                    "task_id": task.get("task_id"),
                    "mission_id": task.get("mission_id"),
                    "role": task.get("role"),
                    "shard": task.get("shard"),
                    "execution_status": "FAILED_RETRYABLE",
                    "ok": False,
                    "provider": None,
                    "model_id": None,
                    "model_family": None,
                    "response": "",
                    "response_sha256": None,
                    "error": repr(exc),
                    "attempted_models": [],
                    "evidence_status": "NO_EVIDENCE",
                    "highway_lane": None,
                }
            results.append(result)
            print(json.dumps({k: result.get(k) for k in (
                "task_id", "role", "ok", "execution_status", "provider",
                "model_id", "model_family", "highway_lane"
            )}, ensure_ascii=False), flush=True)
    # Deterministic artifact order independent of completion order.
    results.sort(key=lambda r: str(r.get("task_id") or ""))
    return results


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--shard", type=int, required=True)
    p.add_argument("--limit", type=int, default=12)
    p.add_argument("--lanes", type=int, default=int(os.getenv("CEREBRON_HIGHWAY_LANES", "4")))
    p.add_argument("--mission-id")
    p.add_argument("--output", required=True)
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--smoke-role", default="PROOF_A")
    p.add_argument("--smoke-objective", default="Verify the Worker Highway without inventing evidence.")
    args = p.parse_args()

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    civ_map = shard_worker.civilization_map()

    if args.smoke:
        tasks = [shard_worker.smoke_task(args.shard, args.smoke_role)]
        missions = {"SMOKE": {"title": "CEREBRON WORKER HIGHWAY SMOKE", "objective": args.smoke_objective}}
    else:
        tasks, missions = shard_worker.queue_tasks(args.shard, args.limit, args.mission_id)

    results = execute_highway(tasks, missions, civ_map, args.lanes)
    with out.open("w", encoding="utf-8") as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")

    routes = shard_worker.available_zero_euro_routes()
    print(json.dumps({
        "engine": "CEREBRON_WORKER_HIGHWAY_V1",
        "shard": args.shard,
        "lanes_requested": args.lanes,
        "lanes_effective": min(max(1, args.lanes), 16, max(1, len(tasks))),
        "selected": len(tasks),
        "results": len(results),
        "ok": sum(bool(r.get("ok")) for r in results),
        "available_zero_euro_routes": routes,
        "paid_fallback": False,
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
