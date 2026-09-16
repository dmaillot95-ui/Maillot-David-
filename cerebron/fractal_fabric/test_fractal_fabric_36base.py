#!/usr/bin/env python3
import hashlib, json, time
from concurrent.futures import ThreadPoolExecutor

BASE_WORKERS = 36
REPLICAS = 28
LOGICAL_WORKERS = BASE_WORKERS * REPLICAS
THREADS = 36

ROLES = [
    "ARCHITECTURE","SCIENCE","INFRASTRUCTURE","ECONOMY","GOVERNANCE","KNOWLEDGE",
    "INDUSTRY","CULTURE","SECURITY","EXPLORATION","REDTEAM","EVALUATOR"
]
LENSES = ["INVERT","TRANSFER","EMERGE"]
BASE_IDENTITIES = [f"{r}:{l}" for r in ROLES for l in LENSES]
assert len(BASE_IDENTITIES) == BASE_WORKERS

CACHE = {}

def task_for(i):
    base_id = BASE_IDENTITIES[i % BASE_WORKERS]
    replica = i // BASE_WORKERS
    value = i + 1
    op = "square" if i % 2 == 0 else "sha256"
    return {"id": f"w{i:04d}", "base_id": base_id, "replica": replica, "value": value, "op": op}

TASKS = [task_for(i) for i in range(LOGICAL_WORKERS)]

def canonical(task):
    return json.dumps(task, sort_keys=True, separators=(",", ":"))

def micro_worker(task):
    key = hashlib.sha256(canonical(task).encode()).hexdigest()
    if key in CACHE:
        return {**CACHE[key], "cache_hit": True}
    t0 = time.perf_counter()
    if task["op"] == "square":
        result = task["value"] ** 2
    else:
        result = hashlib.sha256(str(task["value"]).encode()).hexdigest()
    out = {
        "task_id": task["id"],
        "base_id": task["base_id"],
        "replica": task["replica"],
        "result": result,
        "proof": hashlib.sha256(f"{task['id']}|{task['base_id']}|{result}".encode()).hexdigest(),
        "runtime_s": time.perf_counter() - t0,
        "cache_hit": False,
    }
    CACHE[key] = dict(out)
    return out

def audit(task, out):
    if task["op"] == "square":
        expected = task["value"] * task["value"]
    else:
        expected = hashlib.sha256(str(task["value"]).encode()).hexdigest()
    return out["result"] == expected and out["base_id"] == task["base_id"]

def run_round():
    with ThreadPoolExecutor(max_workers=THREADS) as ex:
        results = list(ex.map(micro_worker, TASKS))
    checks = [audit(t, r) for t, r in zip(TASKS, results)]
    return results, checks

def main():
    first, checks1 = run_round()
    second, checks2 = run_round()
    base_counts = {b: 0 for b in BASE_IDENTITIES}
    for r in first:
        base_counts[r["base_id"]] += 1
    report = {
        "schema": "cerebron-fractal-fabric-36base-v1",
        "physical_nodes": 1,
        "active_processes": 1,
        "base_workers": BASE_WORKERS,
        "base_worker_identities": len(BASE_IDENTITIES),
        "replicas_per_base": REPLICAS,
        "logical_workers": LOGICAL_WORKERS,
        "thread_workers_max": THREADS,
        "first_round_cache_hits": sum(r["cache_hit"] for r in first),
        "second_round_cache_hits": sum(r["cache_hit"] for r in second),
        "proof_checks_passed": sum(checks1) + sum(checks2),
        "proof_checks_total": len(checks1) + len(checks2),
        "all_base_workers_represented": all(v == REPLICAS for v in base_counts.values()),
        "duplicate_result_ids": len({r["task_id"] for r in first}) != len(first),
        "claim_superintelligence": False,
        "paid_api_calls": 0,
        "spend_eur": 0.0,
    }
    assert report["base_workers"] == 36
    assert report["logical_workers"] == 1008
    assert report["second_round_cache_hits"] == LOGICAL_WORKERS
    assert report["proof_checks_passed"] == report["proof_checks_total"]
    assert report["all_base_workers_represented"] is True
    assert report["duplicate_result_ids"] is False
    print(json.dumps(report, indent=2))
    with open("fractal-fabric-36base.json", "w") as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    main()
