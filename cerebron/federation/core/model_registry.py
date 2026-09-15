#!/usr/bin/env python3
"""CÉRÉBRON Ω public Hugging Face Space registry and health probe.

No paid provider is used. This module only calls public Spaces through hf-gradio.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "state" / "model-registry.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def atomic_write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def load_registry():
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def run(cmd, timeout=180):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def build_payload(spec, prompt):
    payload = {}
    prompt_set = False
    for p in spec.get("parameters", []):
        name = p.get("name", "")
        lname = name.lower()
        required = bool(p.get("required", False))
        default = p.get("default", None)
        typ = (p.get("type") or {}).get("type")
        if lname in {"message", "prompt", "text", "query", "input", "instruction", "user_message"}:
            payload[name] = prompt
            prompt_set = True
        elif lname in {"chat_history", "history", "messages"}:
            payload[name] = []
        elif lname in {"max_new_tokens", "max_tokens", "maximum_new_tokens"}:
            payload[name] = 40
        elif lname == "temperature":
            payload[name] = 0.1
        elif lname == "top_p":
            payload[name] = 1.0
        elif lname == "top_k":
            payload[name] = 1
        elif lname in {"repetition_penalty", "repeat_penalty"}:
            payload[name] = 1.0
        elif lname in {"system", "system_prompt"}:
            payload[name] = "Réponds brièvement et exactement."
        elif required and default is None:
            if typ == "string" and not prompt_set:
                payload[name] = prompt
                prompt_set = True
            else:
                return None
    return payload if prompt_set else None


def probe_space(space: str):
    prompt = "Réponds exactement: CEREBRON_HF_OK 19*23=437"
    info = run(["hf-gradio", "info", space], 120)
    if info.returncode != 0:
        return {"ok": False, "stage": "info", "error": (info.stderr or info.stdout)[-1200:]}
    try:
        api = json.loads(info.stdout)
    except Exception as exc:
        return {"ok": False, "stage": "decode", "error": repr(exc)}

    preferred = ["/generate", "/chat", "/predict", "/respond", "/infer", "/run"]
    endpoints = list(api.items())
    endpoints.sort(key=lambda kv: (preferred.index(kv[0]) if kv[0] in preferred else 99, kv[0]))
    errors = []
    for endpoint, spec in endpoints:
        payload = build_payload(spec, prompt)
        if payload is None:
            continue
        pred = run(["hf-gradio", "predict", space, endpoint, json.dumps(payload, ensure_ascii=False)], 180)
        text = (pred.stdout or "").strip()
        if pred.returncode == 0 and text:
            semantic_ok = "437" in text
            return {
                "ok": bool(semantic_ok),
                "stage": "predict",
                "endpoint": endpoint,
                "semantic_ok": bool(semantic_ok),
                "response_excerpt": text[-500:],
                "error": None if semantic_ok else "Response returned but arithmetic sentinel missing"
            }
        errors.append(f"{endpoint}: {(pred.stderr or pred.stdout)[-500:]}")
    return {"ok": False, "stage": "predict", "error": " | ".join(errors[-3:]) or "No compatible endpoint"}


def apply_probe(model, result, policy):
    model["last_probe_at"] = now_iso()
    model["last_probe"] = result
    if result.get("ok"):
        model["last_known_result"] = "SUCCESS"
        model["consecutive_successes"] = int(model.get("consecutive_successes", 0)) + 1
        model["consecutive_failures"] = 0
        if model["consecutive_successes"] >= int(policy.get("rehabilitate_after_consecutive_successes", 2)):
            model["status"] = "HEALTHY"
        elif model.get("status") in {"QUARANTINED", "DEGRADED"}:
            model["status"] = "PROBATION"
        if result.get("endpoint"):
            model["last_endpoint"] = result["endpoint"]
    else:
        model["last_known_result"] = "FAILURE"
        model["consecutive_failures"] = int(model.get("consecutive_failures", 0)) + 1
        model["consecutive_successes"] = 0
        if model["consecutive_failures"] >= int(policy.get("quarantine_after_consecutive_failures", 2)):
            model["status"] = "QUARANTINED"
        elif model.get("status") == "HEALTHY":
            model["status"] = "DEGRADED"


def probe_all(include_quarantined=True):
    reg = load_registry()
    policy = reg.get("policy", {})
    summary = {"tested": 0, "healthy": 0, "failed": 0, "results": {}}
    for model_id, model in reg.get("models", {}).items():
        if not include_quarantined and model.get("status") == "QUARANTINED":
            continue
        result = probe_space(model["space"])
        apply_probe(model, result, policy)
        summary["tested"] += 1
        summary["healthy"] += int(bool(result.get("ok")))
        summary["failed"] += int(not bool(result.get("ok")))
        summary["results"][model_id] = {
            "ok": bool(result.get("ok")),
            "status": model.get("status"),
            "endpoint": result.get("endpoint"),
            "stage": result.get("stage")
        }
    reg["updated_at"] = now_iso()
    reg["last_probe_summary"] = summary
    atomic_write(REGISTRY_PATH, reg)
    return summary


def ranked(role=None):
    reg = load_registry()
    status_rank = {"HEALTHY": 0, "PROBATION": 1, "DEGRADED": 2, "QUARANTINED": 9}
    out = []
    for model_id, model in reg.get("models", {}).items():
        if role and role not in model.get("roles_allowed", []):
            continue
        out.append({"model_id": model_id, **model})
    out.sort(key=lambda m: (status_rank.get(m.get("status"), 8), -int(m.get("consecutive_successes", 0)), m["model_id"]))
    return out


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    pro = sub.add_parser("probe")
    pro.add_argument("--healthy-only", action="store_true")
    ran = sub.add_parser("rank")
    ran.add_argument("--role")
    args = p.parse_args()
    if args.cmd == "probe":
        print(json.dumps(probe_all(include_quarantined=not args.healthy_only), ensure_ascii=False, indent=2))
    elif args.cmd == "rank":
        print(json.dumps(ranked(args.role), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
