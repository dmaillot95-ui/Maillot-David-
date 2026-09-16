#!/usr/bin/env python3
"""CEREBRON OMEGA farm worker.

Partitions one shard's eligible tasks deterministically across logical farms and
executes the assigned subset through Worker Highway. This increases orchestration
capacity without pretending to create new GitHub/provider quota.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

CORE = Path(__file__).resolve().parent
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))

import shard_worker  # noqa: E402
import worker_highway  # noqa: E402


def farm_for_task(task_id: str, farm_count: int) -> int:
    if farm_count < 1:
        raise ValueError("farm_count must be >= 1")
    digest = hashlib.sha256(task_id.encode("utf-8")).hexdigest()
    return int(digest, 16) % farm_count


def farm_tasks(shard: int, farm_id: int, farm_count: int, limit: int, mission_id: str | None):
    q = shard_worker.load(shard_worker.QUEUE_PATH)
    tasks = []
    for t in q.get("tasks", {}).values():
        if int(t.get("shard", -1)) != shard:
            continue
        if t.get("status") not in {"PENDING", "FAILED_RETRYABLE"}:
            continue
        if mission_id and t.get("mission_id") != mission_id:
            continue
        if farm_for_task(str(t.get("task_id")), farm_count) != farm_id:
            continue
        tasks.append(t)
    tasks.sort(key=lambda t: (-int(t.get("priority", 0)), t.get("created_at", ""), t["task_id"]))
    return tasks[:limit], q.get("missions", {})


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--farm-id", type=int, required=True)
    p.add_argument("--farm-count", type=int, required=True)
    p.add_argument("--shard", type=int, required=True)
    p.add_argument("--limit", type=int, default=12)
    p.add_argument("--lanes", type=int, default=4)
    p.add_argument("--mission-id")
    p.add_argument("--output", required=True)
    args = p.parse_args()

    if not 0 <= args.farm_id < args.farm_count:
        raise SystemExit("farm-id must satisfy 0 <= farm-id < farm-count")

    tasks, missions = farm_tasks(args.shard, args.farm_id, args.farm_count, args.limit, args.mission_id)
    civ_map = shard_worker.civilization_map()
    results = worker_highway.execute_highway(tasks, missions, civ_map, args.lanes)
    for r in results:
        r["farm_id"] = args.farm_id
        r["farm_count"] = args.farm_count

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(json.dumps({
        "engine": "CEREBRON_FARM_WORKER_V1",
        "farm_id": args.farm_id,
        "farm_count": args.farm_count,
        "shard": args.shard,
        "lanes": args.lanes,
        "selected": len(tasks),
        "results": len(results),
        "ok": sum(bool(r.get("ok")) for r in results),
        "paid_fallback": False,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
