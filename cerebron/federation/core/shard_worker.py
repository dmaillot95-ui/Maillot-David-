#!/usr/bin/env python3
"""CÉRÉBRON Ω multi-provider shard worker.

Reads the persistent queue and routes tasks only through zero-euro paths that are
actually connected at runtime. GitHub Actions CPU remains orchestration/deterministic
compute; LLM inference can use connected Groq Free / Cloudflare Workers AI Free
routes, then zero-euro public Hugging Face Spaces. No paid fallback exists.

Shard jobs do NOT mutate shared queue state; the reducer merges immutable artifacts.
Quota circuit breakers stop hammering a provider after a shard observes saturation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

from provider_adapters import (
    available_zero_euro_routes,
    invoke_cloudflare,
    invoke_groq,
)

ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = ROOT / "state" / "mission-queue.json"
REGISTRY_PATH = ROOT / "state" / "model-registry.json"
FEDERATION_PATH = ROOT / "federation-v1.json"

ROLE_DIRECTIVES = {
    "SCOUT": "Explore les pistes pertinentes. Distingue faits, hypothèses et inconnues. Ne conclus pas sans preuve.",
    "DECOMPOSER": "Décompose le problème en sous-problèmes falsifiables et dépendances exactes.",
    "PROOF_A": "Cherche une preuve formelle par une voie A. Chaque étape doit être justifiée. Signale explicitement les gaps.",
    "PROOF_B": "Cherche une preuve indépendante par une voie B différente de la voie A. Évite de reprendre ses hypothèses cachées.",
    "COMPUTE_CHECKER": "Vérifie uniquement les calculs reproductibles. Si aucun calcul déterministe n'est possible, écris HOLD_DETERMINISTIC_CHECK.",
    "ALTERNATIVE_ROUTE": "Cherche une méthode substantiellement différente et indique ce qui la rend indépendante.",
    "FALSIFIER": "Cherche contre-exemples, cas limites et conditions qui invalideraient les affirmations proposées.",
    "RED_TEAM": "Attaque les prémisses, les inférences, les preuves et les conclusions. Cherche l'erreur la plus dommageable.",
    "COUNTER_AUDITOR": "Audite l'audit et la Red Team. Cherche erreurs corrélées et hypothèses partagées.",
    "REPLICATOR": "Reproduis indépendamment le résultat à partir de l'énoncé, sans supposer que la conclusion est vraie.",
    "SYNTHESIZER": "Compresse uniquement les éléments soutenus par les preuves. Sépare consensus, contradiction et inconnu.",
    "JUDGE": "Juge les claims selon CLAIM<=EVIDENCE. Accepte, rejette ou place HOLD avec raison précise.",
}

PREFERRED_ENDPOINTS = ["/generate", "/chat", "/predict", "/respond", "/infer", "/run"]
QUOTA_MARKERS = (
    "quota", "zerogpu", "rate limit", "rate_limit", "too many requests",
    "429", "capacity", "temporarily unavailable", "resource exhausted"
)
MAX_MODEL_ATTEMPTS_PER_TASK = 3


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def size_num(value: str) -> float:
    try:
        return float(str(value).upper().replace("B", ""))
    except Exception:
        return 0.0


def is_quota_error(text: str | None) -> bool:
    s = (text or "").lower()
    return any(marker in s for marker in QUOTA_MARKERS)


def active_models(role: str):
    reg = load(REGISTRY_PATH)
    models = []
    for model_id, m in reg.get("models", {}).items():
        if m.get("status") not in {"HEALTHY", "PROBATION"}:
            continue
        if role not in m.get("roles_allowed", []):
            continue
        if m.get("cost_class") != "ZERO_EURO_PUBLIC_SPACE":
            continue
        models.append({"model_id": model_id, **m})
    return models


def model_candidates(task):
    """Deterministic HF candidates, one independent family before reuse."""
    role = task["role"]
    models = active_models(role)
    if not models:
        return []
    groups = {}
    for m in models:
        groups.setdefault(m["family"], []).append(m)
    families = sorted(groups)
    lane = {
        "PROOF_A": 0, "PROOF_B": 1, "RED_TEAM": 1,
        "COUNTER_AUDITOR": 0, "REPLICATOR": 1, "FALSIFIER": 1,
    }.get(role)
    if lane is None:
        lane = int(hashlib.sha256(task["task_id"].encode()).hexdigest(), 16)
    start = lane % len(families)
    family_order = families[start:] + families[:start]
    for fam in family_order:
        groups[fam].sort(key=lambda m: (-size_num(m.get("size_class", "0")), m["model_id"]))
    ordered = [groups[fam][0] for fam in family_order]
    for fam in family_order:
        ordered.extend(groups[fam][1:])
    return ordered[:MAX_MODEL_ATTEMPTS_PER_TASK]


def role_prompt(task, mission, civilization_mission: str):
    directive = ROLE_DIRECTIVES.get(task["role"], "Travaille rigoureusement et sépare preuve et hypothèse.")
    return f"""CÉRÉBRON Ω — AGENT EXTERNE INDÉPENDANT
