#!/usr/bin/env python3
import hashlib, json, os, time
from concurrent.futures import ThreadPoolExecutor

N = int(os.getenv("CEREBRON_SCALE_TASKS", "1000"))
THREADS = int(os.getenv("CEREBRON_SCALE_THREADS", "32"))
TASKS = [
    {"id": f"t{i}", "value": i, "op": "square" if i % 2 == 0 else "sha256"}
    for i in range(1, N + 1)
]
CACHE = {}


def canonical(task):
    return json.dumps(task, sort_keys=True, separators=(",", ":"))


def micro_worker(task):
    key = hashlib.sha256(canonical(task).encode()).hexdigest()
    cached = CACHE.get(key)
    if cached is not None:
        return {**cached, "cache_hit": True}
    t0 = time.perf_counter()
    if task["op"] == "square":
        result = task["value"] ** 2
    else:
        result = hashlib.sha256(str(task["value"]).encode()).hexdigest()
    out = {
        "task_id": task["id"],
        "result": result,
        "proof": hashlib.sha256(f"{task['id']}|{task['op']}|{result}".encode()).hexdigest(),
        "runtime_s": time.perf_counter() - t0,
        "cache_hit": False,
    }
    CACHE[key] = dict(out)
    return out


def red_team(task, out):
    if task["op"] == "square":
        expected = task["value"] * task["value"]
    else:
        expected = hashlib.sha256(str(task["value"]).encode()).hexdigest()
    return out["result"] == expected


def run_round(tasks):
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=THREADS) as ex:
        results = list(ex.map(micro_worker, tasks))
    audits = [red_team(t, r) for t, r in zip(tasks, results)]
    return results, audits, time.perf_counter() - t0


def main():
    first, audits1, first_s = run_round(TASKS)
    second, audits2, second_s = run_round(TASKS)
    unique_ids = len({r["task_id"] for r in first})
    report = {
        "schema": "cerebron-fractal-fabric-scale-v1",
        "physical_nodes": 1,
        "active_processes": 1,
        "thread_workers_max": THREADS,
        "logical_micro_workers": N,
        "tasks": N,
        "first_round_runtime_s": first_s,
        "second_round_runtime_s": second_s,
        "first_round_cache_hits": sum(bool(r["cache_hit"]) for r in first),
        "second_round_cache_hits": sum(bool(r["cache_hit"]) for r in second),
        "proof_checks_passed": sum(audits1) + sum(audits2),
        "proof_checks_total": len(audits1) + len(audits2),
        "unique_result_ids": unique_ids,
        "duplicate_result_ids": unique_ids != N,
        "claim_superintelligence": False,
        "paid_api_calls": 0,
        "spend_eur": 0.0,
    }
    assert report["second_round_cache_hits"] == N
    assert report["proof_checks_passed"] == report["proof_checks_total"]
    assert report["duplicate_result_ids"] is False
    assert report["unique_result_ids"] == N
    with open("fractal-fabric-scale.json", "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
