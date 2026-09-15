#!/usr/bin/env python3
"""Merge immutable shard JSONL artifacts into the persistent queue state.

Only this reducer mutates mission/task status after parallel execution, avoiding
20 concurrent writers to the same state file.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = ROOT / "state" / "mission-queue.json"
LATEST_PATH = ROOT / "state" / "latest-state.json"
TERMINAL = {"COMPLETED", "REJECTED", "CANCELLED"}


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def atomic_write(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def read_results(root: Path):
    rows = []
    for path in sorted(root.rglob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    row = json.loads(line)
                    row["_artifact_file"] = str(path)
                    rows.append(row)
                except Exception:
                    pass
    return rows


def update_mission(q, mission_id):
    m = q["missions"].get(mission_id)
    if not m:
        return
    tasks = [q["tasks"][tid] for tid in m.get("task_ids", []) if tid in q["tasks"]]
    if tasks and all(t.get("status") in TERMINAL for t in tasks):
        m["status"] = "CYCLE_COMPLETE" if int(m.get("current_cycle", 0)) < int(m.get("target_cycles", 1)) else "COMPLETED"
    elif tasks:
        m["status"] = "ACTIVE"
    m["updated_at"] = now_iso()


def count_attempts(row):
    """Return (attempts, successes, failures) without inventing hidden calls."""
    attempts = row.get("attempted_models")
    if isinstance(attempts, list):
        total = len(attempts)
        success = sum(1 for a in attempts if a.get("ok"))
        return total, success, total - success
    # Backward compatibility with pre-fallback shard artifacts.
    if row.get("model_id"):
        return 1, int(bool(row.get("ok"))), int(not bool(row.get("ok")))
    return 0, 0, 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--results-dir", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--summary", required=True)
    args = p.parse_args()

    q = load(QUEUE_PATH)
    rows = read_results(Path(args.results_dir))
    merged = 0
    ignored_smoke = 0
    successful_tasks = 0
    failed_tasks = 0
    deterministic_holds = 0
    quota_holds = 0
    external_attempts = 0
    successful_external_calls = 0
    failed_external_calls = 0
    touched_missions = set()

    for row in rows:
        att, succ, fail = count_attempts(row)
        external_attempts += att
        successful_external_calls += succ
        failed_external_calls += fail

        tid = row.get("task_id")
        if str(tid).startswith("SMOKE-"):
            ignored_smoke += 1
            continue
        t = q.get("tasks", {}).get(tid)
        if not t:
            continue
        status = row.get("execution_status")
        t["attempt"] = int(t.get("attempt", 0)) + 1
        t["model_family"] = row.get("model_family")
        t["worker"] = row.get("space")
        t["updated_at"] = now_iso()
        t["lease_owner"] = None
        t["lease_expires_at"] = None
        t["evidence_status"] = row.get("evidence_status", "UNREVIEWED")
        t["result_ref"] = f"actions://{args.run_id}/{row.get('_artifact_file')}#{tid}"
        if status == "COMPLETED" and row.get("ok"):
            t["status"] = "COMPLETED"
            successful_tasks += 1
        elif status == "HOLD_DETERMINISTIC_CHECK":
            t["status"] = "FAILED_RETRYABLE"
            deterministic_holds += 1
        elif status == "HOLD_QUOTA_BACKOFF":
            t["status"] = "FAILED_RETRYABLE"
            quota_holds += 1
        else:
            t["status"] = "FAILED_RETRYABLE"
            failed_tasks += 1
        touched_missions.add(t["mission_id"])
        merged += 1

    for mid in touched_missions:
        update_mission(q, mid)

    q["updated_at"] = now_iso()
    atomic_write(QUEUE_PATH, q)

    counts = {}
    for t in q.get("tasks", {}).values():
        counts[t.get("status", "UNKNOWN")] = counts.get(t.get("status", "UNKNOWN"), 0) + 1
    latest = {
        "schema": "cerebron-latest-state-v1",
        "updated_at": now_iso(),
        "mission_count": len(q.get("missions", {})),
        "task_count": len(q.get("tasks", {})),
        "task_status": counts,
        "active_missions": [mid for mid,m in q.get("missions", {}).items() if m.get("status") not in TERMINAL],
        "last_event_seq": q.get("event_seq", 0),
        "last_execution_run_id": str(args.run_id)
    }
    atomic_write(LATEST_PATH, latest)

    summary = {
        "schema": "cerebron-shard-run-summary-v2",
        "run_id": str(args.run_id),
        "at": now_iso(),
        "artifact_rows": len(rows),
        "merged_queue_tasks": merged,
        "smoke_rows": ignored_smoke,
        "successful_tasks": successful_tasks,
        "failed_tasks": failed_tasks,
        "deterministic_holds": deterministic_holds,
        "quota_holds": quota_holds,
        "external_call_attempts": external_attempts,
        "successful_external_calls": successful_external_calls,
        "failed_external_calls": failed_external_calls,
        "queue_status": counts,
    }
    atomic_write(Path(args.summary), summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