MISSION GLOBALE: {mission['title']}
OBJECTIF: {mission['objective']}
CIVILISATION: {task.get('civilization')} — {civilization_mission}
ÉQUIPE: {task.get('team')}
RÔLE: {task['role']}
DIRECTIVE: {directive}

RÈGLES ABSOLUES:
- REALITY > COHERENCE
- EVIDENCE > CONFIDENCE
- CLAIM <= EVIDENCE
- ne jamais inventer un calcul, un test, une source ou un résultat
- marquer PROUVÉ / HYPOTHÈSE / INCONNU / CONTRADICTION
- si une étape manque, l'indiquer au lieu de combler le gap

Réponds avec un résultat technique compact, vérifiable et utile au niveau supérieur de la pyramide.
"""


def run(cmd, timeout=240):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def build_payload(spec, prompt):
    payload, prompt_set = {}, False
    for p in spec.get("parameters", []):
        name = p.get("name", "")
        lname = name.lower()
        required = bool(p.get("required", False))
        default = p.get("default", None)
        typ = (p.get("type") or {}).get("type")
        if lname in {"message", "prompt", "text", "query", "input", "instruction", "user_message"}:
            payload[name] = prompt; prompt_set = True
        elif lname in {"chat_history", "history", "messages"}:
            payload[name] = []
        elif lname in {"max_new_tokens", "max_tokens", "maximum_new_tokens"}:
            payload[name] = 700
        elif lname == "temperature":
            payload[name] = 0.1
        elif lname == "top_p":
            payload[name] = 0.9
        elif lname == "top_k":
            payload[name] = 40
        elif lname in {"repetition_penalty", "repeat_penalty"}:
            payload[name] = 1.0
        elif lname in {"system", "system_prompt"}:
            payload[name] = "Tu es un agent CÉRÉBRON rigoureux. CLAIM<=EVIDENCE."
        elif required and default is None:
            if typ == "string" and not prompt_set:
                payload[name] = prompt; prompt_set = True
            else:
                return None
    return payload if prompt_set else None


def extract_text(raw: str) -> str:
    raw = raw.strip()
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            for key in ("Response", "response", "text", "output", "message"):
                if isinstance(obj.get(key), str):
                    return obj[key].strip()
        if isinstance(obj, list):
            return "\n".join(str(x) for x in obj)
    except Exception:
        pass
    return raw


def invoke_hf(model, prompt):
    space = model["space"]
    info = run(["hf-gradio", "info", space], 120)
    if info.returncode != 0:
        err = (info.stderr or info.stdout)[-1500:]
        return False, "", {"stage": "info", "error": err, "error_type": "QUOTA" if is_quota_error(err) else "UPSTREAM"}
    try:
        api = json.loads(info.stdout)
    except Exception as exc:
        return False, "", {"stage": "decode", "error": repr(exc), "error_type": "DECODE"}
    endpoints = list(api.items())
    preferred = [model.get("last_endpoint")] + PREFERRED_ENDPOINTS
    preferred = [x for x in preferred if x]
    endpoints.sort(key=lambda kv: (preferred.index(kv[0]) if kv[0] in preferred else 99, kv[0]))
    errors = []
    for endpoint, spec in endpoints:
        payload = build_payload(spec, prompt)
        if payload is None:
            continue
        pred = run(["hf-gradio", "predict", space, endpoint, json.dumps(payload, ensure_ascii=False)], 240)
        if pred.returncode == 0 and (pred.stdout or "").strip():
            return True, extract_text(pred.stdout), {"stage": "predict", "endpoint": endpoint, "error_type": None}
        err = (pred.stderr or pred.stdout)[-1200:]
        if is_quota_error(err):
            return False, "", {"stage": "predict", "endpoint": endpoint, "error": err, "error_type": "QUOTA"}
        errors.append(f"{endpoint}: {err[-700:]}")
    return False, "", {"stage": "predict", "error": " | ".join(errors[-3:]) or "No compatible endpoint", "error_type": "UPSTREAM"}


def queue_tasks(shard: int, limit: int, mission_id: str | None):
    q = load(QUEUE_PATH)
    tasks = []
    for t in q.get("tasks", {}).values():
        if int(t.get("shard", -1)) != shard:
            continue
        if t.get("status") not in {"PENDING", "FAILED_RETRYABLE"}:
            continue
        if mission_id and t.get("mission_id") != mission_id:
            continue
        tasks.append(t)
    tasks.sort(key=lambda t: (-int(t.get("priority", 0)), t.get("created_at", ""), t["task_id"]))
    return tasks[:limit], q.get("missions", {})


def civilization_map():
    cfg = load(FEDERATION_PATH)
    return {c["id"]: c["mission"] for c in cfg.get("civilizations", [])}


def provider_order(task) -> list[str]:
    """Spread connected providers deterministically across tasks to reduce bursts."""
    available = set(available_zero_euro_routes())
    external = [r for r in ("groq_free", "cloudflare_workers_ai_free") if r in available]
    if len(external) > 1:
        pivot = int(hashlib.sha256(task["task_id"].encode()).hexdigest(), 16) % len(external)
        external = external[pivot:] + external[:pivot]
    if "huggingface_public_spaces" in available:
        external.append("huggingface_public_spaces")
    return external


def _provider_attempt(route: str, prompt: str):
    if route == "groq_free":
        r = invoke_groq(prompt, model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"))
        return r.ok, r.text, {
            "provider": r.provider, "model_id": r.model, "model_family": "groq",
            "endpoint": "chat/completions", "error_type": r.error_type,
            "error": r.error, "retry_after": r.retry_after,
            "remaining_requests": r.remaining_requests, "remaining_tokens": r.remaining_tokens,
        }
    if route == "cloudflare_workers_ai_free":
        r = invoke_cloudflare(prompt, model=os.getenv("CLOUDFLARE_AI_MODEL", "@cf/zai-org/glm-4.7-flash"))
        return r.ok, r.text, {
            "provider": r.provider, "model_id": r.model, "model_family": "cloudflare-ai",
            "endpoint": "workers-ai", "error_type": r.error_type,
            "error": r.error, "retry_after": r.retry_after,
        }
    raise ValueError(route)


def execute_one(task, mission, civ_map, blocked_routes: set[str]):
    base = {
        "task_id": task["task_id"], "mission_id": task.get("mission_id"),
        "cycle": task.get("cycle"), "civilization": task.get("civilization"),
        "team": task.get("team"), "role": task["role"], "shard": task.get("shard")
    }
    prompt = role_prompt(task, mission, civ_map.get(task.get("civilization"), ""))
    attempts = []

    # First use connected non-HF free providers. A quota signal opens a per-shard
    # circuit breaker so subsequent tasks in the same wave do not hammer it.
    for route in provider_order(task):
        if route in blocked_routes or route == "huggingface_public_spaces":
            continue
        ok, response, meta = _provider_attempt(route, prompt)
        attempts.append({
            "provider": route, "model_id": meta.get("model_id"),
            "model_family": meta.get("model_family"), "ok": bool(ok),
            "endpoint": meta.get("endpoint"), "error_type": meta.get("error_type"),
            "error": meta.get("error"), "retry_after": meta.get("retry_after"),
        })
        if ok:
            return {
                **base, "execution_status": "COMPLETED", "ok": True,
                "provider": route, "model_id": meta.get("model_id"),
                "model_family": meta.get("model_family"), "space": None,
                "endpoint": meta.get("endpoint"), "response": response,
                "response_sha256": hashlib.sha256(response.encode()).hexdigest() if response else None,
                "error": None, "attempted_models": attempts,
                "evidence_status": "UNREVIEWED_EXTERNAL_AGENT_OUTPUT",
            }
        if meta.get("error_type") == "QUOTA":
            blocked_routes.add(route)
        time.sleep(0.25)

    # HF fallback remains active only while this shard has not observed an all-quota
    # failure. This preserves useful free capacity but eliminates repeated dead calls.
    hf_route = "huggingface_public_spaces"
    candidates = [] if hf_route in blocked_routes else model_candidates(task)
    final_meta = {}
    for model in candidates:
        ok, response, meta = invoke_hf(model, prompt)
        attempts.append({
            "provider": hf_route, "model_id": model["model_id"],
            "model_family": model["family"], "space": model["space"],
            "ok": bool(ok), "endpoint": meta.get("endpoint"),
            "error_type": meta.get("error_type"), "error": meta.get("error"),
        })
        final_meta = {"model": model, "meta": meta}
        if ok:
            return {
                **base, "execution_status": "COMPLETED", "ok": True,
                "provider": hf_route, "model_id": model["model_id"],
                "model_family": model["family"], "space": model["space"],
                "endpoint": meta.get("endpoint"), "response": response,
                "response_sha256": hashlib.sha256(response.encode()).hexdigest() if response else None,
                "error": None, "attempted_models": attempts,
                "evidence_status": "UNREVIEWED_EXTERNAL_AGENT_OUTPUT",
            }
        time.sleep(0.5 if meta.get("error_type") != "QUOTA" else 1.0)

    hf_attempts = [a for a in attempts if a.get("provider") == hf_route]
    if hf_attempts and all(a.get("error_type") == "QUOTA" for a in hf_attempts):
        blocked_routes.add(hf_route)

    quota_attempts = [a for a in attempts if a.get("error_type") == "QUOTA"]
    all_attempted_quota = bool(attempts) and len(quota_attempts) == len(attempts)
    if not attempts:
        status = "HOLD_NO_CONNECTED_PROVIDER"
        error = "No connected zero-euro inference provider available in this shard"
    elif all_attempted_quota:
        status = "HOLD_QUOTA_BACKOFF"
        error = "All attempted zero-euro inference routes are quota-limited"
    else:
        status = "FAILED_RETRYABLE"
        error = (final_meta.get("meta") or {}).get("error") or attempts[-1].get("error")

    last_model = (final_meta.get("model") or {})
    return {
        **base, "execution_status": status, "ok": False,
        "provider": attempts[-1].get("provider") if attempts else None,
        "model_id": last_model.get("model_id") or (attempts[-1].get("model_id") if attempts else None),
        "model_family": last_model.get("family") or (attempts[-1].get("model_family") if attempts else None),
        "space": last_model.get("space"), "endpoint": (final_meta.get("meta") or {}).get("endpoint"),
        "response": "", "response_sha256": None, "error": error,
        "attempted_models": attempts, "evidence_status": "NO_EVIDENCE",
    }


def smoke_task(shard: int, role: str):
    return {
        "task_id": f"SMOKE-S{shard:02d}-{role}", "mission_id": "SMOKE", "cycle": 0,
        "civilization": "C07" if role == "RED_TEAM" else "C03", "team": 1,
        "role": role, "shard": shard, "priority": 999, "status": "PENDING"
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--shard", type=int, required=True)
    p.add_argument("--limit", type=int, default=1)
    p.add_argument("--mission-id")
    p.add_argument("--output", required=True)
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--smoke-role", default="PROOF_A")
    p.add_argument("--smoke-objective", default="Vérifie que le canal d'agent externe fonctionne sans inventer de preuve.")
    args = p.parse_args()

    out = Path(args.output); out.parent.mkdir(parents=True, exist_ok=True)
    civ_map = civilization_map()
    if args.smoke:
        tasks = [smoke_task(args.shard, args.smoke_role)]
        missions = {"SMOKE": {"title": "CEREBRON SHARD SMOKE TEST", "objective": args.smoke_objective}}
    else:
        tasks, missions = queue_tasks(args.shard, args.limit, args.mission_id)

    if tasks and not args.smoke:
        time.sleep(args.shard * 0.25)

    blocked_routes: set[str] = set()
    results = []
    for index, task in enumerate(tasks):
        mission = missions.get(task.get("mission_id"))
        if not mission:
            result = {"task_id": task["task_id"], "execution_status": "FAILED_RETRYABLE", "ok": False, "error": "Mission missing", "attempted_models": []}
        elif task["role"] == "COMPUTE_CHECKER":
            result = {"task_id": task["task_id"], "mission_id": task.get("mission_id"), "cycle": task.get("cycle"),
                      "civilization": task.get("civilization"), "team": task.get("team"), "role": task["role"],
                      "shard": args.shard, "execution_status": "HOLD_DETERMINISTIC_CHECK", "ok": False,
                      "provider": "github_actions_cpu", "model_id": None, "model_family": None, "response": "HOLD_DETERMINISTIC_CHECK",
                      "error": None, "attempted_models": [], "evidence_status": "DETERMINISTIC_CHECK_REQUIRED"}
        else:
            result = execute_one(task, mission, civ_map, blocked_routes)
        results.append(result)
        print(json.dumps({k: result.get(k) for k in ("task_id","role","ok","execution_status","provider","model_id","model_family","endpoint")}, ensure_ascii=False))
        if index + 1 < len(tasks):
            time.sleep(0.75 + ((args.shard + index) % 3) * 0.25)

    with out.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps({
        "shard": args.shard,
        "selected": len(tasks),
        "results": len(results),
        "ok": sum(bool(r.get('ok')) for r in results),
        "available_zero_euro_routes": available_zero_euro_routes(),
        "quota_circuit_breakers": sorted(blocked_routes),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
