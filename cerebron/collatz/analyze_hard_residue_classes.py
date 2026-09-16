#!/usr/bin/env python3
import json
from collections import defaultdict

MAX_ODD = 5_000_001
MOD_POW = 12
MOD = 1 << MOD_POW
MAX_STEPS = 10000


def v2(n: int) -> int:
    c = 0
    while n % 2 == 0:
        n //= 2
        c += 1
    return c


def T(n: int) -> int:
    m = 3 * n + 1
    return m >> v2(m)


def first_descent_steps(n: int):
    x = n
    for k in range(1, MAX_STEPS + 1):
        x = T(x)
        if x < n:
            return k
    return None


def main():
    stats = defaultdict(lambda: {"count": 0, "sum_steps": 0, "max_steps": 0, "worst_n": None})
    global_max = 0
    global_worst = None
    checked = 0
    unresolved = []

    for n in range(3, MAX_ODD + 1, 2):
        s = first_descent_steps(n)
        checked += 1
        if s is None:
            unresolved.append(n)
            continue
        r = n % MOD
        d = stats[r]
        d["count"] += 1
        d["sum_steps"] += s
        if s > d["max_steps"]:
            d["max_steps"] = s
            d["worst_n"] = n
        if s > global_max:
            global_max = s
            global_worst = n

    classes = []
    for r, d in stats.items():
        classes.append({
            "residue": r,
            "count": d["count"],
            "mean_steps": d["sum_steps"] / d["count"],
            "max_steps": d["max_steps"],
            "worst_n": d["worst_n"],
        })

    hardest = sorted(classes, key=lambda x: (x["max_steps"], x["mean_steps"]), reverse=True)[:36]
    report = {
        "schema": "cerebron-collatz-hard-residue-classes-v1",
        "finite_only": True,
        "max_odd": MAX_ODD,
        "checked_odds": checked,
        "modulus": MOD,
        "modulus_power": MOD_POW,
        "odd_residue_classes": len(classes),
        "counterexamples_found": len(unresolved),
        "global_worst_first_descent_steps": global_max,
        "global_worst_n": global_worst,
        "top_36_hard_classes": hardest,
        "claim_general_proof": False,
        "paid_api_calls": 0,
        "spend_eur": 0.0,
    }
    assert report["odd_residue_classes"] == MOD // 2
    assert report["counterexamples_found"] == 0
    print(json.dumps(report, indent=2))
    with open("collatz-hard-residue-classes.json", "w") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()
