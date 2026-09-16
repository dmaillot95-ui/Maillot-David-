#!/usr/bin/env python3
"""CEREBRON Ω federated compute adapters.

Providers implemented as safe opt-in HTTP adapters:
- github_local: existing local CPU inference path inside GitHub Actions
- vercel_http: user-controlled Vercel endpoint
- scaleway_http: user-controlled Scaleway endpoint
- alibaba_http: user-controlled Alibaba endpoint

No external provider is called unless BOTH CEREBRON_FEDERATION_ENABLE=1 and the
provider-specific endpoint variable are present. Paid fallback is forbidden.
"""
from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from typing import Dict

from cerebron.providers.federated_worker_contract import WorkerTask, WorkerResult, Timer, validate_zero_euro

PROVIDERS = {
    "vercel": "CEREBRON_VERCEL_WORKER_URL",
    "scaleway": "CEREBRON_SCALEWAY_WORKER_URL",
    "alibaba": "CEREBRON_ALIBABA_WORKER_URL",
}
TOKEN_ENV = {
    "vercel": "CEREBRON_VERCEL_WORKER_TOKEN",
    "scaleway": "CEREBRON_SCALEWAY_WORKER_TOKEN",
    "alibaba": "CEREBRON_ALIBABA_WORKER_TOKEN",
}


def _enabled() -> bool:
    return os.getenv("CEREBRON_FEDERATION_ENABLE", "0") == "1"


def provider_status() -> Dict[str, dict]:
    out = {}
    for provider, env_name in PROVIDERS.items():
        endpoint = os.getenv(env_name, "").strip()
        out[provider] = {
            "configured": bool(endpoint),
            "enabled": bool(endpoint) and _enabled(),
            "endpoint_env": env_name,
            "token_present": bool(os.getenv(TOKEN_ENV[provider], "")),
            "paid_fallback": False,
        }
    return out


def invoke_http(provider: str, task: WorkerTask, timeout_s: int = 120) -> WorkerResult:
    validate_zero_euro(task)
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider: {provider}")
    if not _enabled():
        raise RuntimeError("Federated external execution is disabled. Set CEREBRON_FEDERATION_ENABLE=1 explicitly.")

    endpoint = os.getenv(PROVIDERS[provider], "").strip()
    if not endpoint:
        raise RuntimeError(f"{provider} endpoint is not configured ({PROVIDERS[provider]} missing)")

    headers = {"Content-Type": "application/json", "User-Agent": "CEREBRON-Omega/1"}
    token = os.getenv(TOKEN_ENV[provider], "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = task.to_json().encode("utf-8")
    req = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
    worker_id = f"{provider}-{socket.gethostname()}"

    with Timer() as timer:
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as response:
                raw = response.read().decode("utf-8", errors="replace")
                data = json.loads(raw) if raw.lstrip().startswith("{") else {"result": raw}
            return WorkerResult(
                task_id=task.task_id,
                provider=provider,
                worker_id=str(data.get("worker_id") or worker_id),
                ok=bool(data.get("ok", True)),
                result=str(data.get("result", "")),
                evidence=data.get("evidence") if isinstance(data.get("evidence"), dict) else None,
                runtime_s=float(data.get("runtime_s") or timer.elapsed_s),
                cost_eur=float(data.get("cost_eur") or 0.0),
                error=data.get("error"),
                model=data.get("model"),
            )
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            return WorkerResult(
                task_id=task.task_id,
                provider=provider,
                worker_id=worker_id,
                ok=False,
                result="",
                evidence=None,
                runtime_s=timer.elapsed_s,
                cost_eur=0.0,
                error=f"{type(exc).__name__}: {exc}",
            )


def invoke_github_local(task: WorkerTask) -> WorkerResult:
    validate_zero_euro(task)
    from cerebron.providers.local_cpu_llm import invoke_local_cpu
    with Timer() as timer:
        r = invoke_local_cpu(task.prompt, max_new_tokens=192)
    return WorkerResult(
        task_id=task.task_id,
        provider="github_local",
        worker_id=f"github-local-{socket.gethostname()}",
        ok=bool(r.get("ok")),
        result=str(r.get("answer", "")),
        evidence={"runtime": "local_cpu", "api_key_used": False, "paid_fallback": False},
        runtime_s=float(r.get("elapsed_s") or timer.elapsed_s),
        cost_eur=0.0,
        error=r.get("error"),
        model=r.get("model"),
    )


def invoke(provider: str, task: WorkerTask) -> WorkerResult:
    if provider == "github_local":
        return invoke_github_local(task)
    return invoke_http(provider, task)


if __name__ == "__main__":
    print(json.dumps({"federation_enabled": _enabled(), "providers": provider_status()}, indent=2))
