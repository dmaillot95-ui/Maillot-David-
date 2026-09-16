#!/usr/bin/env python3
import hashlib, json, math, random
from concurrent.futures import ThreadPoolExecutor

BASE_WORKERS = 36
MICROS_PER_BASE = 300
TOTAL = BASE_WORKERS * MICROS_PER_BASE
SEED = 20260916
random.seed(SEED)


def score_candidate(base_id, micro_id):
    # Deterministic synthetic candidate quality vector for architecture testing only.
    novelty = ((base_id * 97 + micro_id * 31) % 1000) / 1000
    evidence = ((base_id * 53 + micro_id * 67 + 11) % 1000) / 1000
    reproducibility = ((base_id * 29 + micro_id * 83 + 7) % 1000) / 1000
    cost_eff = 1.0 - (((base_id * 41 + micro_id * 19) % 1000) / 1000)
    contradiction_penalty = (((base_id * 17 + micro_id * 23) % 200) / 1000)
    total = 0.30*novelty + 0.30*evidence + 0.25*reproducibility + 0.15*cost_eff - contradiction_penalty
    cid = f"b{base_id:02d}-m{micro_id:03d}"
    proof = hashlib.sha256(f"{cid}|{novelty:.6f}|{evidence:.6f}|{reproducibility:.6f}|{cost_eff:.6f}|{total:.9f}".encode()).hexdigest()
    return {
        "id": cid,
        "base": base_id,
        "micro": micro_id,
        "score": total,
        "novelty": novelty,
        "evidence": evidence,
        "reproducibility": reproducibility,
        "cost_eff": cost_eff,
        "proof": proof,
    }


def verify(c):
    expected = hashlib.sha256(
        f"{c['id']}|{c['novelty']:.6f}|{c['evidence']:.6f}|{c['reproducibility']:.6f}|{c['cost_eff']:.6f}|{c['score']:.9f}".encode()
    ).hexdigest()
    return expected == c["proof"]


def reduce_stage(items, target):
    if target >= len(items):
        return list(items)
    # Preserve diversity: first keep best per base worker, then fill globally.
    by_base = {}
    for c in items:
        by_base.setdefault(c["base"], []).append(c)
    survivors = []
    per_base = max(1, target // BASE_WORKERS)
    for base in sorted(by_base):
        survivors.extend(sorted(by_base[base], key=lambda x: x["score"], reverse=True)[:per_base])
    seen = {c["id"] for c in survivors}
    if len(survivors) < target:
        for c in sorted(items, key=lambda x: x["score"], reverse=True):
            if c["id"] not in seen:
                survivors.append(c)
                seen.add(c["id"])
                if len(survivors) == target:
                    break
    return sorted(survivors, key=lambda x: x["score"], reverse=True)[:target]


def main():
    tasks = [(b, m) for b in range(BASE_WORKERS) for m in range(MICROS_PER_BASE)]
    with ThreadPoolExecutor(max_workers=72) as ex:
        candidates = list(ex.map(lambda bm: score_candidate(*bm), tasks))

    assert len(candidates) == TOTAL
    assert len({c['id'] for c in candidates}) == TOTAL
    assert all(verify(c) for c in candidates)

    stages = [5400, 2700, 1350, 675, 300, 150, 72, 36, 18, 9, 3, 1]
    current = candidates
    history = [{"stage": TOTAL, "proof_checks": TOTAL, "unique": TOTAL}]
    for target in stages:
        current = reduce_stage(current, target)
        assert len(current) == target
        assert len({c['id'] for c in current}) == target
        assert all(verify(c) for c in current)
        history.append({"stage": target, "proof_checks": target, "unique": target})

    winner = current[0]
    report = {
        "schema": "cerebron-degressive-campaign-test-v1",
        "physical_nodes_claimed": 1,
        "base_workers": BASE_WORKERS,
        "micro_workers_per_base": MICROS_PER_BASE,
        "logical_micro_workers": TOTAL,
        "thread_workers_max": 72,
        "stages": history,
        "winner": {"id": winner["id"], "score": winner["score"], "proof": winner["proof"]},
        "all_proofs_verified": True,
        "paid_api_calls": 0,
        "spend_eur": 0.0,
        "note": "Synthetic deterministic architecture test; validates funnel mechanics, not solution quality on an external real-world problem."
    }
    print(json.dumps(report, indent=2))
    with open("degressive-campaign-test.json", "w") as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    main()
