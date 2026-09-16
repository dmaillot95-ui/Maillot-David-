#!/usr/bin/env python3
"""Zero-euro provider adapters for CEREBRON federation.

Adapters are inert unless credentials are present. They never perform paid fallback,
never create accounts, and surface quota/rate-limit signals to the Router Swarm.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class ProviderResult:
    ok: bool
    provider: str
    model: str | None = None
    text: str = ""
    status_code: int | None = None
    error_type: str | None = None
    error: str | None = None
    retry_after: str | None = None
    remaining_requests: str | None = None
    remaining_tokens: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _post_json(url: str, headers: dict[str, str], payload: dict[str, Any], timeout: int = 120):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, dict(resp.headers.items()), body, None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, dict(exc.headers.items()), body, None
    except Exception as exc:
        return None, {}, "", repr(exc)


def _classify_http(status: int | None, body: str, transport_error: str | None) -> str:
    if transport_error:
        return "TRANSPORT"
    low = (body or "").lower()
    if status == 429 or "rate limit" in low or "quota" in low or "resource exhausted" in low:
        return "QUOTA"
    if status in {401, 403}:
        return "AUTH_OR_PLAN"
    if status and status >= 500:
        return "UPSTREAM"
    return "BAD_RESPONSE"


def invoke_groq(prompt: str, model: str = "openai/gpt-oss-20b", max_tokens: int = 700) -> ProviderResult:
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        return ProviderResult(False, "groq_free", model=model, error_type="NOT_CONNECTED", error="GROQ_API_KEY missing")
    status, headers, body, transport_error = _post_json(
        "https://api.groq.com/openai/v1/chat/completions",
        {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": max_tokens,
        },
    )
    if status == 200:
        try:
            obj = json.loads(body)
            text = obj["choices"][0]["message"]["content"].strip()
            return ProviderResult(
                True,
                "groq_free",
                model=model,
                text=text,
                status_code=status,
                retry_after=headers.get("retry-after"),
                remaining_requests=headers.get("x-ratelimit-remaining-requests"),
                remaining_tokens=headers.get("x-ratelimit-remaining-tokens"),
            )
        except Exception as exc:
            return ProviderResult(False, "groq_free", model=model, status_code=status, error_type="DECODE", error=repr(exc))
    return ProviderResult(
        False,
        "groq_free",
        model=model,
        status_code=status,
        error_type=_classify_http(status, body, transport_error),
        error=transport_error or body[-1200:],
        retry_after=headers.get("retry-after"),
        remaining_requests=headers.get("x-ratelimit-remaining-requests"),
        remaining_tokens=headers.get("x-ratelimit-remaining-tokens"),
    )


def invoke_cloudflare(prompt: str, model: str = "@cf/zai-org/glm-4.7-flash", max_tokens: int = 700) -> ProviderResult:
    token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    account = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    if not token or not account:
        return ProviderResult(False, "cloudflare_workers_ai_free", model=model, error_type="NOT_CONNECTED", error="Cloudflare credentials missing")
    model_path = urllib.parse.quote(model, safe="@/-._")
    url = f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model_path}"
    status, headers, body, transport_error = _post_json(
        url,
        {"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        {"prompt": prompt, "max_tokens": max_tokens},
    )
    if status == 200:
        try:
            obj = json.loads(body)
            result = obj.get("result", {})
            text = result.get("response") or result.get("text") or ""
            if isinstance(text, str) and text.strip():
                return ProviderResult(True, "cloudflare_workers_ai_free", model=model, text=text.strip(), status_code=status)
            return ProviderResult(False, "cloudflare_workers_ai_free", model=model, status_code=status, error_type="DECODE", error=body[-1200:])
        except Exception as exc:
            return ProviderResult(False, "cloudflare_workers_ai_free", model=model, status_code=status, error_type="DECODE", error=repr(exc))
    return ProviderResult(
        False,
        "cloudflare_workers_ai_free",
        model=model,
        status_code=status,
        error_type=_classify_http(status, body, transport_error),
        error=transport_error or body[-1200:],
        retry_after=headers.get("retry-after"),
    )


def available_zero_euro_routes() -> list[str]:
    routes = ["huggingface_public_spaces", "github_actions_cpu"]
    if os.getenv("GROQ_API_KEY"):
        routes.append("groq_free")
    if os.getenv("CLOUDFLARE_API_TOKEN") and os.getenv("CLOUDFLARE_ACCOUNT_ID"):
        routes.append("cloudflare_workers_ai_free")
    return routes
