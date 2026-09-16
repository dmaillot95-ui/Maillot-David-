#!/usr/bin/env python3
import json
from dataclasses import dataclass, asdict
from fractions import Fraction

# CEREBRON Ω — focused symbolic funnel v2
# Family: FIRST CONTRACTING BLOCK BARRIER Ω
# Search target: a uniform lower bound on
# Q=((2^(r+b)-3^(r+1))*t)/(2^(b-1)-1)
# for exact admissible contracting blocks.
# Q>1 is exactly the strict valley-descent condition y'<y.
# FINITE falsification/ranking only; not a proof engine.

R_MAX = 120
T_MAX = 3999
START = 2000
FUNNEL = [2000, 1000, 500, 250, 100, 50, 20, 10, 3, 1]


def v2(n: int) -> int:
    c = 0
    while n and n % 2 == 0:
        n //= 2
        c += 1
    return c


@dataclass
class Candidate:
    cid: int
    threshold_num: int
    threshold_den: int
    tested: int = 0
    falsified: int = 0
    margin_num: int = 0
    margin_den: int = 1
    score: int = 0

    @property
    def threshold(self):
        return Fraction(self.threshold_num, self.threshold_den)


def generate_candidates():
    # 2000 rational lower-bound candidates from 1.002 to 5.000, step 0.002.
    out = []
    for cid in range(START):
        num = 1002 + 2 * cid
        out.append(Candidate(cid=cid, threshold_num=num, threshold_den=1000))
    assert len(out) == START
    return out


def corpus():
    data = []
    exact_min = None
    exact_argmin = None
    for r in range(1, R_MAX + 1):
        p3 = pow(3, r + 1)
        for t in range(1, T_MAX + 1, 2):
            q = p3 * t - 1
            b = 1 + v2(q)
            gap = (1 << (r + b)) - p3
            if gap <= 0:
                continue
            den = (1 << (b - 1)) - 1
            Q = Fraction(gap * t, den)
            data.append((Q, r, b, t))
            if exact_min is None or Q < exact_min:
                exact_min = Q
                exact_argmin = (r, b, t)
    return data, exact_min, exact_argmin


def evaluate(c: Candidate, data):
    th = c.threshold
    c.tested = len(data)
    worst_margin = None
    falsified = 0
    for Q, r, b, t in data:
        if Q < th:
            falsified += 1
        margin = Q - th
        if worst_margin is None or margin < worst_margin:
            worst_margin = margin
    c.falsified = falsified
    if worst_margin is None:
        worst_margin = Fraction(0, 1)
    c.margin_num = worst_margin.numerator
    c.margin_den = worst_margin.denominator
    # Prefer zero-falsification, then strongest threshold.
    c.score = (10**12 if falsified == 0 else 0) + c.threshold_num * 10**4 - falsified
    return c


def funnel(cands):
    history = []
    current = cands
    for target in FUNNEL[1:]:
        current = sorted(
            current,
            key=lambda c: (c.falsified == 0, c.threshold, -c.falsified, c.margin_num / c.margin_den),
            reverse=True,
        )[:target]
        history.append({
            "target": target,
            "best": asdict(current[0]),
            "zero_falsification": sum(1 for c in current if c.falsified == 0),
        })
    return current[0], history


def main():
    data, qmin, argmin = corpus()
    cands = [evaluate(c, data) for c in generate_candidates()]
    winner, history = funnel(cands)
    report = {
        "schema": "cerebron-collatz-first-contracting-block-q-funnel-v2",
        "family": "FIRST CONTRACTING BLOCK BARRIER OMEGA",
        "finite_only": True,
        "claim_universal_proof": False,
        "initial_candidates": START,
        "funnel": FUNNEL,
        "corpus": {
            "r_max": R_MAX,
            "odd_t_max": T_MAX,
            "exact_relation": "b=1+v2(3^(r+1)t-1)",
            "contracting_only": True,
            "tested_exact_blocks": len(data),
        },
        "quantity": "Q=((2^(r+b)-3^(r+1))*t)/(2^(b-1)-1)",
        "meaning": "Q>1 iff the exact contracting block sends next valley strictly below starting valley",
        "observed_exact_min_Q": {"num": qmin.numerator, "den": qmin.denominator},
        "observed_argmin": {"r": argmin[0], "b": argmin[1], "t": argmin[2]},
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
