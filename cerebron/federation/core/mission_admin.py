#!/usr/bin/env python3
from __future__ import annotations

import argparse

import queue_engine as qe


def cancel_mission(mission_id: str) -> int:
    q = qe.queue()
    mission = q["missions"].get(mission_id)
    if not mission:
        raise SystemExit(f"Unknown mission: {mission_id}")

    cancelled = 0
    for task_id in mission.get("task_ids", []):
        task = q["tasks"].get(task_id)
        if not task:
            continue
        if task.get("status") in qe.TERMINAL:
            continue
        task["status"] = "CANCELLED"
        task["lease_owner"] = None
        task["lease_expires_at"] = None
        task["updated_at"] = qe.now_iso()
        cancelled += 1

    mission["status"] = "CANCELLED"
    mission["updated_at"] = qe.now_iso()
    qe.event(q, "MISSION_CANCELLED", mission_id=mission_id, tasks_cancelled=cancelled)
    qe.save(q)
    return cancelled


def set_target_cycles(mission_id: str, target_cycles: int) -> int:
    q = qe.queue()
    mission = q["missions"].get(mission_id)
    if not mission:
        raise SystemExit(f"Unknown mission: {mission_id}")
    target_cycles = int(target_cycles)
    if target_cycles < int(mission.get("current_cycle", 0)):
        raise SystemExit("target_cycles cannot be below current_cycle")
    mission["target_cycles"] = target_cycles
    mission["updated_at"] = qe.now_iso()
    qe.event(q, "MISSION_TARGET_CYCLES_UPDATED", mission_id=mission_id, target_cycles=target_cycles)
    qe.save(q)
    return target_cycles


def main() -> None:
    parser = argparse.ArgumentParser(description="CEREBRON federation mission administration")
    sub = parser.add_subparsers(dest="cmd", required=True)

    cancel = sub.add_parser("cancel")
    cancel.add_argument("mission_id")

    target = sub.add_parser("set-target-cycles")
    target.add_argument("mission_id")
    target.add_argument("target_cycles", type=int)

    args = parser.parse_args()

    if args.cmd == "cancel":
        print(cancel_mission(args.mission_id))
    elif args.cmd == "set-target-cycles":
        print(set_target_cycles(args.mission_id, args.target_cycles))


if __name__ == "__main__":
    main()
