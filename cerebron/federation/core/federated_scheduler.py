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


def _compact(cfg: dict) -> bool:
    return all(k in cfg for k in ("tribes", "hubs_per_tribe", "shards_per_hub")) and isinstance(cfg.get("tribes"), int)


def addresses(cfg: dict) -> list[ShardAddress]:
    out: list[ShardAddress] = []
    if _compact(cfg):
        tribes = int(cfg["tribes"])
        hubs_per_tribe = int(cfg["hubs_per_tribe"])
        per_hub = int(cfg["shards_per_hub"])
        for t in range(tribes):
            tid = f"T{t+1:02d}"
            for h in range(hubs_per_tribe):
                hid = f"H{h+1:02d}"
                for shard in range(per_hub):
                    out.append(ShardAddress(tid, hid, shard))
        return out

    per_hub = int(cfg["logical_shards_per_hub"])
    for tribe in cfg["tribes"]:
        tid = tribe["tribe_id"]
        for hub in tribe["hubs"]:
            hid = hub if isinstance(hub, str) else hub.get("hub_id")
            for shard in range(per_hub):
                out.append(ShardAddress(tid, hid, shard))
    return out


def physical_cap(cfg: dict) -> int:
    return int(cfg.get("physical_concurrency_cap", cfg.get("physical_parallel_cap", 0)))


def activation_wave(cfg: dict, cursor: int = 0) -> list[ShardAddress]:
    all_addresses = addresses(cfg)
    cap = min(physical_cap(cfg), len(all_addresses))
    if not all_addresses or cap <= 0:
        return []
    start = cursor % len(all_addresses)
    return [all_addresses[(start + i) % len(all_addresses)] for i in range(cap)]


def validate(cfg: dict) -> dict:
    all_addresses = addresses(cfg)
    keys = [a.key for a in all_addresses]
    wave = activation_wave(cfg)
    assert len(keys) == len(set(keys)), "duplicate shard addresses"
    assert len(wave) <= physical_cap(cfg), "wave exceeds physical cap"
    declared = cfg.get("logical_shards")
    if declared is not None:
        assert len(all_addresses) == int(declared), f"declared logical_shards={declared}, generated={len(all_addresses)}"
    if _compact(cfg):
        tribe_count = int(cfg["tribes"])
        hub_count = tribe_count * int(cfg["hubs_per_tribe"])
    else:
        tribe_count = len(cfg["tribes"])
        hub_count = sum(len(t["hubs"]) for t in cfg["tribes"])
    return {
        "tribes": tribe_count,
        "hubs": hub_count,
        "logical_shards": len(all_addresses),
        "unique_addresses": len(set(keys)),
        "physical_concurrency_cap": physical_cap(cfg),
        "active_in_wave": len(wave),
        "first_wave": [a.key for a in wave],
    }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--topology", default=str(TOPOLOGY))
    args = p.parse_args()
    print(json.dumps(validate(load_topology(Path(args.topology))), ensure_ascii=False, indent=2))
