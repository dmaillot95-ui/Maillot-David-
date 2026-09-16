#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from federated_scheduler import load_topology, addresses

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TOPOLOGY = ROOT / "topology" / "federated-hubs-10000.json"
DEFAULT_STATE = ROOT / "state" / "federated-dispatch-state.json"


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


def fresh_state(total: int, physical_cap: int) -> dict:
    return {
        "schema": "cerebron-federated-dispatch-state-v1",
        "cursor": 0,
        "round": 0,
        "logical_total": total,
        "physical_cap": physical_cap,
        "mission_id": None,
        "assignments": {},
        "completed": {},
        "last_wave": [],
    }


def ensure_state(cfg: dict, state: dict) -> dict:
    total = len(addresses(cfg))
    cap = int(cfg.get("physical_parallel_cap", cfg.get("physical_concurrency_cap", 20)))
    if not isinstance(state, dict) or state.get("schema") != "cerebron-federated-dispatch-state-v1":
        return fresh_state(total, cap)
    state["logical_total"] = total
    state["physical_cap"] = cap
    state.setdefault("cursor", 0)
    state.setdefault("round", 0)
    state.setdefault("assignments", {})
    state.setdefault("completed", {})
    state.setdefault("last_wave", [])
    return state


def next_wave(cfg: dict, state: dict, mission_id: str, wave_size: int | None = None) -> list[dict]:
    addrs = addresses(cfg)
    if not addrs:
        return []
    cap = int(state["physical_cap"])
    size = min(wave_size or cap, cap, len(addrs))
    cursor = int(state["cursor"]) % len(addrs)
    out = []
    for i in range(size):
        idx = (cursor + i) % len(addrs)
        addr = addrs[idx]
        key = addr.key
        out.append({
            "address": key,
            "mission_id": mission_id,
            "round": int(state["round"]),
            "logical_index": idx,
            "status": "DISPATCHED",
        })
        state["assignments"][key] = {
            "mission_id": mission_id,
            "round": int(state["round"]),
            "logical_index": idx,
            "status": "DISPATCHED",
        }
    state["mission_id"] = mission_id
    state["last_wave"] = out
    state["cursor"] = (cursor + size) % len(addrs)
    if state["cursor"] == 0:
        state["round"] = int(state["round"]) + 1
    return out


def mark_completed(state: dict, addresses_done: Iterable[str]) -> None:
    for key in addresses_done:
        info = state.get("assignments", {}).get(key)
        if not info:
            continue
        info["status"] = "COMPLETED"
        state.setdefault("completed", {})[key] = {
            "mission_id": info.get("mission_id"),
            "round": info.get("round"),
            "logical_index": info.get("logical_index"),
        }


def summary(state: dict) -> dict:
    return {
        "mission_id": state.get("mission_id"),
        "logical_total": state.get("logical_total"),
        "physical_cap": state.get("physical_cap"),
        "cursor": state.get("cursor"),
        "round": state.get("round"),
        "assigned_unique": len(state.get("assignments", {})),
        "completed_unique": len(state.get("completed", {})),
        "last_wave_size": len(state.get("last_wave", [])),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--topology", default=str(DEFAULT_TOPOLOGY))
    p.add_argument("--state", default=str(DEFAULT_STATE))
    p.add_argument("--mission-id", required=True)
    p.add_argument("--wave-size", type=int)
    p.add_argument("--complete", nargs="*")
    args = p.parse_args()

    topology_path = Path(args.topology)
    state_path = Path(args.state)
    cfg = load_topology(topology_path)
    state = ensure_state(cfg, load_json(state_path, {}))
    if args.complete:
        mark_completed(state, args.complete)
    wave = next_wave(cfg, state, args.mission_id, args.wave_size)
    save_json(state_path, state)
    print(json.dumps({"wave": wave, "summary": summary(state)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
