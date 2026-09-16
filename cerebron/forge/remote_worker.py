#!/usr/bin/env python3
"""CEREBRON FORGE Ω — remote worker client.

Registers with the Forge server, claims one task at a time, executes deterministic
CPU-safe task kinds, and returns results. No paid APIs.
"""
from __future__ import annotations

import json
import os
import socket
import time
import urllib.request

BASE = os.getenv("CEREBRON_FORGE_URL", "http://127.0.0.1:8765").rstrip("/")
TOKEN = os.getenv("CEREBRON_FORGE_TOKEN", "")
WORKER_ID = os.getenv("CEREBRON_WORKER_ID", f"REMOTE-{socket.gethostname()}")
MACHINE_ID = os.getenv("CEREBRON_MACHINE_ID", socket.gethostname())
PROVIDER = os.getenv("CEREBRON_WORKER_PROVIDER", "self_hosted")
CAPS = [x for x in os.getenv("CEREBRON_WORKER_CAPS", "deterministic,cpu").split(",") if x]
MAX_PARALLEL = int(os.getenv("CEREBRON_WORKER_MAX_PARALLEL", "1"))


def post(path: str, data: dict) -> dict:
    headers = {"Content-Type": "application/json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(BASE + path, data=json.dumps(data).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def register():
    return post("/register", {
        "worker_id": WORKER_ID,
        "machine_id": MACHINE_ID,
        "provider": PROVIDER,
        "capabilities": CAPS,
        "max_parallel": MAX_PARALLEL,
    })


def execute(task: dict) -> tuple[str, dict, str | None]:
    kind = task["kind"]
    payload = task.get("payload") or json.loads(task.get("payload_json", "{}"))
    if kind == "sum":
        return "COMPLETED", {"sum": sum(payload.get("values", []))}, None
    if kind == "echo":
        return "COMPLETED", {"echo": payload}, None
    return "QUARANTINED", {}, f"unsupported kind: {kind}"


def once() -> bool:
    claimed = post("/claim", {"worker_id": WORKER_ID})
    task = claimed.get("task")
    if not task:
        return False
    status, result, error = execute(task)
    post("/finish", {
        "worker_id": WORKER_ID,
        "task_id": task["task_id"],
        "status": status,
        "result": result,
        "error": error,
    })
    return True


def main():
    register()
    idle_rounds = int(os.getenv("CEREBRON_WORKER_IDLE_ROUNDS", "3"))
    sleep_s = float(os.getenv("CEREBRON_WORKER_SLEEP_S", "0.1"))
    idle = 0
    completed = 0
    while idle < idle_rounds:
        if once():
            completed += 1
            idle = 0
        else:
            idle += 1
            time.sleep(sleep_s)
    print(json.dumps({"worker_id": WORKER_ID, "completed": completed, "ok": True}))


if __name__ == "__main__":
    main()
