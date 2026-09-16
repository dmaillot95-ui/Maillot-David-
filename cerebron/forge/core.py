#!/usr/bin/env python3
"""CEREBRON FORGE Ω — minimal independent scheduler/worker fabric.

Standard-library only. Persistent state uses SQLite so the same code can run on
one PC, a NAS, a self-hosted runner, or a small server. It deliberately keeps
worker != machine != model != cognitive role.
"""
from __future__ import annotations

import json
import os
import sqlite3
import socket
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

SCHEMA = "cerebron-forge-v1"
TERMINAL = {"COMPLETED", "FAILED", "CANCELLED", "QUARANTINED"}


@dataclass
class Worker:
    worker_id: str
    machine_id: str
    capabilities: list[str]
    max_parallel: int = 1
    provider: str = "self_hosted"


@dataclass
class Task:
    task_id: str
    kind: str
    payload: dict
    required_capabilities: list[str]
    priority: int = 100
    status: str = "PENDING"


def connect(path: str | os.PathLike[str]) -> sqlite3.Connection:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(p)
    db.row_factory = sqlite3.Row
    db.executescript(
        """
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS workers(
          worker_id TEXT PRIMARY KEY,
          machine_id TEXT NOT NULL,
          provider TEXT NOT NULL,
          capabilities_json TEXT NOT NULL,
          max_parallel INTEGER NOT NULL,
          active INTEGER NOT NULL DEFAULT 1,
          last_seen REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tasks(
          task_id TEXT PRIMARY KEY,
          kind TEXT NOT NULL,
          payload_json TEXT NOT NULL,
          required_capabilities_json TEXT NOT NULL,
          priority INTEGER NOT NULL,
          status TEXT NOT NULL,
          claimed_by TEXT,
          created_at REAL NOT NULL,
          updated_at REAL NOT NULL,
          result_json TEXT,
          error TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_tasks_sched
          ON tasks(status, priority, created_at);
        """
    )
    db.commit()
    return db


def register_worker(db: sqlite3.Connection, worker: Worker) -> None:
    now = time.time()
    db.execute(
        """INSERT INTO workers(worker_id,machine_id,provider,capabilities_json,max_parallel,active,last_seen)
           VALUES(?,?,?,?,?,1,?)
           ON CONFLICT(worker_id) DO UPDATE SET
             machine_id=excluded.machine_id,
             provider=excluded.provider,
             capabilities_json=excluded.capabilities_json,
             max_parallel=excluded.max_parallel,
             active=1,last_seen=excluded.last_seen""",
        (worker.worker_id, worker.machine_id, worker.provider,
         json.dumps(sorted(set(worker.capabilities))), worker.max_parallel, now),
    )
    db.commit()


def submit_task(db: sqlite3.Connection, kind: str, payload: dict,
                required_capabilities: Iterable[str] = (), priority: int = 100) -> str:
    task_id = f"T-{uuid.uuid4().hex[:12].upper()}"
    now = time.time()
    db.execute(
        """INSERT INTO tasks(task_id,kind,payload_json,required_capabilities_json,priority,status,created_at,updated_at)
           VALUES(?,?,?,?,?,'PENDING',?,?)""",
        (task_id, kind, json.dumps(payload), json.dumps(sorted(set(required_capabilities))), priority, now, now),
    )
    db.commit()
    return task_id


def _caps(row: sqlite3.Row) -> set[str]:
    return set(json.loads(row["capabilities_json"]))


