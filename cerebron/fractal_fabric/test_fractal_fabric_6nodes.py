#!/usr/bin/env python3
import hashlib, json, os
from concurrent.futures import ThreadPoolExecutor

SHARD = int(os.environ["CEREBRON_SHARD"])
BASE_PER_SHARD = 6
MICROS_PER_BASE = 300
THREADS = 12

BASE_START = SHARD * BASE_PER_SHARD
BASE_IDS = list(range(BASE_START, BASE_START + BASE_PER_SHARD))
TASKS = [
    {"base": b, "micro": m, "id": f"b{b:02d}-m{m:03d}"}
    for b in BASE_IDS
    for m in range(MICROS_PER_BASE)
]

def worker(task):
    payload = f"{task['base']}|{task['micro']}|{task['id']}".encode()
    digest = hashlib.sha256(payload).hexdigest()
    proof = hashlib.sha256((digest + task['id']).encode()).hexdigest()
    return {"id": task["id"], "digest": digest, "proof": proof}

def verify(task, out):
    payload = f"{task['base']}|{task['micro']}|{task['id']}".encode()
    digest = hashlib.sha256(payload).hexdigest()
    proof = hashlib.sha256((digest + task['id']).encode()).hexdigest()
    return out["digest"] == digest and out["proof"] == proof

def main():
    with ThreadPoolExecutor(max_workers=THREADS) as ex:
        outs = list(ex.map(worker, TASKS))
    checks = [verify(t, o) for t, o in zip(TASKS, outs)]
    report = {
        "schema": "cerebron-fractal-fabric-6nodes-shard-v1",
        "shard": SHARD,
        "base_workers": BASE_IDS,
        "base_workers_count": len(BASE_IDS),
        "micro_workers_per_base": MICROS_PER_BASE,
        "logical_micro_workers": len(TASKS),
        "thread_workers_max": THREADS,
        "unique_logical_ids": len({o['id'] for o in outs}),
        "proof_checks_passed": sum(checks),
        "proof_checks_total": len(checks),
        "github_runner_name": os.environ.get("RUNNER_NAME"),
        "github_runner_os": os.environ.get("RUNNER_OS"),
        "github_runner_arch": os.environ.get("RUNNER_ARCH"),
        "paid_api_calls": 0,
        "spend_eur": 0.0
    }
    assert report["logical_micro_workers"] == BASE_PER_SHARD * MICROS_PER_BASE
    assert report["unique_logical_ids"] == report["logical_micro_workers"]
    assert report["proof_checks_passed"] == report["proof_checks_total"]
    print(json.dumps(report, indent=2))
    with open(f"fractal-fabric-shard-{SHARD}.json", "w") as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    main()
