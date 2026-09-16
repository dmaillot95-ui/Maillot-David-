#!/usr/bin/env python3
"""Zero-euro local CPU LLM probe for CEREBRON Ω.

Runs a small public instruction model locally on the GitHub-hosted runner.
No inference API key is used and no paid fallback is permitted.
"""
from __future__ import annotations

import json
import os
import platform
import time

MODEL = os.getenv("CEREBRON_LOCAL_CPU_MODEL", "HuggingFaceTB/SmolLM2-135M-Instruct")
PROMPT = os.getenv(
    "CEREBRON_LOCAL_CPU_PROMPT",
    "Reply with exactly: CEREBRON_LOCAL_CPU_OK",
)
MAX_NEW_TOKENS = int(os.getenv("CEREBRON_LOCAL_CPU_MAX_NEW_TOKENS", "24"))
OUT = os.getenv("CEREBRON_LOCAL_CPU_OUT", "out/local-cpu-llm.json")


def main() -> int:
    started = time.time()
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForCausalLM.from_pretrained(MODEL)
    messages = [{"role": "user", "content": PROMPT}]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt")
    outputs = model.generate(
        **inputs,
        max_new_tokens=MAX_NEW_TOKENS,
        do_sample=False,
        pad_token_id=tokenizer.eos_token_id,
    )
    generated = outputs[0][inputs["input_ids"].shape[-1]:]
    answer = tokenizer.decode(generated, skip_special_tokens=True).strip()
    elapsed = round(time.time() - started, 3)
    result = {
        "engine": "CEREBRON_LOCAL_CPU_LLM_V1",
        "provider": "github_actions_local_cpu_llm",
        "model": MODEL,
        "ok": bool(answer),
        "answer": answer,
        "elapsed_s": elapsed,
        "machine": platform.machine(),
        "python": platform.python_version(),
        "spend_limit_eur": 0,
        "paid_fallback": False,
        "api_key_used": False,
    }
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
