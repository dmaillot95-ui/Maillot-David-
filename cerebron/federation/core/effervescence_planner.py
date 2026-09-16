#!/usr/bin/env python3
"""CEREBRON OMEGA Effervescence planner.

Builds a compact GitHub Actions matrix containing only farm/shard pairs that own
eligible pending work. This increases useful runner density without creating or
bypassing quota. Ownership remains deterministic and unique.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def farm_for_task(task_id: str, farm_count: int) -> int:
    if farm_count < 1:
        raise ValueError("farm_count must be >= 1")
    return int(hashlib.sha256(task_id.encode("utf-8")).hexdigest(), 16) % farm_count


def build_matrix(queue: dict, cfg: dict) -> dict:
    mission = cfg.get("mission_id")
    farm_count = int(cfg["farm_count"])
    shard_count = int(cfg["shards_per_farm"])
    per_pair_limit = int(cfg.get("limit_per_farm_shard", 12))

    pair_counts: Counter[tuple[int, int]] = Counter()
    eligible = 0
    for task in queue.get("tasks", {}).values():
        if task.get("status") not in {"PENDING", "FAILED_RETRYABLE"}:
            continue
        if mission and task.get("mission_id") != mission:
            continue
        shard = int(task.get("shard", -1))
        if not 0 <= shard < shard_count:
            continue
        farm = farm_for_task(str(task.get("task_id")), farm_count)
        pair_counts[(farm, shard)] += 1
        eligible += 1

    # Most useful pairs first: fuller worker highways consume scarce runner slots first.
    ranked = sorted(
        pair_counts.items(),
        key=lambda kv: (-min(kv[1], per_pair_limit), -kv[1], kv[0][0], kv[0][1]),
    )
    include = [
        {
            "farm": farm,
            "shard": shard,
            "pending": count,
            "planned": min(count, per_pair_limit),
        }
        for (farm, shard), count in ranked
        if count > 0
    ]

    by_farm = {str(f): 0 for f in range(farm_count)}
    planned_tasks = 0
    for row in include:
        by_farm[str(row["farm"])] += row["pending"]
        planned_tasks += row["planned"]

    return {
        "matrix": {"include": include},
        "eligible_tasks": eligible,
        "active_pairs": len(include),
        "planned_tasks_this_wave": planned_tasks,
        "pending_by_farm": by_farm,
        "empty_pairs_skipped": farm_count * shard_count - len(include),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--queue", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--output")
    args = p.parse_args()

    queue = json.loads(Path(args.queue).read_text(encoding="utf-8"))
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    report = build_matrix(queue, cfg)
    text = json.dumps(report, ensure_ascii=False, separators=(",", ":"))
    print(text)
    if args.output:
        Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
