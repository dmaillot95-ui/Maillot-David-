#!/usr/bin/env python3
"""CÉRÉBRON Ω adaptive shard worker entrypoint.

Loads the persisted provider runtime memory read-only for each shard process and
uses provider_router scoring to order only zero-euro routes that are actually
available at runtime. Shared provider state is never written by shards; the wave
reducer remains the single writer after all lanes finish.
"""
from __future__ import annotations

import sys
from pathlib import Path

CORE = Path(__file__).resolve().parent
FEDERATION = CORE.parent
ROUTING = FEDERATION / "routing"
STATE = FEDERATION / "state" / "provider-runtime.json"

for p in (str(CORE), str(ROUTING)):
    if p not in sys.path:
        sys.path.insert(0, p)

import shard_worker  # noqa: E402
from provider_router import load_state, ordered_routes, snapshot  # noqa: E402

ROUTER_STATE = load_state(STATE)


def adaptive_provider_order(task) -> list[str]:
    """Return learned order, restricted to routes connected in this runtime."""
    available = shard_worker.available_zero_euro_routes()
    return ordered_routes(available, ROUTER_STATE)


def router_snapshot() -> dict:
    available = shard_worker.available_zero_euro_routes()
    return snapshot(ROUTER_STATE, available)


# Runtime injection: execute_one() resolves provider_order from shard_worker globals,
# so replacing this symbol activates learned routing without duplicating worker logic.
shard_worker.provider_order = adaptive_provider_order


if __name__ == "__main__":
    print("CEREBRON_ADAPTIVE_ROUTER", router_snapshot(), file=sys.stderr)
    shard_worker.main()
