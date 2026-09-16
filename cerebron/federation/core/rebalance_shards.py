#!/usr/bin/env python3
"""Safely rebalance non-active CEREBRON tasks across the configured shard cap.

Only PENDING and FAILED_RETRYABLE tasks are moved. LEASED/RUNNING and terminal
records are never reassigned, so an in-flight worker keeps ownership.
"""
from __future__ import annotations

import hashlib
import json

import queue_engine as qe


def desired_shard(task_id: str, cap: int) -> int:
    return int(hashlib.sha256(task_id.encode()).hexdigest(), 16) % cap


def main() -> None:
    cfg = qe.config()
    cap = int(cfg.get("scale", {}).get("github_parallel_cap", 1))
    if cap < 1:
        raise SystemExit("github_parallel_cap must be >= 1")

    q = qe.queue()
    moved = 0
    untouched_active = 0
    eligible = {"PENDING", "FAILED_RETRYABLE"}

    for task in q.get("tasks", {}).values():
        if task.get("status") not in eligible:
            if task.get("status") in {"LEASED", "RUNNING"}:
                untouched_active += 1
            continue
        target = desired_shard(str(task["task_id"]), cap)
        if int(task.get("shard", -1)) != target:
            task["shard"] = target
            moved += 1

    qe.event(q, "SHARDS_REBALANCED", parallel_cap=cap, tasks_moved=moved,
             active_tasks_untouched=untouched_active)
    qe.save(q)
    print(json.dumps({
        "parallel_cap": cap,
        "tasks_moved": moved,
        "active_tasks_untouched": untouched_active,
        "policy": "PENDING_AND_FAILED_RETRYABLE_ONLY"
    }, indent=2))


if __name__ == "__main__":
    main()
