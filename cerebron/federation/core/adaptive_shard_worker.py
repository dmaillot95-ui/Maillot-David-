#!/usr/bin/env python3
"""CÉRÉBRON Ω adaptive shard worker entrypoint.

Loads persisted provider memory read-only and extends the base worker with optional
zero-euro external adapters plus a local CPU LLM route. Hugging Face public-space
calls are globally paced per runner so parallel highway lanes do not stampede the
same free route. No paid fallback is possible.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import threading
import time
from pathlib import Path

CORE = Path(__file__).resolve().parent
FEDERATION = CORE.parent
ROUTING = FEDERATION / "routing"
STATE = FEDERATION / "state" / "provider-runtime.json"
PROVIDERS = FEDERATION.parent / "providers"

for p in (str(CORE), str(ROUTING), str(PROVIDERS)):
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
_BASE_INVOKE_HF = shard_worker.invoke_hf

_HF_PARALLEL = max(1, min(int(os.getenv("CEREBRON_HF_PARALLEL", "1")), 2))
_HF_MIN_INTERVAL = max(0.0, float(os.getenv("CEREBRON_HF_MIN_INTERVAL_SECONDS", "1.25")))
_HF_GATE = threading.Semaphore(_HF_PARALLEL)
_HF_CLOCK_LOCK = threading.Lock()
_HF_LAST_START = 0.0


def _local_cpu_ready() -> bool:
    if os.getenv("CEREBRON_LOCAL_CPU_ENABLE", "0").strip().lower() not in {"1", "true", "yes", "on"}:
        return False
    return importlib.util.find_spec("transformers") is not None and importlib.util.find_spec("torch") is not None


def expanded_available_zero_euro_routes() -> list[str]:
    routes = list(_BASE_AVAILABLE())
    for route in available_extra_zero_euro_routes():
        if route not in routes:
            routes.append(route)
    if _local_cpu_ready() and "github_actions_local_cpu_llm" not in routes:
        routes.append("github_actions_local_cpu_llm")
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
    if route == "github_actions_local_cpu_llm":
        from local_cpu_llm import invoke_local_cpu
        r = invoke_local_cpu(prompt, max_new_tokens=int(os.getenv("CEREBRON_LOCAL_CPU_MAX_NEW_TOKENS", "96")))
        return bool(r.get("ok")), str(r.get("answer") or ""), {
            "provider": "github_actions_local_cpu_llm",
            "model_id": r.get("model"),
            "model_family": "smollm2-local-cpu",
            "endpoint": "local-process",
            "error_type": r.get("error_type"),
            "error": r.get("error"),
            "elapsed_s": r.get("elapsed_s"),
            "api_key_used": False,
            "spend_limit_eur": 0,
        }
    return _BASE_PROVIDER_ATTEMPT(route, prompt)


def paced_invoke_hf(model, prompt):
    global _HF_LAST_START
    with _HF_GATE:
        with _HF_CLOCK_LOCK:
            now = time.monotonic()
            delay = _HF_MIN_INTERVAL - (now - _HF_LAST_START)
            if delay > 0:
                time.sleep(delay)
            _HF_LAST_START = time.monotonic()
        return _BASE_INVOKE_HF(model, prompt)


def adaptive_provider_order(task) -> list[str]:
    available = expanded_available_zero_euro_routes()
    ordered = ordered_routes(available, ROUTER_STATE)
    # Keep local CPU as a true zero-euro fallback after connected external free routes.
    if "github_actions_local_cpu_llm" in ordered:
        ordered = [x for x in ordered if x != "github_actions_local_cpu_llm"] + ["github_actions_local_cpu_llm"]
    return ordered


def router_snapshot() -> dict:
    available = expanded_available_zero_euro_routes()
    snap = snapshot(ROUTER_STATE, available)
    snap["hf_parallel_per_runner"] = _HF_PARALLEL
    snap["hf_min_interval_seconds"] = _HF_MIN_INTERVAL
    snap["local_cpu_ready"] = _local_cpu_ready()
    snap["local_cpu_model"] = os.getenv("CEREBRON_LOCAL_CPU_MODEL", "HuggingFaceTB/SmolLM2-135M-Instruct")
    return snap


shard_worker.available_zero_euro_routes = expanded_available_zero_euro_routes
shard_worker._provider_attempt = expanded_provider_attempt
shard_worker.invoke_hf = paced_invoke_hf
shard_worker.provider_order = adaptive_provider_order


if __name__ == "__main__":
    print("CEREBRON_ADAPTIVE_ROUTER", router_snapshot(), file=sys.stderr)
    shard_worker.main()
