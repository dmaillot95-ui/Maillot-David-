#!/usr/bin/env python3
"""Additional zero-euro adapters for CEREBRON Ω.

These adapters are inert unless credentials are present. They never create
accounts, never purchase credits, and never fall back to paid routes.
"""
from __future__ import annotations

import json
import os
import urllib.parse

from provider_adapters import ProviderResult, _classify_http, _post_json


def invoke_gemini(prompt: str, model: str | None = None, max_tokens: int = 700) -> ProviderResult:
    key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    if not key:
        return ProviderResult(False, "gemini_free", model=model, error_type="NOT_CONNECTED", error="GEMINI_API_KEY/GOOGLE_API_KEY missing")
    model_path = urllib.parse.quote(model, safe="-._")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_path}:generateContent?key={urllib.parse.quote(key, safe='')}"
    status, headers, body, transport_error = _post_json(
        url,
        {"Content-Type": "application/json"},
        {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": max_tokens},
        },
    )
    if status == 200:
        try:
            obj = json.loads(body)
            parts = obj["candidates"][0]["content"]["parts"]
            text = "\n".join(str(p.get("text", "")) for p in parts if p.get("text")).strip()
            if text:
                return ProviderResult(True, "gemini_free", model=model, text=text, status_code=status)
            raise ValueError("empty Gemini response")
        except Exception as exc:
            return ProviderResult(False, "gemini_free", model=model, status_code=status, error_type="DECODE", error=repr(exc))
    return ProviderResult(False, "gemini_free", model=model, status_code=status,
                          error_type=_classify_http(status, body, transport_error),
                          error=transport_error or body[-1200:], retry_after=headers.get("retry-after"))


def invoke_openrouter(prompt: str, model: str | None = None, max_tokens: int = 700) -> ProviderResult:
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    model = model or os.getenv("OPENROUTER_MODEL", "openrouter/free")
    if not key:
        return ProviderResult(False, "openrouter_free", model=model, error_type="NOT_CONNECTED", error="OPENROUTER_API_KEY missing")
    status, headers, body, transport_error = _post_json(
        "https://openrouter.ai/api/v1/chat/completions",
        {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "https://github.com/dmaillot95-ui/Maillot-David-"),
            "X-Title": "CEREBRON OMEGA",
        },
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
            actual_model = obj.get("model") or model
            if text:
                return ProviderResult(True, "openrouter_free", model=actual_model, text=text, status_code=status)
            raise ValueError("empty OpenRouter response")
        except Exception as exc:
            return ProviderResult(False, "openrouter_free", model=model, status_code=status, error_type="DECODE", error=repr(exc))
    return ProviderResult(False, "openrouter_free", model=model, status_code=status,
                          error_type=_classify_http(status, body, transport_error),
                          error=transport_error or body[-1200:], retry_after=headers.get("retry-after"),
                          remaining_requests=headers.get("x-ratelimit-remaining-requests"),
                          remaining_tokens=headers.get("x-ratelimit-remaining-tokens"))


def invoke_mistral(prompt: str, model: str | None = None, max_tokens: int = 700) -> ProviderResult:
    key = os.getenv("MISTRAL_API_KEY", "").strip()
    model = model or os.getenv("MISTRAL_MODEL", "mistral-small-latest")
    if not key:
        return ProviderResult(False, "mistral_free", model=model, error_type="NOT_CONNECTED", error="MISTRAL_API_KEY missing")
    status, headers, body, transport_error = _post_json(
        "https://api.mistral.ai/v1/chat/completions",
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
            if text:
                return ProviderResult(True, "mistral_free", model=model, text=text, status_code=status)
            raise ValueError("empty Mistral response")
        except Exception as exc:
            return ProviderResult(False, "mistral_free", model=model, status_code=status, error_type="DECODE", error=repr(exc))
    return ProviderResult(False, "mistral_free", model=model, status_code=status,
                          error_type=_classify_http(status, body, transport_error),
                          error=transport_error or body[-1200:], retry_after=headers.get("retry-after"))


def available_extra_zero_euro_routes() -> list[str]:
    routes: list[str] = []
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        routes.append("gemini_free")
    if os.getenv("OPENROUTER_API_KEY"):
        routes.append("openrouter_free")
    if os.getenv("MISTRAL_API_KEY"):
        routes.append("mistral_free")
    return routes
