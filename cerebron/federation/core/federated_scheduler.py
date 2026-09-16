#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOPOLOGY = ROOT / "topology" / "federated-hubs-v1.json"


@dataclass(frozen=True)
class ShardAddress:
    tribe_id: str
    hub_id: str
    shard: int

    @property
    def key(self) -> str:
        return f"{self.tribe_id}/{self.hub_id}/S{self.shard:02d}"


def load_topology(path: Path = TOPOLOGY) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def addresses(cfg: dict) -> list[ShardAddress]:
    per_hub = int(cfg["logical_shards_per_hub"])
    out: list[ShardAddress] = []
    for tribe in cfg["tribes"]:
        tid = tribe["tribe_id"]
        for hub in tribe["hubs"]:
            for shard in range(per_hub):
                out.append(ShardAddress(tid, hub, shard))
    return out


def activation_wave(cfg: dict, cursor: int = 0) -> list[ShardAddress]:
    all_addresses = addresses(cfg)
    cap = min(int(cfg["physical_concurrency_cap"]), len(all_addresses))
    if not all_addresses or cap <= 0:
        return []
    start = cursor % len(all_addresses)
    return [all_addresses[(start + i) % len(all_addresses)] for i in range(cap)]


def validate(cfg: dict) -> dict:
    all_addresses = addresses(cfg)
    keys = [a.key for a in all_addresses]
    wave = activation_wave(cfg)
    assert len(keys) == len(set(keys)), "duplicate shard addresses"
    assert len(wave) <= int(cfg["physical_concurrency_cap"])
    return {
        "tribes": len(cfg["tribes"]),
        "hubs": sum(len(t["hubs"]) for t in cfg["tribes"]),
        "logical_shards": len(all_addresses),
        "unique_addresses": len(set(keys)),
        "physical_concurrency_cap": int(cfg["physical_concurrency_cap"]),
        "active_in_wave": len(wave),
        "first_wave": [a.key for a in wave],
    }


if __name__ == "__main__":
    print(json.dumps(validate(load_topology()), ensure_ascii=False, indent=2))
