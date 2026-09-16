#!/usr/bin/env python3
"""Daily long-run campaign controller for CÉRÉBRON Ω.

This controller does not call any model. It extends the persistent mission horizon
and opens at most one new 12x10x12 cycle per UTC day when the previous cycle is
fully terminal. It is bounded by an explicit end date and maximum cycle count.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "control" / "longrun.json"
QUEUE_PATH = ROOT / "state" / "mission-queue.json"
LATEST_PATH = ROOT / "state" / "latest-state.json"
FEDERATION_PATH = ROOT / "federation-v1.json"


def now():
    return datetime.now(timezone.utc)


def now_iso():
    return now().replace(microsecond=0).isoformat()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write(path: Path, data):
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def task_id(mid: str, cycle: int, civ: str, team: int, role: str):
    raw = f"{mid}|{cycle}|{civ}|{team}|{role}".encode()
    return "T-" + hashlib.sha256(raw).hexdigest()[:20].upper()


def write_latest(q):
    counts = {}
    for t in q.get("tasks", {}).values():
        s = t.get("status", "UNKNOWN")
        counts[s] = counts.get(s, 0) + 1
    terminal_missions = {"COMPLETED", "REJECTED", "CANCELLED"}
    latest = {
        "schema": "cerebron-latest-state-v1",
        "updated_at": now_iso(),
        "mission_count": len(q.get("missions", {})),
        "task_count": len(q.get("tasks", {})),
        "task_status": counts,
        "active_missions": [mid for mid,m in q.get("missions", {}).items() if m.get("status") not in terminal_missions],
        "last_event_seq": q.get("event_seq", 0),
        "longrun": {
            "policy": str(POLICY_PATH.relative_to(ROOT)),
            "checked_at": now_iso(),
        },
    }
    atomic_write(LATEST_PATH, latest)


def main():
    policy = load(POLICY_PATH)
    q = load(QUEUE_PATH)
    fed = load(FEDERATION_PATH)
    ts = now()
    today = ts.date().isoformat()

    report = {"at": now_iso(), "today": today, "changed": False, "expanded": False}
    if not policy.get("enabled", False):
        report["reason"] = "DISABLED"
        print(json.dumps(report, ensure_ascii=False, indent=2)); return
    if today < policy["start_date_utc"] or today > policy["end_date_utc"]:
        report["reason"] = "OUTSIDE_CAMPAIGN_WINDOW"
        print(json.dumps(report, ensure_ascii=False, indent=2)); return

    mid = policy["mission_id"]
    m = q.get("missions", {}).get(mid)
    if not m:
        report["reason"] = "MISSION_NOT_FOUND"
        print(json.dumps(report, ensure_ascii=False, indent=2)); return

    max_cycles = int(policy.get("max_cycles", 62))
    if int(m.get("target_cycles", 1)) != max_cycles:
        m["target_cycles"] = max_cycles
        report["changed"] = True

    current = int(m.get("current_cycle", 0))
    terminal = set(policy.get("terminal_statuses", ["COMPLETED","REJECTED","CANCELLED","QUARANTINED"]))
    current_tasks = [t for t in q.get("tasks", {}).values() if t.get("mission_id") == mid and int(t.get("cycle", 0)) == current]
    nonterminal = [t for t in current_tasks if t.get("status") not in terminal]

    report.update({
        "mission_id": mid,
        "current_cycle": current,
        "target_cycles": max_cycles,
        "current_cycle_tasks": len(current_tasks),
        "current_cycle_nonterminal": len(nonterminal),
    })

    # At most one new cycle per UTC day. This intentionally prevents runaway
    # generation even if a cycle completes quickly.
    if current >= max_cycles:
        report["reason"] = "MAX_CYCLES_REACHED"
    elif current_tasks and nonterminal:
        report["reason"] = "CURRENT_CYCLE_STILL_ACTIVE"
    elif m.get("last_longrun_expand_date") == today:
        report["reason"] = "DAILY_EXPANSION_ALREADY_USED"
    else:
        next_cycle = current + 1
        roles = fed["team_template"]["roles"]
        civs = fed["civilizations"]
        teams = int(fed["scale"]["teams_per_civilization"])
        shards = int(fed["scale"]["github_parallel_cap"])
        created = 0
        for civ in civs:
            for team in range(1, teams + 1):
                for role in roles:
                    tid = task_id(mid, next_cycle, civ["id"], team, role)
                    if tid in q["tasks"]:
                        continue
                    shard = int(hashlib.sha256(tid.encode()).hexdigest(), 16) % shards
                    q["tasks"][tid] = {
                        "task_id": tid,
                        "mission_id": mid,
                        "cycle": next_cycle,
                        "civilization": civ["id"],
                        "civilization_name": civ["name"],
                        "team": team,
                        "role": role,
                        "shard": shard,
                        "priority": int(m.get("priority", 50)),
                        "status": "PENDING",
                        "attempt": 0,
                        "lease_owner": None,
                        "lease_expires_at": None,
                        "model_family": None,
                        "worker": None,
                        "result_ref": None,
                        "evidence_status": "UNREVIEWED",
                        "created_at": now_iso(),
                        "updated_at": now_iso(),
                    }
                    m.setdefault("task_ids", []).append(tid)
                    created += 1
        m["current_cycle"] = next_cycle
        m["status"] = "ACTIVE"
        m["last_longrun_expand_date"] = today
        m["updated_at"] = now_iso()
        q["event_seq"] = int(q.get("event_seq", 0)) + 1
        q.setdefault("events", []).append({
            "seq": q["event_seq"], "at": now_iso(), "kind": "LONGRUN_CYCLE_EXPANDED",
            "mission_id": mid, "cycle": next_cycle, "tasks_created": created,
        })
        q["events"] = q["events"][-2000:]
        report.update({"changed": True, "expanded": True, "new_cycle": next_cycle, "tasks_created": created, "reason": "EXPANDED"})

    if report["changed"]:
        q["updated_at"] = now_iso()
        m["updated_at"] = now_iso()
        atomic_write(QUEUE_PATH, q)
        write_latest(q)

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