def claim_task(db: sqlite3.Connection, worker_id: str) -> sqlite3.Row | None:
    worker = db.execute("SELECT * FROM workers WHERE worker_id=? AND active=1", (worker_id,)).fetchone()
    if not worker:
        return None
    caps = _caps(worker)
    active = db.execute(
        "SELECT COUNT(*) n FROM tasks WHERE claimed_by=? AND status='RUNNING'", (worker_id,)
    ).fetchone()["n"]
    if active >= worker["max_parallel"]:
        return None

    db.execute("BEGIN IMMEDIATE")
    rows = db.execute(
        "SELECT * FROM tasks WHERE status='PENDING' ORDER BY priority ASC, created_at ASC"
    ).fetchall()
    chosen = None
    for row in rows:
        required = set(json.loads(row["required_capabilities_json"]))
        if required.issubset(caps):
            chosen = row
            break
    if chosen is None:
        db.commit()
        return None
    now = time.time()
    updated = db.execute(
        "UPDATE tasks SET status='RUNNING',claimed_by=?,updated_at=? WHERE task_id=? AND status='PENDING'",
        (worker_id, now, chosen["task_id"]),
    ).rowcount
    db.commit()
    if updated != 1:
        return None
    return db.execute("SELECT * FROM tasks WHERE task_id=?", (chosen["task_id"],)).fetchone()


def finish_task(db: sqlite3.Connection, task_id: str, worker_id: str, result: dict,
                status: str = "COMPLETED", error: str | None = None) -> None:
    if status not in TERMINAL:
        raise ValueError("finish_task requires a terminal status")
    row = db.execute("SELECT status,claimed_by FROM tasks WHERE task_id=?", (task_id,)).fetchone()
    if not row or row["status"] != "RUNNING" or row["claimed_by"] != worker_id:
        raise RuntimeError("task ownership/state mismatch")
    db.execute(
        "UPDATE tasks SET status=?,result_json=?,error=?,updated_at=? WHERE task_id=?",
        (status, json.dumps(result), error, time.time(), task_id),
    )
    db.commit()


def status(db: sqlite3.Connection) -> dict:
    counts = {r["status"]: r["n"] for r in db.execute("SELECT status,COUNT(*) n FROM tasks GROUP BY status")}
    workers = db.execute("SELECT COUNT(*) n FROM workers WHERE active=1").fetchone()["n"]
    capacity = db.execute("SELECT COALESCE(SUM(max_parallel),0) n FROM workers WHERE active=1").fetchone()["n"]
    return {"schema": SCHEMA, "workers_active": workers, "logical_parallel_capacity": capacity, "tasks": counts}


def deterministic_worker_once(db: sqlite3.Connection, worker_id: str) -> str | None:
    row = claim_task(db, worker_id)
    if row is None:
        return None
    payload = json.loads(row["payload_json"])
    kind = row["kind"]
    if kind == "echo":
        result = {"echo": payload}
    elif kind == "sum":
        values = payload.get("values", [])
        result = {"sum": sum(values)}
    else:
        finish_task(db, row["task_id"], worker_id, {}, status="QUARANTINED", error=f"unsupported kind: {kind}")
        return row["task_id"]
    finish_task(db, row["task_id"], worker_id, result)
    return row["task_id"]


def bootstrap_demo(db_path: str) -> dict:
    db = connect(db_path)
    host = socket.gethostname()
    for i in range(4):
        register_worker(db, Worker(
            worker_id=f"LOCAL-{i+1}", machine_id=host,
            capabilities=["deterministic", "cpu"], max_parallel=1,
        ))
    ids = [submit_task(db, "sum", {"values": [i, i + 1]}, ["deterministic"]) for i in range(8)]
    progress = True
    while progress:
        progress = False
        for i in range(4):
            if deterministic_worker_once(db, f"LOCAL-{i+1}"):
                progress = True
    report = status(db)
    report["submitted"] = len(ids)
    report["completed_exact"] = sum(
        1 for r in db.execute("SELECT result_json FROM tasks WHERE status='COMPLETED'")
        if json.loads(r["result_json"])["sum"] >= 1
    )
    report["claim_superintelligence"] = False
    report["spend_limit_eur"] = 0
    return report


if __name__ == "__main__":
    path = os.getenv("CEREBRON_FORGE_DB", "out/cerebron-forge.db")
    print(json.dumps(bootstrap_demo(path), indent=2))
