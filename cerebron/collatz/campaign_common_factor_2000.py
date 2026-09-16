#!/usr/bin/env python3
import json
import itertools
from collections import Counter

# CEREBRON Ω — FACTEUR COMMUN Ω
# Structural mining only: this does NOT prove Collatz or universal cycle exclusion.

FACTORS = {
    "GAP": {"arith", "global"},
    "D_DIV_S": {"arith", "closure"},
    "PREFIX_K": {"dynamic", "minimum", "closure"},
    "RATIO_BARRIER": {"dynamic", "minimum"},
    "MIN_LOCAL": {"minimum", "local"},
    "RAMP_V2": {"adic", "local"},
    "BLOCK_AFFINE": {"dynamic", "local"},
    "BLOCK_CONTRACTION": {"dynamic", "local", "minimum"},
    "EXACT_B": {"adic", "local"},
    "PRIME_SIEVE": {"arith", "modular"},
    "ROTATION": {"closure", "minimum"},
    "PRODUCT_ALPHA": {"global", "dynamic"},
}

CORE_DOMAINS = {"arith", "dynamic", "minimum", "closure", "adic"}
FUNNEL = [2000, 1000, 500, 250, 100, 50, 20, 10, 3, 1]


def redundancy_penalty(combo):
    # Penalize overpacking factors that cover the same narrow role without adding a new domain.
    penalty = 0
    for a, b in itertools.combinations(combo, 2):
        sa, sb = FACTORS[a], FACTORS[b]
        inter = len(sa & sb)
        if inter >= 2:
            penalty += inter - 1
    return penalty


def bridge_bonus(combo):
    s = set(combo)
    bonus = 0
    # Bridges that connect distinct mechanisms already present in the checkpoint.
    bridges = [
        {"PREFIX_K", "EXACT_B"},
        {"BLOCK_CONTRACTION", "RAMP_V2"},
        {"GAP", "PRODUCT_ALPHA"},
        {"D_DIV_S", "PREFIX_K"},
        {"ROTATION", "PREFIX_K"},
        {"GAP", "BLOCK_CONTRACTION"},
        {"D_DIV_S", "PRIME_SIEVE"},
    ]
    for pair in bridges:
        if pair <= s:
            bonus += 5
    return bonus


def score(combo):
    covered = set().union(*(FACTORS[x] for x in combo))
    core_cov = len(covered & CORE_DOMAINS)
    domain_cov = len(covered)
    closure = 3 if "closure" in covered else 0
    minimum = 3 if "minimum" in covered else 0
    adic = 3 if "adic" in covered else 0
    compact = max(0, 8 - len(combo))
    return (
        core_cov * 100
        + domain_cov * 20
        + closure + minimum + adic
        + bridge_bonus(combo)
        + compact
        - 3 * redundancy_penalty(combo)
    )


def generate_2000():
    names = sorted(FACTORS)
    pool = []
    # Enumerate compact proof architectures first; deterministic selection of 2000.
    for k in range(3, 8):
        for c in itertools.combinations(names, k):
            pool.append(c)
    assert len(pool) >= 2000
    # diversity: interleave by size and lexicographic hash-like order
    pool.sort(key=lambda c: (sum(ord(ch) for x in c for ch in x) % 997, len(c), c))
    return pool[:2000]


def funnel(items):
    current = items
    history = []
    for target in FUNNEL[1:]:
        current = sorted(current, key=lambda x: (x["score"], -len(x["combo"]), x["combo"]), reverse=True)[:target]
        factor_counts = Counter(f for x in current for f in x["combo"])
        pair_counts = Counter()
        for x in current:
            for p in itertools.combinations(sorted(x["combo"]), 2):
                pair_counts[p] += 1
        history.append({
            "target": target,
            "top_factors": factor_counts.most_common(6),
            "top_pairs": [[list(k), v] for k, v in pair_counts.most_common(6)],
            "best": current[0],
        })
    return current[0], history


def main():
    combos = generate_2000()
    items = []
    for i, c in enumerate(combos):
        covered = sorted(set().union(*(FACTORS[x] for x in c)))
        items.append({
            "cid": i,
            "combo": list(c),
            "score": score(c),
            "domains": covered,
            "core_domains_covered": len(set(covered) & CORE_DOMAINS),
            "redundancy_penalty": redundancy_penalty(c),
            "bridge_bonus": bridge_bonus(c),
        })

    winner, history = funnel(items)

    # Common factors/pairs among final 50 are more informative than single winner.
    top50 = sorted(items, key=lambda x: (x["score"], -len(x["combo"]), x["combo"]), reverse=True)[:50]
    fc = Counter(f for x in top50 for f in x["combo"])
    pc = Counter()
    for x in top50:
        for p in itertools.combinations(sorted(x["combo"]), 2):
            pc[p] += 1

    report = {
        "schema": "cerebron-collatz-common-factor-funnel-v1",
        "finite_structural_mining_only": True,
        "claim_universal_proof": False,
        "initial_architectures": 2000,
        "funnel": FUNNEL,
        "factor_count": len(FACTORS),
        "winner": winner,
        "top50_common_factors": fc.most_common(),
        "top50_common_pairs": [[list(k), v] for k, v in pc.most_common(20)],
        "history": history,
        "paid_api_calls": 0,
        "spend_eur": 0.0,
    }
    print(json.dumps(report, indent=2))
    with open("collatz-common-factor-funnel.json", "w") as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    main()
