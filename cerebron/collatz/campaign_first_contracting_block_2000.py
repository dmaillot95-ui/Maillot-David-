#!/usr/bin/env python3
import json
from dataclasses import dataclass, asdict

# CEREBRON Ω — focused symbolic funnel
# Family: FIRST CONTRACTING BLOCK BARRIER Ω
# This is a finite falsification/ranking campaign, not a proof engine.

R_MAX = 80
B_MAX = 80
START = 2000
FUNNEL = [2000, 1000, 500, 250, 100, 50, 20, 10, 3, 1]


def v2(n: int) -> int:
    c = 0
    while n and n % 2 == 0:
        n //= 2
        c += 1
    return c


def block_next(r: int, b: int, t: int) -> int:
    # y+1 = 2^(r+1)t, t odd
    num = pow(3, r + 1) * t - 1
    den = 1 << (b - 1)
    if num % den:
        return -1
    return num // den


def y_from(r: int, t: int) -> int:
    return (1 << (r + 1)) * t - 1


@dataclass
class Candidate:
    cid: int
    r_cap: int
    b_cap: int
    margin_num: int
    margin_den: int
    require_exact_v2: bool
    score: int = 0
    tested: int = 0
    falsified: int = 0
    survivors: int = 0


def generate_candidates():
    out = []
    cid = 0
    # 20 x 10 x 10 = 2000 structured variants in one proof family.
    for r_cap in range(4, 84, 4):            # 20
        for b_cap in range(4, 24, 2):        # 10
            for margin_num in range(1, 11):  # 10
                out.append(Candidate(
                    cid=cid,
                    r_cap=r_cap,
                    b_cap=b_cap,
                    margin_num=margin_num,
                    margin_den=10,
                    require_exact_v2=True,
                ))
                cid += 1
    assert len(out) == START
    return out


def evaluate(c: Candidate):
    # Falsification corpus: admissible local Collatz blocks only.
    # Candidate claims: for exact 2-adic block data in its region,
    # if alpha<1 and contraction margin exceeds threshold, next valley falls below start.
    falsified = 0
    tested = 0
    survivors = 0
    for r in range(1, min(R_MAX, c.r_cap) + 1):
        for t in range(1, 401, 2):
            q = pow(3, r + 1) * t - 1
            b = 1 + v2(q)
            if b < 2 or b > min(B_MAX, c.b_cap):
                continue
            # contracting block only
            gap = (1 << (r + b)) - pow(3, r + 1)
            if gap <= 0:
                continue
            tested += 1
            y = y_from(r, t)
            yn = block_next(r, b, t)
            if yn < 0:
                falsified += 1
                continue
            # normalized local contraction pressure
            lhs = gap * t
            rhs = (1 << (b - 1)) - 1
            threshold_ok = lhs * c.margin_den >= rhs * c.margin_num
            if threshold_ok:
                survivors += 1
                # Claim predicts strict descent below current valley.
                if not (yn < y):
                    falsified += 1
    c.tested = tested
    c.falsified = falsified
    c.survivors = survivors
    # reward broad tested region, exactness, and zero falsification
    c.score = (1000000 if falsified == 0 else 0) + survivors * 10 + tested - falsified * 100000
    return c


def funnel(cands):
    history = []
    current = cands
    for target in FUNNEL[1:]:
        current = sorted(
            current,
            key=lambda c: (c.falsified == 0, c.score, c.survivors, c.tested, -c.cid),
            reverse=True,
        )[:target]
        history.append({
            "target": target,
            "best": asdict(current[0]),
            "zero_falsification": sum(1 for c in current if c.falsified == 0),
        })
    return current[0], history


def main():
    cands = [evaluate(c) for c in generate_candidates()]
    winner, history = funnel(cands)
    report = {
        "schema": "cerebron-collatz-first-contracting-block-funnel-v1",
        "family": "FIRST CONTRACTING BLOCK BARRIER OMEGA",
        "finite_only": True,
        "claim_universal_proof": False,
        "initial_candidates": START,
        "funnel": FUNNEL,
        "corpus": {
            "r_max": R_MAX,
            "b_max": B_MAX,
            "odd_t_max": 399,
            "exact_block_relation": "b=1+v2(3^(r+1)t-1)",
        },
        "winner": asdict(winner),
        "history": history,
        "paid_api_calls": 0,
        "spend_eur": 0.0,
    }
    print(json.dumps(report, indent=2))
    with open("collatz-first-contracting-block-funnel.json", "w") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()
