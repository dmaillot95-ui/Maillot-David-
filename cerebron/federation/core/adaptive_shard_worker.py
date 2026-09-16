#!/usr/bin/env python3
"""CÉRÉBRON Ω adaptive shard worker entrypoint.

Loads persisted provider memory read-only and extends the base worker with optional
zero-euro Gemini, OpenRouter and Mistral adapters. No paid fallback is possible.
"""
from __future__ import annotations

import os
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
from provider_adapters_extra import (  # noqa: E402
    available_extra_zero_euro_routes,
    invoke_gemini,
    invoke_mistral,
    invoke_openrouter,
)

ROUTER_STATE = load_state(STATE)
_BASE_AVAILABLE = shard_worker.available_zero_euro_routes
_BASE_PROVIDER_ATTEMPT = shard_worker._provider_attempt


def expanded_available_zero_euro_routes() -> list[str]:
    routes = list(_BASE_AVAILABLE())
    for route in available_extra_zero_euro_routes():
        if route not in routes:
            routes.append(route)
    return routes


def expanded_provider_attempt(route: str, prompt: str):
    if route == "gemini_free":
        r = invoke_gemini(prompt, model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
        return r.ok, r.text, {
            "provider": r.provider, "model_id": r.model, "model_family": "gemini",
            "endpoint": "generateContent", "error_type": r.error_type,
            "error": r.error, "retry_after": r.retry_after,
        }
    if route == "openrouter_free":
        r = invoke_openrouter(prompt, model=os.getenv("OPENROUTER_MODEL", "openrouter/free"))
        return r.ok, r.text, {
            "provider": r.provider, "model_id": r.model, "model_family": "openrouter-free",
            "endpoint": "chat/completions", "error_type": r.error_type,
            "error": r.error, "retry_after": r.retry_after,
            "remaining_requests": r.remaining_requests, "remaining_tokens": r.remaining_tokens,
        }
    if route == "mistral_free":
        r = invoke_mistral(prompt, model=os.getenv("MISTRAL_MODEL", "mistral-small-latest"))
        return r.ok, r.text, {
            "provider": r.provider, "model_id": r.model, "model_family": "mistral-api",
            "endpoint": "chat/completions", "error_type": r.error_type,
            "error": r.error, "retry_after": r.retry_after,
        }
    return _BASE_PROVIDER_ATTEMPT(route, prompt)


def adaptive_provider_order(task) -> list[str]:
    """Return learned order, restricted to routes connected in this runtime."""
    available = expanded_available_zero_euro_routes()
    return ordered_routes(available, ROUTER_STATE)


def router_snapshot() -> dict:
    available = expanded_available_zero_euro_routes()
    return snapshot(ROUTER_STATE, available)


# Runtime injection into the existing worker avoids duplicating queue/execution logic.
shard_worker.available_zero_euro_routes = expanded_available_zero_euro_routes
shard_worker._provider_attempt = expanded_provider_attempt
shard_worker.provider_order = adaptive_provider_order


if __name__ == "__main__":
    print("CEREBRON_ADAPTIVE_ROUTER", router_snapshot(), file=sys.stderr)
    shard_worker.main()
