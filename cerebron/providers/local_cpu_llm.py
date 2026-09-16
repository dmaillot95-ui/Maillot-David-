#!/usr/bin/env python3
"""Zero-euro local CPU LLM provider for CEREBRON Ω.

Runs a small public instruction model locally on the current runner.
No inference API key is used and no paid fallback is permitted.
The model/tokenizer are cached once per Python process so multiple tasks can reuse them.
"""
from __future__ import annotations

import json
import os
import platform
import threading
import time
from typing import Any

MODEL = os.getenv("CEREBRON_LOCAL_CPU_MODEL", "HuggingFaceTB/SmolLM2-135M-Instruct")
DEFAULT_PROMPT = os.getenv(
    "CEREBRON_LOCAL_CPU_PROMPT",
    "Reply with exactly: CEREBRON_LOCAL_CPU_OK",
)
MAX_NEW_TOKENS = int(os.getenv("CEREBRON_LOCAL_CPU_MAX_NEW_TOKENS", "96"))
OUT = os.getenv("CEREBRON_LOCAL_CPU_OUT", "out/local-cpu-llm.json")

_MODEL = None
_TOKENIZER = None
_LOAD_LOCK = threading.Lock()
_GENERATE_LOCK = threading.Lock()


def _load_runtime():
    global _MODEL, _TOKENIZER
    if _MODEL is not None and _TOKENIZER is not None:
        return _TOKENIZER, _MODEL
    with _LOAD_LOCK:
        if _MODEL is None or _TOKENIZER is None:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            _TOKENIZER = AutoTokenizer.from_pretrained(MODEL)
            _MODEL = AutoModelForCausalLM.from_pretrained(MODEL)
    return _TOKENIZER, _MODEL


def invoke_local_cpu(prompt: str, max_new_tokens: int | None = None) -> dict[str, Any]:
    started = time.time()
    try:
        tokenizer, model = _load_runtime()
        messages = [{"role": "user", "content": prompt}]
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(text, return_tensors="pt")
        with _GENERATE_LOCK:
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens or MAX_NEW_TOKENS,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        generated = outputs[0][inputs["input_ids"].shape[-1]:]
        answer = tokenizer.decode(generated, skip_special_tokens=True).strip()
        return {
            "engine": "CEREBRON_LOCAL_CPU_LLM_V2",
            "provider": "github_actions_local_cpu_llm",
            "model": MODEL,
            "ok": bool(answer),
            "answer": answer,
            "elapsed_s": round(time.time() - started, 3),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "spend_limit_eur": 0,
            "paid_fallback": False,
            "api_key_used": False,
            "error_type": None if answer else "EMPTY_RESPONSE",
            "error": None if answer else "empty local model response",
        }
    except Exception as exc:
        return {
            "engine": "CEREBRON_LOCAL_CPU_LLM_V2",
            "provider": "github_actions_local_cpu_llm",
            "model": MODEL,
            "ok": False,
            "answer": "",
            "elapsed_s": round(time.time() - started, 3),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "spend_limit_eur": 0,
            "paid_fallback": False,
            "api_key_used": False,
            "error_type": type(exc).__name__,
            "error": repr(exc),
        }


def main() -> int:
    result = invoke_local_cpu(DEFAULT_PROMPT, max_new_tokens=MAX_NEW_TOKENS)
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
