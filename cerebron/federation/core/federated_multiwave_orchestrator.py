#!/usr/bin/env python3
"""CÉRÉBRON Ω persistent multi-wave orchestrator.

Purpose:
- allocate at most physical_cap logical addresses per wave;
- choose active missions by explicit priority;
- never dispatch the same (mission, address) twice unless retry is explicitly requested;
- persist cursors, inflight assignments, completions and bounded history;
- resume deterministically after process interruption;
- keep logical addressability separate from physical concurrency.

This module only schedules work. It does not claim an inference occurred.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from federated_scheduler import load_topology, addresses

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TOPOLOGY = ROOT / "topology" / "federated-hubs-10000.json"
DEFAULT_STATE = ROOT / "state" / "federated-multiwave-state.json"
DEFAULT_CONTROL = ROOT / "state" / "federated-missions.json"
HISTORY_LIMIT = 500


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def fresh_state(total: int, cap: int) -> dict:
    return {
        "schema": "cerebron-federated-multiwave-state-v1",
        "logical_total": total,
        "physical_cap": cap,
        "wave_number": 0,
        "missions": {},
        "inflight": {},
        "completed": {},
        "failed": {},
        "history": [],
        "last_wave": [],
    }


def ensure_state(cfg: dict, state: dict) -> dict:
    total = len(addresses(cfg))
    cap = int(cfg.get("physical_parallel_cap", cfg.get("physical_concurrency_cap", 20)))
    if not isinstance(state, dict) or state.get("schema") != "cerebron-federated-multiwave-state-v1":
        return fresh_state(total, cap)
    state["logical_total"] = total
    state["physical_cap"] = cap
    state.setdefault("wave_number", 0)
    state.setdefault("missions", {})
    state.setdefault("inflight", {})
    state.setdefault("completed", {})
    state.setdefault("failed", {})
    state.setdefault("history", [])
    state.setdefault("last_wave", [])
    return state


def normalize_control(control: dict) -> list[dict]:
    missions = []
    for m in control.get("missions", []):
        if not m.get("enabled", True):
            continue
        mid = str(m.get("mission_id") or "").strip()
        if not mid:
            continue
        missions.append({
            "mission_id": mid,
            "priority": int(m.get("priority", 0)),
            "max_addresses": m.get("max_addresses"),
            "enabled": True,
        })
    missions.sort(key=lambda m: (-m["priority"], m["mission_id"]))
    return missions


def _mission_state(state: dict, mission: dict) -> dict:
    mid = mission["mission_id"]
    ms = state["missions"].setdefault(mid, {
        "priority": mission["priority"],
        "cursor": 0,
        "round": 0,
        "dispatched_count": 0,
        "completed_count": 0,
        "failed_count": 0,
        "status": "ACTIVE",
    })
    ms["priority"] = mission["priority"]
    return ms


def assignment_id(mission_id: str, address: str) -> str:
    return f"{mission_id}|{address}"


def _already_seen(state: dict, aid: str) -> bool:
    return aid in state["inflight"] or aid in state["completed"] or aid in state["failed"]


def mission_remaining_capacity(state: dict, mission: dict) -> int:
    ms = _mission_state(state, mission)
    max_addresses = mission.get("max_addresses")
    hard = int(state["logical_total"]) if max_addresses in (None, 0) else min(int(max_addresses), int(state["logical_total"]))
    used = int(ms.get("dispatched_count", 0))
    return max(0, hard - used)


def select_mission(state: dict, missions: list[dict]) -> dict | None:
    candidates = []
    for mission in missions:
        ms = _mission_state(state, mission)
        if ms.get("status") != "ACTIVE":
            continue
        remaining = mission_remaining_capacity(state, mission)
        if remaining <= 0:
            ms["status"] = "EXHAUSTED"
            continue
        inflight = sum(1 for x in state["inflight"].values() if x.get("mission_id") == mission["mission_id"])
        candidates.append((mission["priority"], -inflight, mission["mission_id"], mission))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (-x[0], -x[1], x[2]))
    return candidates[0][3]


def next_wave(cfg: dict, state: dict, control: dict, wave_size: int | None = None) -> list[dict]:
    addrs = addresses(cfg)
    if not addrs:
        state["last_wave"] = []
        return []
    missions = normalize_control(control)
    cap = min(int(state["physical_cap"]), len(addrs))
    target = min(int(wave_size or cap), cap)
    out: list[dict] = []

    while len(out) < target:
        mission = select_mission(state, missions)
        if mission is None:
            break
        mid = mission["mission_id"]
        ms = _mission_state(state, mission)
        start = int(ms.get("cursor", 0)) % len(addrs)
        chosen = None
        for offset in range(len(addrs)):
            idx = (start + offset) % len(addrs)
            addr = addrs[idx].key
            aid = assignment_id(mid, addr)
            if _already_seen(state, aid):
                continue
            chosen = (idx, addr, aid)
            break
        if chosen is None:
            ms["status"] = "EXHAUSTED"
            continue

        idx, addr, aid = chosen
        record = {
            "assignment_id": aid,
            "mission_id": mid,
            "priority": mission["priority"],
            "address": addr,
            "logical_index": idx,
            "physical_lane": len(out),
            "wave_number": int(state["wave_number"]),
            "status": "DISPATCHED",
        }
        out.append(record)
        state["inflight"][aid] = dict(record)
        ms["dispatched_count"] = int(ms.get("dispatched_count", 0)) + 1
        ms["cursor"] = (idx + 1) % len(addrs)
        if ms["cursor"] == 0:
            ms["round"] = int(ms.get("round", 0)) + 1

    state["last_wave"] = out
    if out:
        state["wave_number"] = int(state["wave_number"]) + 1
        state["history"].append({
            "wave_number": out[0]["wave_number"],
            "assignments": [x["assignment_id"] for x in out],
        })
        state["history"] = state["history"][-HISTORY_LIMIT:]
    return out


def mark_terminal(state: dict, assignment_ids: Iterable[str], status: str) -> None:
    if status not in {"COMPLETED", "FAILED"}:
        raise ValueError(status)
    bucket = state["completed"] if status == "COMPLETED" else state["failed"]
    for aid in assignment_ids:
        info = state["inflight"].pop(aid, None)
        if not info:
            continue
        info["status"] = status
        bucket[aid] = info
        ms = state["missions"].get(info["mission_id"], {})
        key = "completed_count" if status == "COMPLETED" else "failed_count"
        ms[key] = int(ms.get(key, 0)) + 1


def requeue_failed(state: dict, assignment_ids: Iterable[str]) -> int:
    """Explicit retry escape hatch. Removes FAILED dedup lock for selected assignments."""
    count = 0
    for aid in assignment_ids:
        info = state["failed"].pop(aid, None)
        if not info:
            continue
        ms = state["missions"].get(info["mission_id"], {})
        ms["failed_count"] = max(0, int(ms.get("failed_count", 0)) - 1)
        ms["dispatched_count"] = max(0, int(ms.get("dispatched_count", 0)) - 1)
        ms["status"] = "ACTIVE"
        count += 1
    return count


def summary(state: dict) -> dict:
    return {
        "logical_total": state.get("logical_total"),
        "physical_cap": state.get("physical_cap"),
        "wave_number": state.get("wave_number"),
        "inflight": len(state.get("inflight", {})),
        "completed": len(state.get("completed", {})),
        "failed": len(state.get("failed", {})),
        "last_wave_size": len(state.get("last_wave", [])),
        "missions": state.get("missions", {}),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--topology", default=str(DEFAULT_TOPOLOGY))
    p.add_argument("--state", default=str(DEFAULT_STATE))
    p.add_argument("--control", default=str(DEFAULT_CONTROL))
    p.add_argument("--wave-size", type=int)
    p.add_argument("--complete", nargs="*")
    p.add_argument("--fail", nargs="*")
    p.add_argument("--retry", nargs="*")
    args = p.parse_args()

    cfg = load_topology(Path(args.topology))
    state_path = Path(args.state)
    state = ensure_state(cfg, load_json(state_path, {}))
    if args.complete:
        mark_terminal(state, args.complete, "COMPLETED")
    if args.fail:
        mark_terminal(state, args.fail, "FAILED")
    if args.retry:
        requeue_failed(state, args.retry)
    control = load_json(Path(args.control), {"missions": []})
    wave = next_wave(cfg, state, control, args.wave_size)
    save_json(state_path, state)
    print(json.dumps({"wave": wave, "summary": summary(state)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
