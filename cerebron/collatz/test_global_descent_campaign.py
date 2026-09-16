#!/usr/bin/env python3
import json, math, hashlib
from concurrent.futures import ThreadPoolExecutor

BASE_WORKERS = 36
MICROS_PER_BASE = 300
TOTAL_MICROS = BASE_WORKERS * MICROS_PER_BASE
MAX_ODD = 2_000_001  # finite stress-test domain, odds only
MAX_STEPS = 10_000


def v2(n:int)->int:
    c=0
    while n%2==0:
        n//=2; c+=1
    return c


def T(n:int)->int:
    m=3*n+1
    return m >> v2(m)


def first_descent(n:int):
    x=n
    for k in range(1, MAX_STEPS+1):
        x=T(x)
        if x < n:
            return k, x
    return None, x


def worker_task(idx:int):
    # Partition odd n>1 by logical micro-worker id modulo TOTAL_MICROS.
    # This is a finite verification only; it is not a proof of the universal theorem.
    checked=0
    worst_k=0
    worst_n=None
    failures=[]
    start=3 + 2*idx
    stride=2*TOTAL_MICROS
    n=start
    while n <= MAX_ODD:
        k,x=first_descent(n)
        checked += 1
        if k is None:
            failures.append({"n":n,"last":x})
            if len(failures)>=3:
                break
        elif k>worst_k:
            worst_k=k; worst_n=n
        n += stride
    proof = hashlib.sha256(f"{idx}|{checked}|{worst_k}|{worst_n}|{failures}".encode()).hexdigest()
    return {"micro":idx,"base":idx//MICROS_PER_BASE,"checked":checked,"worst_k":worst_k,"worst_n":worst_n,"failures":failures,"proof":proof}


def main():
    with ThreadPoolExecutor(max_workers=72) as ex:
        rows=list(ex.map(worker_task, range(TOTAL_MICROS)))
    total_checked=sum(r['checked'] for r in rows)
    failures=[f for r in rows for f in r['failures']]
    worst=max(rows, key=lambda r:r['worst_k'])
    counts=[0]*BASE_WORKERS
    for r in rows: counts[r['base']]+=1
    report={
        "schema":"cerebron-collatz-global-descent-finite-test-v1",
        "target_theorem":"for every odd n>1, exists k>=1 with T^k(n)<n",
        "implication":"if proved universally, Collatz follows by strong induction/well-ordering",
        "finite_only":True,
        "max_odd":MAX_ODD,
        "base_workers":BASE_WORKERS,
        "micro_workers_per_base":MICROS_PER_BASE,
        "logical_micro_workers":TOTAL_MICROS,
        "thread_workers_max":72,
        "checked_odds":total_checked,
        "counterexamples_found":len(failures),
        "worst_first_descent_steps":worst['worst_k'],
        "worst_n":worst['worst_n'],
        "all_base_workers_have_300_micros":all(c==MICROS_PER_BASE for c in counts),
        "paid_api_calls":0,
        "spend_eur":0.0,
        "claim_universal_proof":False
    }
    assert report['all_base_workers_have_300_micros']
    assert report['logical_micro_workers']==10800
    print(json.dumps(report,indent=2))
    with open('collatz-global-descent-finite-test.json','w') as f:
        json.dump(report,f,indent=2)

if __name__=='__main__': main()
