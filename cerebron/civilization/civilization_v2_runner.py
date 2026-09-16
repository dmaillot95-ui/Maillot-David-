#!/usr/bin/env python3
"""Execution entrypoints for the 36-worker CEREBRON Civilization V2 loop."""
from __future__ import annotations

import argparse
import glob
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCTRINE = ROOT / "cerebron" / "civilization" / "CAPABILITIES_V2.md"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def compact_memory(path="out/memory/memory-packet.json", synthesis=False):
    mem = load_json(path)
    out = {
        "summary": mem["summary"],
        "role_performance": mem["role_performance"],
        "top_failure_modes": mem["top_failure_modes"][:20 if synthesis else 12],
        "outcome_divergence_sample": mem["outcome_divergence_sample"][:20 if synthesis else 10],
        "instructions": mem["instructions"],
    }
    if not synthesis:
        out["candidate_sample"] = mem["candidate_sample"][:10]
    return out


def invoke(prompt: str):
    os.environ["CEREBRON_LOCAL_CPU_PROMPT"] = prompt
    from cerebron.providers.local_cpu_llm import main
    main()


def worker():
    role = os.environ["ROLE"]
    mode = os.environ["MODE"]
    doctrine = DOCTRINE.read_text(encoding="utf-8")
    memory = compact_memory()
    prompt = "\n".join([
        "You are one real local CEREBRON Civilization worker.",
        f"ROLE={role}",
        f"NOVELTY_OPERATOR={mode}",
        "",
        "Apply ALL C1-C11 capabilities below as an executable protocol, not prose to summarize.",
        "",
        "DOCTRINE:",
        doctrine,
        "",
        "CURRENT CAMPAIGN EXPERIENCE (metadata is routing evidence, not proof of semantic truth):",
        json.dumps(memory, ensure_ascii=False),
        "",
        f"MISSION: Develop one concrete civilization capability upgrade in domain {role} using {mode}. Explicitly reuse campaign experience where relevant. Do not treat COMPLETED as scientific validation.",
        "",
        "MANDATORY CHAIN:",
        "TASK -> EXPERIENCE REPLAY -> DECOMPOSE -> DIVERSE SEARCH -> ATOMIC CLAIMS -> CONTRADICTION GRAPH -> COGNITIVE ERROR CORRECTION -> DYNAMIC COALITION -> PROOF/REDTEAM -> OBJECTIVE SCORE -> ABLATION -> STRATEGY MEMORY -> ROUTER UPDATE.",
        "",
        "Return: 1) atomic claims; 2) historical evidence used and limits; 3) contradiction/failure graph; 4) dynamic coalition; 5) cognitive error-correction rule; 6) measurable benchmark and threshold; 7) best-single and matched-compute baselines; 8) ablation; 9) decisive falsifier; 10) Strategy Memory entry only if evidence justifies promotion; 11) router update if justified; 12) reject/quarantine conditions.",
        "",
        "Do not claim superintelligence. Do not answer merely with more agents, more context, more data, or a larger model. CLAIM<=EVIDENCE.",
    ])
    invoke(prompt)
    p = load_json(os.environ.get("CEREBRON_LOCAL_CPU_OUT", "out/result.json"))
    assert p["ok"] is True
    assert p["spend_limit_eur"] == 0
    assert p["paid_fallback"] is False
    assert p["api_key_used"] is False
    p["role"] = role
    p["operator"] = mode
    p["worker_id"] = f"CIV-{role}-{mode}"
    p["capability_protocol"] = "C1-C11"
    p["experience_replay"] = True
    Path("out/result.json").write_text(json.dumps(p, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def synthesis():
    files = sorted(glob.glob("civilization/*/result.json"))
    assert len(files) == 36, len(files)
    rows = [load_json(f) for f in files]
    assert len({r["worker_id"] for r in rows}) == 36
    assert len({r["role"] for r in rows}) == 12
    assert {r["operator"] for r in rows} == {"INVERT", "TRANSFER", "EMERGE"}
    assert all(r["ok"] and r["spend_limit_eur"] == 0 and not r["paid_fallback"] and not r["api_key_used"] for r in rows)
    assert all(r.get("capability_protocol") == "C1-C11" and r.get("experience_replay") is True for r in rows)

    Path("out").mkdir(exist_ok=True)
    Path("out/workers.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    packet = "\n\n".join(f"{r['worker_id']}:\n{r['answer']}" for r in rows)
    Path("out/packet.txt").write_text(packet, encoding="utf-8")

    doctrine = DOCTRINE.read_text(encoding="utf-8")
    memory = compact_memory(synthesis=True)
    prompt = "\n".join([
        "You are the synthesis/evidence gate for 36 CEREBRON Civilization workers. Apply C1-C11 strictly.",
        "Historical COMPLETED status is execution evidence only, not semantic truth. Never majority-vote a claim into truth. Cluster contradictions, preserve disagreement, and require PROOF/REDTEAM/EVALUATOR gates before promotion to Strategy Memory.",
        "",
        "Return exactly:",
        "A) 10 strongest distinct candidate capabilities;",
        "B) for each: mechanism, workers combined, historical evidence used, contradiction status, benchmark, best-single baseline, matched-compute baseline, ablation, falsifier, evidence needed;",
        "C) TOP 3 multiplicative combinations;",
        "D) 5 proposals rejected as weak/redundant/unfalsifiable;",
        "E) highest-value historical divergence to inspect next;",
        "F) one smallest executable benchmark experiment;",
        "G) Strategy Memory candidates and what additional evidence each needs;",
        "H) Router updates justified by measured evidence only;",
        "I) established / derived / conjectural / not demonstrated.",
        "Never claim superintelligence without benchmark evidence.",
        "",
        "DOCTRINE:", doctrine,
        "",
        "CAMPAIGN MEMORY:", json.dumps(memory, ensure_ascii=False),
        "",
        "WORKERS:", packet,
    ])
    invoke(prompt)
    p = load_json(os.environ.get("CEREBRON_LOCAL_CPU_OUT", "out/synthesis.json"))
    assert p["ok"] is True and p["spend_limit_eur"] == 0 and not p["paid_fallback"] and not p["api_key_used"]
    print(p["answer"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["worker", "synthesis"])
    args = ap.parse_args()
    worker() if args.mode == "worker" else synthesis()


if __name__ == "__main__":
    main()
