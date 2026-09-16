#!/usr/bin/env python3
import hashlib, json, time
from concurrent.futures import ThreadPoolExecutor

TASKS = [
    {"id": f"t{i}", "value": i, "op": "square" if i % 2 == 0 else "sha256"}
    for i in range(1, 33)
]

CACHE = {}

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
        "op": task["op"],
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
        ok = out["result"] == expected
    else:
        expected = hashlib.sha256(str(task["value"]).encode()).hexdigest()
        ok = out["result"] == expected
    return {"task_id": task["id"], "ok": ok}

def run_round(tasks):
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(micro_worker, tasks))
    audits = [red_team(t, r) for t, r in zip(tasks, results)]
    return results, audits

def main():
    first, audits1 = run_round(TASKS)
    second, audits2 = run_round(TASKS)
    report = {
        "schema": "cerebron-fractal-fabric-test-v1",
        "physical_nodes": 1,
        "active_processes": 1,
        "thread_workers_max": 8,
        "logical_micro_workers": len(TASKS),
        "coalitions": 2,
        "tasks": len(TASKS),
        "first_round_cache_hits": sum(r["cache_hit"] for r in first),
        "second_round_cache_hits": sum(r["cache_hit"] for r in second),
        "proof_checks_passed": sum(a["ok"] for a in audits1 + audits2),
        "proof_checks_total": len(audits1) + len(audits2),
        "duplicate_result_ids": len({r["task_id"] for r in first}) != len(first),
        "claim_superintelligence": False,
        "paid_api_calls": 0,
        "spend_eur": 0.0,
    }
    assert report["second_round_cache_hits"] == len(TASKS)
    assert report["proof_checks_passed"] == report["proof_checks_total"]
    assert report["duplicate_result_ids"] is False
    print(json.dumps(report, indent=2))
    with open("fractal-fabric-test.json", "w") as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    main()
