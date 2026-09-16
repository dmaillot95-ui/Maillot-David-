#!/usr/bin/env python3
"""CEREBRON OMEGA — BOOSTER ZERO-EURO 432 v2.

Fixes the v1 prompt-recursion bug by capturing the base role prompt before
installing the booster prompt wrapper. Executes the same deterministic 432-task
campaign through Worker Highway. CLAIM<=EVIDENCE.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import booster_wave as bw
import shard_worker
import worker_highway

BASE_ROLE_PROMPT = shard_worker.role_prompt
TRIGGER_NONCE = "2026-09-16TBOOSTER-432-V2"


def safe_booster_prompt(task, mission, civilization_mission: str):
    base = BASE_ROLE_PROMPT(task, mission, civilization_mission)
    return (
        base
        + f"\nTHEME DE RECHERCHE: {task['booster_theme']}\nVARIANTE: {task['variant']}\n"
        + "Cherche une solution concrete, zero-euro par defaut, conforme aux CGU, "
          "avec architecture, limites, test falsifiable et prochaine action.\n"
    )


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
    tasks = [bw.make_task(start + i, args.shard) for i in range(args.tasks_per_shard)]
    missions = {bw.MISSION_ID: bw.MISSION}
    civ_map = {"C03": "Infrastructure, software, compute et validation."}

    original_prompt = shard_worker.role_prompt
    shard_worker.role_prompt = safe_booster_prompt
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
        "engine": "CEREBRON_BOOSTER_ZERO_EURO_432_V2",
        "shard": args.shard,
        "selected": len(tasks),
        "results": len(results),
        "ok": sum(bool(r.get("ok")) for r in results),
        "paid_fallback": False,
        "trigger_nonce": TRIGGER_NONCE,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
