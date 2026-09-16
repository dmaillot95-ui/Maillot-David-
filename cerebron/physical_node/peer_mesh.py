#!/usr/bin/env python3
"""CEREBRON Ω peer mesh for autonomous physical nodes.

Zero-euro, local-first task exchange. Nodes exchange signed-like hash envelopes
through a shared directory transport by default (NFS, Syncthing, USB, mounted
folder, or CI artifact staging). Transport is intentionally pluggable.

This module does NOT create physical machines. It lets existing machines publish,
claim, execute and return tasks while preserving node-local autonomy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import time
import uuid
from pathlib import Path

ROOT = Path(os.getenv("CEREBRON_NODE_ROOT", str(Path.home() / ".cerebron-node")))
MESH = Path(os.getenv("CEREBRON_MESH_ROOT", str(ROOT / "mesh")))
NODE_ID = os.getenv("CEREBRON_NODE_ID", f"PN-{hashlib.sha256(socket.gethostname().encode()).hexdigest()[:16]}")
SPEND_LIMIT_EUR = 0


def ensure_dirs() -> None:
    for name in ("inbox", "claims", "results", "peers", "archive"):
        (MESH / name).mkdir(parents=True, exist_ok=True)


def canon(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def seal(payload: dict) -> dict:
    body = dict(payload)
    body["spend_limit_eur"] = 0
    body["paid_fallback"] = False
    digest = hashlib.sha256(canon(body)).hexdigest()
    return {"body": body, "sha256": digest}


def verify(env: dict) -> bool:
    return isinstance(env, dict) and env.get("sha256") == hashlib.sha256(canon(env.get("body", {}))).hexdigest()


def atomic_write(path: Path, obj: dict) -> None:
    tmp = path.with_suffix(path.suffix + f".{uuid.uuid4().hex}.tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def heartbeat() -> dict:
    ensure_dirs()
    p = {
        "node_id": NODE_ID,
        "host": socket.gethostname(),
        "ts": time.time(),
        "cpu_count": os.cpu_count() or 1,
        "capabilities": ["CALC", "FANOUT", "LOCAL_LLM_OPTIONAL"],
    }
    env = seal(p)
    atomic_write(MESH / "peers" / f"{NODE_ID}.json", env)
    return env


def publish(kind: str, payload: dict, priority: int = 100, target: str | None = None) -> dict:
    ensure_dirs()
    task_id = f"MT-{uuid.uuid4().hex[:16]}"
    body = {
        "task_id": task_id,
        "source_node": NODE_ID,
        "target_node": target,
        "kind": kind,
        "payload": payload,
        "priority": int(priority),
        "created_at": time.time(),
        "state": "PUBLISHED",
    }
    env = seal(body)
    atomic_write(MESH / "inbox" / f"{priority:06d}-{task_id}.json", env)
    return env


def _eligible(body: dict) -> bool:
    tgt = body.get("target_node")
    return tgt in (None, "", NODE_ID) and body.get("source_node") != NODE_ID


def claim_one() -> dict | None:
    ensure_dirs()
    for path in sorted((MESH / "inbox").glob("*.json")):
        try:
            env = json.loads(path.read_text(encoding="utf-8"))
            if not verify(env):
                continue
            body = env["body"]
            if not _eligible(body):
                continue
            claim_path = MESH / "claims" / f"{body['task_id']}.json"
            try:
                fd = os.open(claim_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            except FileExistsError:
                continue
            claim = seal({
                "task_id": body["task_id"],
                "claimed_by": NODE_ID,
                "claimed_at": time.time(),
                "source_node": body["source_node"],
            })
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(claim, fh, indent=2, ensure_ascii=False)
            return env
        except Exception:
            continue
    return None


def submit_result(task_env: dict, result: dict) -> dict:
    ensure_dirs()
    body = task_env["body"]
    out = seal({
        "task_id": body["task_id"],
        "source_node": body["source_node"],
        "executed_by": NODE_ID,
        "kind": body["kind"],
        "result": result,
        "completed_at": time.time(),
    })
    atomic_write(MESH / "results" / f"{body['task_id']}.json", out)
    return out


def list_peers(max_age_s: float = 120.0) -> list[dict]:
    ensure_dirs()
    now = time.time()
    peers = []
    for p in (MESH / "peers").glob("*.json"):
        try:
            env = json.loads(p.read_text(encoding="utf-8"))
            if verify(env) and now - float(env["body"].get("ts", 0)) <= max_age_s:
                peers.append(env["body"])
        except Exception:
            pass
    return sorted(peers, key=lambda x: x["node_id"])


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("heartbeat")
    p = sub.add_parser("publish")
    p.add_argument("kind")
    p.add_argument("payload_json")
    p.add_argument("--priority", type=int, default=100)
    p.add_argument("--target")
    sub.add_parser("claim")
    sub.add_parser("peers")
    r = sub.add_parser("result")
    r.add_argument("task_file")
    r.add_argument("result_json")
    args = ap.parse_args()

    if args.cmd == "heartbeat":
        print(json.dumps(heartbeat(), ensure_ascii=False))
    elif args.cmd == "publish":
        print(json.dumps(publish(args.kind, json.loads(args.payload_json), args.priority, args.target), ensure_ascii=False))
    elif args.cmd == "claim":
        print(json.dumps(claim_one(), ensure_ascii=False))
    elif args.cmd == "peers":
        print(json.dumps(list_peers(), ensure_ascii=False))
    elif args.cmd == "result":
        env = json.loads(Path(args.task_file).read_text(encoding="utf-8"))
        if not verify(env):
            raise SystemExit("invalid task envelope")
        print(json.dumps(submit_result(env, json.loads(args.result_json)), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
