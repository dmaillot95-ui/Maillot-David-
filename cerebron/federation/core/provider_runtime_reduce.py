#!/usr/bin/env python3
"""Aggregate shard JSONL results into persistent CEREBRON provider runtime state.

This reducer is deterministic, zero-euro, and never enables a provider. It only
updates observed success/failure/quota/latency statistics used by provider_router.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTING_DIR = ROOT / "routing"
import sys
sys.path.insert(0, str(ROUTING_DIR))
from provider_router import load_state, save_state, record_result, snapshot


def iter_jsonl(paths: list[Path]):
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--state", required=True)
    p.add_argument("--results", nargs="+", required=True)
    p.add_argument("--output")
    args = p.parse_args()

    state_path = Path(args.state)
    state = load_state(state_path)
    seen = 0
    for row in iter_jsonl([Path(x) for x in args.results]):
        attempts = row.get("attempted_models") or []
        for a in attempts:
            route = a.get("provider")
            if not route:
                continue
            retry_after = a.get("retry_after")
            try:
                retry_after_s = float(retry_after) if retry_after not in (None, "") else None
            except Exception:
                retry_after_s = None
            record_result(
                state,
                route,
                ok=bool(a.get("ok")),
                error_type=a.get("error_type"),
                latency_ms=a.get("latency_ms"),
                retry_after_seconds=retry_after_s,
                now=time.time(),
            )
            seen += 1

    save_state(state_path, state)
    out = {
        "schema": "cerebron-provider-runtime-reduce-v1",
        "attempts_observed": seen,
        "state_path": str(state_path),
        "snapshot": snapshot(state, state.get("providers", {}).keys()),
    }
    if args.output:
        Path(args.output).write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
