#!/usr/bin/env python3
"""CÉRÉBRON Ω Scanner + Task Scaler.

Control-plane only: classifies a mission, decomposes it into deterministic
microtasks, and maps them onto a fixed worker pool. It never claims that a
microtask was executed merely because it was planned.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter

CATEGORIES = (
    "research", "proof", "compute", "code", "vision", "multimodal",
    "red_team", "replication", "synthesis", "judge"
)

KEYWORDS = {
    "proof": ("proof", "prove", "theorem", "lemma", "preuve", "théorème", "collatz"),
    "compute": ("calculate", "calculation", "compute", "equation", "calcul", "simulation", "numeric"),
    "code": ("code", "python", "software", "workflow", "github", "api"),
    "vision": ("image", "vision", "photo", "diagram", "scan"),
    "multimodal": ("multimodal", "pdf", "document", "audio", "video"),
    "red_team": ("red team", "falsify", "attack", "counterexample", "audit"),
    "research": ("research", "search", "source", "benchmark", "état de l'art"),
}


def classify(text: str) -> list[str]:
    low = text.lower()
    hits = []
    for cat, words in KEYWORDS.items():
        if any(w in low for w in words):
            hits.append(cat)
    if not hits:
        hits = ["research", "compute", "red_team", "synthesis"]
    if "proof" in hits and "red_team" not in hits:
        hits.append("red_team")
    if "research" in hits and "replication" not in hits:
        hits.append("replication")
    hits.extend(["synthesis", "judge"])
    return [c for c in CATEGORIES if c in set(hits)]


def deterministic_id(mission: str, index: int, category: str) -> str:
    raw = f"{mission}|{index}|{category}".encode("utf-8")
    return "MT-" + hashlib.sha256(raw).hexdigest()[:24].upper()


def build_plan(mission: str, target_tasks: int, workers: int) -> dict:
    if target_tasks <= 0 or workers <= 0:
        raise ValueError("target_tasks and workers must be > 0")
    cats = classify(mission)
    tasks = []
    per_worker = Counter()
    per_category = Counter()
    for i in range(target_tasks):
        cat = cats[i % len(cats)]
        worker = i % workers
        task = {
            "task_id": deterministic_id(mission, i, cat),
            "logical_index": i,
            "category": cat,
            "worker_slot": worker,
            "status": "PLANNED",
            "execution_evidence": False,
        }
        tasks.append(task)
        per_worker[worker] += 1
        per_category[cat] += 1

    ids = [t["task_id"] for t in tasks]
    assert len(ids) == len(set(ids)), "duplicate task ids"
    counts = list(per_worker.values())
    return {
        "schema": "cerebron-scanner-scaler-v1",
        "mission": mission,
        "classified_categories": cats,
        "workers": workers,
        "tasks_planned": len(tasks),
        "unique_task_ids": len(set(ids)),
        "min_tasks_per_worker": min(counts),
        "max_tasks_per_worker": max(counts),
        "category_counts": dict(sorted(per_category.items())),
        "claim": "PLANNED logical microtasks only; not executed tasks and not independent agents",
        "tasks": tasks,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--mission", required=True)
    p.add_argument("--target-tasks", type=int, default=24000)
    p.add_argument("--workers", type=int, default=240)
    p.add_argument("--output")
    args = p.parse_args()
    plan = build_plan(args.mission, args.target_tasks, args.workers)
    payload = json.dumps(plan, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(payload + "\n")
    summary = {k: v for k, v in plan.items() if k != "tasks"}
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
