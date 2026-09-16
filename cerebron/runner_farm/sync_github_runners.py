#!/usr/bin/env python3
"""Synchronize the physical runner registry from GitHub's self-hosted runner API.

Only repository self-hosted runners carrying both `cerebron` and `physical` labels
are counted as CEREBRON physical capacity. GitHub-hosted jobs, logical lanes and
matrix entries are never counted.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

TARGET = 432


def api_get(url: str, token: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "cerebron-runner-farm-audit",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_all(repo: str, token: str) -> list[dict]:
    rows: list[dict] = []
    page = 1
    while True:
        q = urllib.parse.urlencode({"per_page": 100, "page": page})
        data = api_get(f"https://api.github.com/repos/{repo}/actions/runners?{q}", token)
        batch = data.get("runners", [])
        rows.extend(batch)
        if len(batch) < 100:
            break
        page += 1
        if page > 20:
            raise RuntimeError("Unexpected runner pagination > 2000 entries")
    return rows


def labels(row: dict) -> set[str]:
    return {str(x.get("name", "")).lower() for x in row.get("labels", [])}


def main() -> None:
    repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not repo or not token:
        raise SystemExit("GITHUB_REPOSITORY and GITHUB_TOKEN are required")

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    raw = fetch_all(repo, token)
    physical = [r for r in raw if {"cerebron", "physical"}.issubset(labels(r))]

    registry = {"schema": "cerebron-runner-registry-v2", "source": "github-self-hosted-runners-api", "verified_at": now, "target_physical_runners": TARGET, "runners": {}}
    for r in physical:
        rid = str(r.get("id"))
        registry["runners"][rid] = {
            "github_runner_id": r.get("id"),
            "name": r.get("name"),
            "os": r.get("os"),
            "status": r.get("status"),
            "busy": bool(r.get("busy")),
            "labels": sorted(labels(r)),
            "verified_at": now,
            "source": "github-self-hosted-runners-api",
        }

    online = sorted(rid for rid, r in registry["runners"].items() if r.get("status") == "online")
    offline = sorted(rid for rid, r in registry["runners"].items() if r.get("status") != "online")
    busy = sorted(rid for rid, r in registry["runners"].items() if r.get("status") == "online" and r.get("busy"))
    idle = sorted(rid for rid, r in registry["runners"].items() if r.get("status") == "online" and not r.get("busy"))
    status = {
        "schema": "cerebron-runner-farm-status-v2",
        "source": "github-self-hosted-runners-api",
        "verified_at": now,
        "registered_physical_runners": len(registry["runners"]),
        "online_physical_runners": len(online),
        "busy_physical_runners": len(busy),
        "idle_physical_runners": len(idle),
        "offline_physical_runners": len(offline),
        "target_physical_runners": TARGET,
        "gap_to_432_online": max(0, TARGET - len(online)),
        "online_runner_ids": online,
        "busy_runner_ids": busy,
        "idle_runner_ids": idle,
        "offline_runner_ids": offline,
        "runners": registry["runners"],
    }

    root = Path("cerebron/runner_farm/state")
    root.mkdir(parents=True, exist_ok=True)
    (root / "runner-registry.json").write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (root / "runner-farm-status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: status[k] for k in ("registered_physical_runners", "online_physical_runners", "busy_physical_runners", "idle_physical_runners", "offline_physical_runners", "gap_to_432_online")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
