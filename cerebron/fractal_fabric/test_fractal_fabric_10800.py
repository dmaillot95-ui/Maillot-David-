#!/usr/bin/env python3
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

BASE_WORKERS = 36
MICROS_PER_BASE = 300
TOTAL = BASE_WORKERS * MICROS_PER_BASE
MAX_THREADS = 72


def task_for(base_id: int, micro_id: int):
    value = base_id * MICROS_PER_BASE + micro_id + 1
    op = "square" if (base_id + micro_id) % 2 == 0 else "sha256"
    return {
        "base_worker": base_id,
        "micro_worker": micro_id,
        "logical_id": f"w{base_id:02d}-m{micro_id:03d}",
        "value": value,
        "op": op,
    }


def execute(task):
    if task["op"] == "square":
        result = task["value"] ** 2
    else:
        result = hashlib.sha256(str(task["value"]).encode()).hexdigest()
    proof = hashlib.sha256(
        f"{task['logical_id']}|{task['op']}|{result}".encode()
    ).hexdigest()
    return {
        "logical_id": task["logical_id"],
        "base_worker": task["base_worker"],
        "micro_worker": task["micro_worker"],
        "op": task["op"],
        "result": result,
        "proof": proof,
    }


def verify(task, out):
    if task["op"] == "square":
        expected = task["value"] * task["value"]
    else:
        expected = hashlib.sha256(str(task["value"]).encode()).hexdigest()
    expected_proof = hashlib.sha256(
        f"{task['logical_id']}|{task['op']}|{expected}".encode()
    ).hexdigest()
    return out["result"] == expected and out["proof"] == expected_proof


def main():
    tasks = [task_for(b, m) for b in range(BASE_WORKERS) for m in range(MICROS_PER_BASE)]
    assert len(tasks) == TOTAL == 10800
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as ex:
        outputs = list(ex.map(execute, tasks))
    checks = [verify(t, o) for t, o in zip(tasks, outputs)]
    unique_ids = len({o["logical_id"] for o in outputs})
    per_base = {}
    for o in outputs:
        per_base[o["base_worker"]] = per_base.get(o["base_worker"], 0) + 1
    report = {
        "schema": "cerebron-fractal-fabric-10800-v1",
        "physical_nodes": 1,
        "active_processes": 1,
        "base_workers": BASE_WORKERS,
        "micro_workers_per_base": MICROS_PER_BASE,
        "logical_micro_workers": TOTAL,
        "thread_workers_max": MAX_THREADS,
        "unique_logical_ids": unique_ids,
        "proof_checks_passed": sum(checks),
        "proof_checks_total": len(checks),
        "all_base_workers_have_300_micros": all(v == MICROS_PER_BASE for v in per_base.values()) and len(per_base) == BASE_WORKERS,
        "paid_api_calls": 0,
        "spend_eur": 0.0,
        "claim_physical_workers": 1,
    }
    assert report["unique_logical_ids"] == TOTAL
    assert report["proof_checks_passed"] == TOTAL
    assert report["all_base_workers_have_300_micros"] is True
    print(json.dumps(report, indent=2))
    with open("fractal-fabric-10800.json", "w") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()
