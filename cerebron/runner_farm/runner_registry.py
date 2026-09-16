#!/usr/bin/env python3
"""CEREBRON OMEGA physical runner registry.

Counts only distinct physical/self-hosted runner identities that have produced a
recent heartbeat. Logical lanes, matrix jobs and planned workers never count as
physical runners.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def parse_ts(value: str):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def load(path: Path):
    if not path.exists():
        return {"schema": "cerebron-runner-registry-v1", "runners": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def status_snapshot(registry: dict, stale_seconds: int = 180):
    now = datetime.now(timezone.utc)
    runners = registry.get("runners", {})
    physical = {}
    for rid, row in runners.items():
        last = row.get("last_heartbeat")
        online = False
        if last:
            try:
                online = (now - parse_ts(last)).total_seconds() <= stale_seconds
            except Exception:
                online = False
        physical[rid] = {**row, "online": online}
    online = [rid for rid, row in physical.items() if row["online"]]
    offline = [rid for rid, row in physical.items() if not row["online"]]
    return {
        "schema": "cerebron-runner-farm-status-v1",
        "at": now.replace(microsecond=0).isoformat(),
        "registered_physical_runners": len(physical),
        "online_physical_runners": len(online),
        "offline_physical_runners": len(offline),
        "target_physical_runners": 432,
        "gap_to_432_online": max(0, 432 - len(online)),
        "online_runner_ids": sorted(online),
        "offline_runner_ids": sorted(offline),
        "runners": physical,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--registry", default="cerebron/runner_farm/state/runner-registry.json")
    p.add_argument("--output", default="cerebron/runner_farm/state/runner-farm-status.json")
    p.add_argument("--stale-seconds", type=int, default=180)
    args = p.parse_args()
    reg = load(Path(args.registry))
    out = status_snapshot(reg, args.stale_seconds)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in (
        "registered_physical_runners", "online_physical_runners",
        "offline_physical_runners", "target_physical_runners", "gap_to_432_online"
    )}, ensure_ascii=False))


if __name__ == "__main__":
    main()
