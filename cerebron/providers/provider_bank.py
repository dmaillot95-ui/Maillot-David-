#!/usr/bin/env python3
"""CEREBRON Ω Provider Bank 100 — zero-euro registry.

The registry is deliberately conservative: a candidate is never routed merely
because it appears here. Activation requires free-status approval AND a usable
connection/local runtime. Paid fallback is forbidden globally.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

NAMES = [
"Google Gemini API","Groq","OpenRouter","Cloudflare Workers AI","Mistral API","Cohere","Hugging Face Inference","Vercel AI Gateway","SambaNova Cloud","NVIDIA NIM / Build","Z.ai / GLM","Cerebras Inference","AI Gateway HQ","EUrouter","Jina AI","Alibaba Cloud Model Studio","Modal","AKI.IO","Baseten","Beam","Fireworks AI","Novita AI","DeepInfra","Nscale","OVHcloud AI Endpoints","Scaleway Generative APIs","Together AI","Replicate","fal.ai","Featherless AI","Public AI","WaveSpeedAI","Hyperbolic","Nebius AI Studio","Inference.net","AI21","Upstage","NLP Cloud","Monster API","SiliconFlow","IonRouter","Infercom","Cortecs AI","GreenPT","Miapi","Requesty","Runware","TokensMind","Tokenware","Regolo","CodingPlanX","LLMWise","NanoGPT","2kw.ai","Berget AI","AISIX","ARK Labs","Parity Layer","Voyage AI","DeepSeek API","Amazon Bedrock","Anthropic","OpenAI API","Cerebrium","Lambda Cloud","RunPod","Vast.ai","Hyperstack","Packet.ai","Verda","Taiga Cloud","Theta EdgeCloud","TensorX","Synexa","Airon","General Compute","Geodd","Hostnot GPU","IONOS AI Model Hub","LLM Tech","Varion","AiQu","Opper","Project Zero","Openspender","OurToken","FerryAPI","Fast Pivot","LibertAI","SimpleLLM","vLLM self-hosted","SGLang self-hosted","BentoML","AISIX self-hosted","Beam open-source/serverless stack","LocalAI","Ollama","llama.cpp server","Text Generation Inference","OpenLLM/BentoML local inference"
]

IDS = [
"google_gemini","groq","openrouter","cloudflare_workers_ai","mistral","cohere","huggingface","vercel_ai_gateway","sambanova","nvidia_nim","zai","cerebras","ai_gateway_hq","eurouter","jina","alibaba_model_studio","modal","aki_io","baseten","beam","fireworks","novita","deepinfra","nscale","ovh_ai_endpoints","scaleway_genai","together","replicate","fal","featherless","public_ai","wavespeed","hyperbolic","nebius","inference_net","ai21","upstage","nlp_cloud","monster_api","siliconflow","ionrouter","infercom","cortecs","greenpt","miapi","requesty","runware","tokensmind","tokenware","regolo","codingplanx","llmwise","nanogpt","two_kw_ai","berget_ai","aisix","ark_labs","parity_layer","voyage_ai","deepseek","amazon_bedrock","anthropic","openai","cerebrium","lambda_cloud","runpod","vast_ai","hyperstack","packet_ai","verda","taiga_cloud","theta_edgecloud","tensorx","synexa","airon","general_compute","geodd","hostnot_gpu","ionos_ai_model_hub","llm_tech","varion","aiqu","opper","project_zero","openspender","ourtoken","ferryapi","fast_pivot","libertai","simplellm","vllm_self_hosted","sglang_self_hosted","bentoml","aisix_self_hosted","beam_open_source","localai","ollama","llama_cpp_server","tgi","openllm_bentoml"
]

VERIFIED_FREE = {
"google_gemini","groq","openrouter","cloudflare_workers_ai","mistral","cohere","huggingface",
"vllm_self_hosted","sglang_self_hosted","bentoml","localai","ollama","llama_cpp_server","tgi","openllm_bentoml"
}
SELF_HOSTED = {"vllm_self_hosted","sglang_self_hosted","bentoml","aisix_self_hosted","beam_open_source","localai","ollama","llama_cpp_server","tgi","openllm_bentoml"}
SECRET_ENV = {
"google_gemini":["GEMINI_API_KEY","GOOGLE_API_KEY"],
"groq":["GROQ_API_KEY"],
"openrouter":["OPENROUTER_API_KEY"],
"cloudflare_workers_ai":["CLOUDFLARE_API_TOKEN","CLOUDFLARE_ACCOUNT_ID"],
"mistral":["MISTRAL_API_KEY"],
"cohere":["COHERE_API_KEY"],
"huggingface":["HF_TOKEN"],
"vercel_ai_gateway":["AI_GATEWAY_API_KEY","VERCEL_OIDC_TOKEN"],
"sambanova":["SAMBANOVA_API_KEY"],"nvidia_nim":["NVIDIA_API_KEY"],"zai":["ZAI_API_KEY"],
"cerebras":["CEREBRAS_API_KEY"],"jina":["JINA_API_KEY"],"fireworks":["FIREWORKS_API_KEY"],
"deepinfra":["DEEPINFRA_API_KEY"],"together":["TOGETHER_API_KEY"],"replicate":["REPLICATE_API_TOKEN"],
"deepseek":["DEEPSEEK_API_KEY"],"anthropic":["ANTHROPIC_API_KEY"],"openai":["OPENAI_API_KEY"],
"alibaba_model_studio":["CEREBRON_ALIBABA_WORKER_URL"],
"scaleway_genai":["CEREBRON_SCALEWAY_WORKER_URL"]
}
LOCAL_COMMAND = {"vllm_self_hosted":"vllm","sglang_self_hosted":"python","bentoml":"bentoml","localai":"local-ai","ollama":"ollama","llama_cpp_server":"llama-server","tgi":"text-generation-launcher","openllm_bentoml":"openllm"}

assert len(NAMES) == len(IDS) == 100

def connected(pid: str) -> tuple[bool,str]:
    if pid == "huggingface":
        return True, "public_route_available"
    if pid in SELF_HOSTED:
        cmd = LOCAL_COMMAND.get(pid)
        return (bool(cmd and shutil.which(cmd)), f"local_command:{cmd or 'unspecified'}")
    req = SECRET_ENV.get(pid, [])
    if not req:
        return False, "no_probe_adapter_yet"
    if pid == "google_gemini":
        ok = any(os.getenv(x) for x in req)
    else:
        ok = all(os.getenv(x) for x in req)
    return ok, "credentials_present" if ok else "credentials_missing"

def build_bank() -> dict:
    providers=[]
    for rank,(pid,name) in enumerate(zip(IDS,NAMES),1):
        is_free = pid in VERIFIED_FREE
        is_connected, reason = connected(pid)
        status = "VERIFIED_FREE" if is_free else "NEEDS_VERIFICATION"
        runtime = "AVAILABLE" if is_connected else "UNAVAILABLE"
        routable = bool(is_free and is_connected)
        providers.append({
            "rank":rank,"id":pid,"name":name,"status":status,
            "mode":"self_hosted" if pid in SELF_HOSTED else "provider",
            "runtime":runtime,"routable":routable,"allow_paid":False,
            "probe_reason":reason,"secret_env":SECRET_ENV.get(pid,[])
        })
    return {"schema":"cerebron-provider-bank-v1","provider_count":100,"spend_limit_eur":0,
            "paid_fallback":False,"providers":providers}

def main() -> None:
    bank=build_bank()
    out=Path(os.getenv("CEREBRON_PROVIDER_BANK_OUT","cerebron/providers/provider-bank-runtime.json"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bank,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    routable=[p["id"] for p in bank["providers"] if p["routable"]]
    print(json.dumps({"engine":"CEREBRON_PROVIDER_BANK_100","providers":100,"routable":len(routable),"routable_ids":routable,"spend_limit_eur":0},ensure_ascii=False))

if __name__ == "__main__":
    main()
