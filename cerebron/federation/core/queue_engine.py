#!/usr/bin/env python3
"""CÉRÉBRON Ω federation queue/state engine.

Standard-library-only control-plane component. It does not perform inference.
It creates deterministic 12x10x12 agent tasks, leases them to shards, records
results/failures, recovers expired leases, and exposes compact status.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "federation-v1.json"
STATE_DIR = ROOT / "state"
QUEUE_PATH = STATE_DIR / "mission-queue.json"
LATEST_PATH = STATE_DIR / "latest-state.json"

TERMINAL = {"COMPLETED", "REJECTED", "CANCELLED"}
ACTIVE = {"PENDING", "LEASED", "RUNNING", "FAILED_RETRYABLE"}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def config():
    return load_json(CONFIG_PATH, {})


def empty_queue():
    return {
        "schema": "cerebron-mission-queue-v1",
        "updated_at": now_iso(),
        "missions": {},
        "tasks": {},
        "event_seq": 0,
        "events": [],
    }


def queue():
    q = load_json(QUEUE_PATH, empty_queue())
    q.setdefault("missions", {})
    q.setdefault("tasks", {})
    q.setdefault("events", [])
    q.setdefault("event_seq", 0)
    return q


def event(q, kind: str, **fields):
    q["event_seq"] += 1
    item = {"seq": q["event_seq"], "at": now_iso(), "kind": kind, **fields}
    q["events"].append(item)
    # Keep the control-plane file bounded; detailed outputs live in artifacts/ledgers.
    q["events"] = q["events"][-2000:]


def save(q):
    q["updated_at"] = now_iso()
    atomic_write(QUEUE_PATH, q)
    write_latest(q)


def write_latest(q):
    counts = {}
    for t in q["tasks"].values():
        counts[t["status"]] = counts.get(t["status"], 0) + 1
    missions = list(q["missions"].values())
    latest = {
        "schema": "cerebron-latest-state-v1",
        "updated_at": now_iso(),
        "mission_count": len(missions),
        "task_count": len(q["tasks"]),
        "task_status": counts,
        "active_missions": [m["mission_id"] for m in missions if m["status"] not in TERMINAL],
        "last_event_seq": q.get("event_seq", 0),
    }
    atomic_write(LATEST_PATH, latest)


def new_mission(title: str, objective: str, priority: int, cycles: int):
    q = queue()
    mission_id = "M-" + uuid.uuid4().hex[:12].upper()
    m = {
        "mission_id": mission_id,
        "title": title,
        "objective": objective,
        "priority": int(priority),
        "target_cycles": int(cycles),
        "current_cycle": 0,
        "status": "QUEUED",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "task_ids": [],
    }
    q["missions"][mission_id] = m
    event(q, "MISSION_ENQUEUED", mission_id=mission_id, priority=int(priority))
    save(q)
    return mission_id


def deterministic_task_id(mission_id: str, cycle: int, civ: str, team: int, role: str) -> str:
    raw = f"{mission_id}|{cycle}|{civ}|{team}|{role}".encode()
    return "T-" + hashlib.sha256(raw).hexdigest()[:20].upper()


def expand(mission_id: str, cycle: int | None = None):
    q = queue()
    cfg = config()
    m = q["missions"].get(mission_id)
    if not m:
        raise SystemExit(f"Unknown mission: {mission_id}")
    cycle = int(cycle or (m["current_cycle"] + 1))
    if cycle > m["target_cycles"]:
        raise SystemExit("Target cycle limit reached")
    roles = cfg["team_template"]["roles"]
    civs = cfg["civilizations"]
    teams = int(cfg["scale"]["teams_per_civilization"])
    created = 0
    for civ in civs:
        for team in range(1, teams + 1):
            for role in roles:
                tid = deterministic_task_id(mission_id, cycle, civ["id"], team, role)
                if tid in q["tasks"]:
                    continue
                shard = int(hashlib.sha256(tid.encode()).hexdigest(), 16) % int(cfg["scale"]["github_parallel_cap"])
                q["tasks"][tid] = {
                    "task_id": tid,
                    "mission_id": mission_id,
                    "cycle": cycle,
                    "civilization": civ["id"],
                    "civilization_name": civ["name"],
                    "team": team,
                    "role": role,
                    "shard": shard,
                    "priority": m["priority"],
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
                m["task_ids"].append(tid)
                created += 1
    m["current_cycle"] = max(m["current_cycle"], cycle)
    m["status"] = "ACTIVE"
    m["updated_at"] = now_iso()
    event(q, "MISSION_EXPANDED", mission_id=mission_id, cycle=cycle, tasks_created=created)
    save(q)
    return created


def lease(shard: int, owner: str, limit: int, minutes: int):
    q = queue()
    recover_in_memory(q)
    candidates = [
        t for t in q["tasks"].values()
        if t["shard"] == shard and t["status"] in {"PENDING", "FAILED_RETRYABLE"}
    ]
    candidates.sort(key=lambda t: (-int(t["priority"]), t["created_at"], t["task_id"]))
    chosen = candidates[: int(limit)]
    expiry = (datetime.now(timezone.utc) + timedelta(minutes=int(minutes))).replace(microsecond=0).isoformat()
    for t in chosen:
        t["status"] = "LEASED"
        t["attempt"] += 1
        t["lease_owner"] = owner
        t["lease_expires_at"] = expiry
        t["updated_at"] = now_iso()
        event(q, "TASK_LEASED", task_id=t["task_id"], owner=owner, attempt=t["attempt"])
    save(q)
    return chosen


def recover_in_memory(q):
    now = datetime.now(timezone.utc)
    recovered = 0
    for t in q["tasks"].values():
        if t["status"] in {"LEASED", "RUNNING"} and t.get("lease_expires_at"):
            if parse_iso(t["lease_expires_at"]) < now:
                t["status"] = "FAILED_RETRYABLE"
                t["lease_owner"] = None
                t["lease_expires_at"] = None
                t["updated_at"] = now_iso()
                recovered += 1
                event(q, "LEASE_EXPIRED", task_id=t["task_id"])
    return recovered


def recover():
    q = queue()
    n = recover_in_memory(q)
    save(q)
    return n


def mark(task_id: str, status: str, owner: str | None = None, model: str | None = None,
         worker: str | None = None, result_ref: str | None = None, evidence: str | None = None):
    q = queue()
    t = q["tasks"].get(task_id)
    if not t:
        raise SystemExit(f"Unknown task: {task_id}")
    allowed = {"RUNNING", "COMPLETED", "FAILED_RETRYABLE", "REJECTED", "CANCELLED"}
    if status not in allowed:
        raise SystemExit(f"Invalid status: {status}")
    if owner and t.get("lease_owner") not in {None, owner}:
        raise SystemExit("Lease owner mismatch")
    t["status"] = status
    if owner: t["lease_owner"] = owner
    if model: t["model_family"] = model
    if worker: t["worker"] = worker
    if result_ref: t["result_ref"] = result_ref
    if evidence: t["evidence_status"] = evidence
    if status in TERMINAL or status == "FAILED_RETRYABLE":
        t["lease_expires_at"] = None
    t["updated_at"] = now_iso()
    event(q, "TASK_STATUS", task_id=task_id, status=status, model_family=t.get("model_family"))
    update_mission_status(q, t["mission_id"])
    save(q)


def update_mission_status(q, mission_id: str):
    m = q["missions"][mission_id]
    tasks = [q["tasks"][tid] for tid in m["task_ids"] if tid in q["tasks"]]
    if tasks and all(t["status"] in TERMINAL for t in tasks):
        m["status"] = "CYCLE_COMPLETE" if m["current_cycle"] < m["target_cycles"] else "COMPLETED"
    elif any(t["status"] in ACTIVE for t in tasks):
        m["status"] = "ACTIVE"
    m["updated_at"] = now_iso()


def status(mission_id: str | None = None):
    q = queue()
    tasks = list(q["tasks"].values())
    if mission_id:
        tasks = [t for t in tasks if t["mission_id"] == mission_id]
    counts = {}
    by_civ = {}
    by_shard = {}
    for t in tasks:
        counts[t["status"]] = counts.get(t["status"], 0) + 1
        by_civ.setdefault(t["civilization"], {}).setdefault(t["status"], 0)
        by_civ[t["civilization"]][t["status"]] += 1
        by_shard.setdefault(str(t["shard"]), {}).setdefault(t["status"], 0)
        by_shard[str(t["shard"])][t["status"]] += 1
    return {
        "updated_at": q["updated_at"],
        "mission_id": mission_id,
        "tasks": len(tasks),
        "status": counts,
        "by_civilization": by_civ,
        "by_shard": by_shard,
        "last_event_seq": q.get("event_seq", 0),
    }


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    enq = sub.add_parser("enqueue")
    enq.add_argument("--title", required=True); enq.add_argument("--objective", required=True)
    enq.add_argument("--priority", type=int, default=50); enq.add_argument("--cycles", type=int, default=10)
    exp = sub.add_parser("expand"); exp.add_argument("mission_id"); exp.add_argument("--cycle", type=int)
    lea = sub.add_parser("lease"); lea.add_argument("--shard", type=int, required=True); lea.add_argument("--owner", required=True)
    lea.add_argument("--limit", type=int, default=1); lea.add_argument("--minutes", type=int, default=30)
    rec = sub.add_parser("recover")
    sta = sub.add_parser("status"); sta.add_argument("--mission-id")
    mar = sub.add_parser("mark"); mar.add_argument("task_id"); mar.add_argument("--status", required=True)
    mar.add_argument("--owner"); mar.add_argument("--model"); mar.add_argument("--worker"); mar.add_argument("--result-ref"); mar.add_argument("--evidence")
    args = p.parse_args()

    if args.cmd == "init":
        q = queue(); save(q); print(json.dumps(status(), ensure_ascii=False, indent=2))
    elif args.cmd == "enqueue":
        mid = new_mission(args.title, args.objective, args.priority, args.cycles); print(mid)
    elif args.cmd == "expand":
        print(expand(args.mission_id, args.cycle))
    elif args.cmd == "lease":
        print(json.dumps(lease(args.shard, args.owner, args.limit, args.minutes), ensure_ascii=False, indent=2))
    elif args.cmd == "recover":
        print(recover())
    elif args.cmd == "status":
        print(json.dumps(status(args.mission_id), ensure_ascii=False, indent=2))
    elif args.cmd == "mark":
        mark(args.task_id, args.status, args.owner, args.model, args.worker, args.result_ref, args.evidence); print("OK")


if __name__ == "__main__":
    main()
