#!/usr/bin/env python3
"""CEREBRON zero-euro provider scorer.

Scores only routes already declared available by the runtime. The scorer itself
never enables a provider and never permits paid fallback.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Iterable

DEFAULT_STATE = {
    "schema": "cerebron-provider-runtime-v1",
    "providers": {
        "groq_free": {"successes": 0, "failures": 0, "quota_hits": 0, "ewma_latency_ms": None, "cooldown_until": 0},
        "cloudflare_workers_ai_free": {"successes": 0, "failures": 0, "quota_hits": 0, "ewma_latency_ms": None, "cooldown_until": 0},
        "huggingface_public_spaces": {"successes": 0, "failures": 0, "quota_hits": 0, "ewma_latency_ms": None, "cooldown_until": 0},
    },
}


def load_state(path: Path | None) -> dict:
    if path and path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return json.loads(json.dumps(DEFAULT_STATE))


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _stats(state: dict, route: str) -> dict:
    return state.setdefault("providers", {}).setdefault(route, {
        "successes": 0, "failures": 0, "quota_hits": 0,
        "ewma_latency_ms": None, "cooldown_until": 0,
    })


def score_route(route: str, state: dict, now: float | None = None) -> float:
    now = time.time() if now is None else now
    s = _stats(state, route)
    if float(s.get("cooldown_until") or 0) > now:
        return -1e9

    success = float(s.get("successes") or 0)
    failure = float(s.get("failures") or 0)
    quota = float(s.get("quota_hits") or 0)
    latency = s.get("ewma_latency_ms")

    # Bayesian-smoothed reliability. Starts neutral at 0.5.
    reliability = (success + 1.0) / (success + failure + 2.0)
    quota_penalty = min(0.45, 0.08 * quota)
    latency_penalty = 0.0 if latency in (None, 0) else min(0.25, math.log1p(float(latency)) / 45.0)

    # Small diversity prior prevents one route from monopolizing all tasks before evidence exists.
    prior = {
        "groq_free": 0.03,
        "cloudflare_workers_ai_free": 0.02,
        "huggingface_public_spaces": 0.0,
    }.get(route, 0.0)
    return reliability + prior - quota_penalty - latency_penalty


def ordered_routes(available: Iterable[str], state: dict, now: float | None = None) -> list[str]:
    routes = [r for r in available if r not in {"github_actions_cpu"}]
    return sorted(routes, key=lambda r: (-score_route(r, state, now), r))


def record_result(
    state: dict,
    route: str,
    *,
    ok: bool,
    error_type: str | None = None,
    latency_ms: float | None = None,
    retry_after_seconds: float | None = None,
    now: float | None = None,
) -> None:
    now = time.time() if now is None else now
    s = _stats(state, route)
    if ok:
        s["successes"] = int(s.get("successes") or 0) + 1
    else:
        s["failures"] = int(s.get("failures") or 0) + 1
    if error_type == "QUOTA":
        s["quota_hits"] = int(s.get("quota_hits") or 0) + 1
        # Respect provider retry hints; otherwise cool down conservatively for this local runtime.
        delay = float(retry_after_seconds) if retry_after_seconds is not None else 60.0
        s["cooldown_until"] = max(float(s.get("cooldown_until") or 0), now + max(1.0, delay))
    elif ok:
        s["cooldown_until"] = 0

    if latency_ms is not None and latency_ms >= 0:
        old = s.get("ewma_latency_ms")
        s["ewma_latency_ms"] = float(latency_ms) if old is None else (0.7 * float(old) + 0.3 * float(latency_ms))


def snapshot(state: dict, available: Iterable[str], now: float | None = None) -> dict:
    return {
        "ordered": ordered_routes(available, state, now),
        "scores": {r: score_route(r, state, now) for r in available if r != "github_actions_cpu"},
    }


if __name__ == "__main__":
    st = load_state(None)
    print(json.dumps(snapshot(st, ["groq_free", "cloudflare_workers_ai_free", "huggingface_public_spaces"]), indent=2))
