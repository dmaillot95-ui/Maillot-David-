#!/usr/bin/env python3
"""CEREBRON Ω World AI Registry.

Separates technical connectability from cost approval. Remote APIs are never
assumed free. Local/self-hosted routes are zero-external-API-cost candidates,
but still require an available runtime/model before routing.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

REMOTE = [
    ("openai", "OpenAI", ["general", "reasoning", "code", "vision", "audio"]),
    ("anthropic", "Anthropic Claude", ["general", "reasoning", "code", "vision"]),
    ("google_gemini", "Google Gemini", ["general", "reasoning", "code", "vision", "audio"]),
    ("xai", "xAI Grok", ["general", "reasoning", "code"]),
    ("mistral", "Mistral AI", ["general", "code", "vision"]),
    ("cohere", "Cohere", ["general", "retrieval", "embeddings"]),
    ("deepseek", "DeepSeek", ["reasoning", "math", "code"]),
    ("alibaba_qwen", "Alibaba Qwen / Model Studio", ["general", "reasoning", "math", "code", "vision"]),
    ("zai", "Z.ai / GLM", ["general", "reasoning", "code"]),
    ("groq", "Groq", ["inference", "general", "reasoning"]),
    ("cerebras", "Cerebras Inference", ["inference", "general", "reasoning"]),
    ("sambanova", "SambaNova Cloud", ["inference", "general", "reasoning"]),
    ("together", "Together AI", ["multi_model", "general", "code", "vision"]),
    ("fireworks", "Fireworks AI", ["multi_model", "general", "code"]),
    ("deepinfra", "DeepInfra", ["multi_model", "general", "code", "vision"]),
    ("nvidia_nim", "NVIDIA NIM", ["multi_model", "general", "code", "vision"]),
    ("huggingface", "Hugging Face Inference Providers", ["multi_model", "general", "math", "code", "vision"]),
    ("replicate", "Replicate", ["multi_model", "general", "vision", "audio"]),
    ("baseten", "Baseten", ["inference", "multi_model"]),
    ("featherless", "Featherless AI", ["multi_model", "general"]),
    ("novita", "Novita AI", ["multi_model", "general", "vision"]),
    ("ovh_ai", "OVHcloud AI Endpoints", ["multi_model", "general"]),
    ("scaleway", "Scaleway Generative APIs", ["multi_model", "general"]),
    ("public_ai", "Public AI", ["multi_model", "general"]),
    ("openrouter", "OpenRouter", ["gateway", "multi_model", "general", "reasoning", "math", "code"]),
    ("vercel_ai_gateway", "Vercel AI Gateway", ["gateway", "multi_model"]),
    ("cloudflare_workers_ai", "Cloudflare Workers AI", ["multi_model", "general", "embeddings"]),
]

LOCAL = [
    ("vllm", "vLLM", "vllm"),
    ("sglang", "SGLang", "python"),
    ("ollama", "Ollama", "ollama"),
    ("llama_cpp", "llama.cpp server", "llama-server"),
    ("tgi", "Text Generation Inference", "text-generation-launcher"),
    ("localai", "LocalAI", "local-ai"),
    ("bentoml", "BentoML/OpenLLM", "bentoml"),
]

MATH_MODELS = [
    {"id":"qwen_math_local", "name":"Qwen Math family", "specialties":["math","reasoning"], "formal":False},
    {"id":"deepseek_prover_local", "name":"DeepSeek Prover family", "specialties":["math","formal_proof","lean4"], "formal":True},
    {"id":"phi_reasoning_local", "name":"Phi reasoning family", "specialties":["math","reasoning","science"], "formal":False},
    {"id":"lean4", "name":"Lean 4 verifier", "specialties":["formal_proof","verification"], "formal":True},
    {"id":"sympy", "name":"SymPy", "specialties":["symbolic_math","verification"], "formal":False},
    {"id":"python_math", "name":"Python exact/numeric calculator", "specialties":["calculation","verification"], "formal":False},
]

SECRET_ENV = {
    "openai":["OPENAI_API_KEY"], "anthropic":["ANTHROPIC_API_KEY"],
    "google_gemini":["GEMINI_API_KEY","GOOGLE_API_KEY"], "xai":["XAI_API_KEY"],
    "mistral":["MISTRAL_API_KEY"], "cohere":["COHERE_API_KEY"],
    "deepseek":["DEEPSEEK_API_KEY"], "alibaba_qwen":["DASHSCOPE_API_KEY"],
    "zai":["ZAI_API_KEY"], "groq":["GROQ_API_KEY"], "cerebras":["CEREBRAS_API_KEY"],
    "sambanova":["SAMBANOVA_API_KEY"], "together":["TOGETHER_API_KEY"],
    "fireworks":["FIREWORKS_API_KEY"], "deepinfra":["DEEPINFRA_API_KEY"],
    "nvidia_nim":["NVIDIA_API_KEY"], "huggingface":["HF_TOKEN"],
    "replicate":["REPLICATE_API_TOKEN"], "openrouter":["OPENROUTER_API_KEY"],
    "vercel_ai_gateway":["AI_GATEWAY_API_KEY","VERCEL_OIDC_TOKEN"],
    "cloudflare_workers_ai":["CLOUDFLARE_API_TOKEN","CLOUDFLARE_ACCOUNT_ID"],
}


def remote_connected(pid: str) -> tuple[bool, str]:
    req = SECRET_ENV.get(pid, [])
    if not req:
        return False, "adapter_or_credentials_not_configured"
    if pid in {"google_gemini", "vercel_ai_gateway"}:
        ok = any(os.getenv(k) for k in req)
    else:
        ok = all(os.getenv(k) for k in req)
    return ok, "credentials_present" if ok else "credentials_missing"


def build_registry() -> dict:
    providers=[]
    for pid,name,spec in REMOTE:
        connected,why=remote_connected(pid)
        providers.append({
            "id":pid,"name":name,"kind":"remote_api","specialties":spec,
            "technically_connectable":True,"runtime_connected":connected,
            "cost_class":"REMOTE_COST_UNVERIFIED","zero_euro_approved":False,
            "routable_zero_euro":False,"reason":why,
        })
    for pid,name,cmd in LOCAL:
        available=bool(shutil.which(cmd))
        providers.append({
            "id":pid,"name":name,"kind":"self_hosted_runtime","specialties":["multi_model"],
            "technically_connectable":True,"runtime_connected":available,
            "cost_class":"LOCAL_ZERO_EXTERNAL_API_COST","zero_euro_approved":True,
            "routable_zero_euro":available,"reason":f"local_command:{cmd}",
        })
    return {
        "schema":"cerebron-world-ai-registry-v1",
        "spend_limit_eur":0,"paid_fallback":False,
        "provider_count":len(providers),"providers":providers,
        "math_specialists":MATH_MODELS,
        "claim_rule":"connectable != connected != zero_euro_approved != validated",
    }


def choose_specialists(task: str) -> list[str]:
    t=task.lower()
    if any(k in t for k in ["proof","prove","theorem","lean","preuve","théorème","collatz"]):
        return ["qwen_math_local","deepseek_prover_local","lean4","sympy","python_math"]
    if any(k in t for k in ["math","equation","algebra","number theory","calcul","équation"]):
        return ["qwen_math_local","phi_reasoning_local","sympy","python_math"]
    if any(k in t for k in ["code","python","program","logiciel"]):
        return ["local_multi_model","python_math"]
    return ["local_multi_model"]


def main() -> None:
    registry=build_registry()
    out=Path(os.getenv("CEREBRON_WORLD_AI_REGISTRY_OUT","cerebron/providers/world-ai-registry-runtime.json"))
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "engine":"CEREBRON_WORLD_AI_REGISTRY_V1",
        "providers":registry["provider_count"],
        "zero_euro_routable":[p["id"] for p in registry["providers"] if p["routable_zero_euro"]],
        "math_specialists":[m["id"] for m in registry["math_specialists"]],
        "spend_limit_eur":0,"paid_fallback":False,
    },ensure_ascii=False))

if __name__ == "__main__":
    main()
