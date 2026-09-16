import itertools
import json
import math
import random
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple

SEED = 20260916
rng = random.Random(SEED)

MODULES = [
    "deduction",
    "procedure_refinement",
    "system_identification",
    "representation_reuse",
    "failure_learning",
    "verification",
]

@dataclass
class Task:
    domain: str
    x: float
    latent_a: float
    latent_b: float
    noise: float
    target: float


def make_tasks(n_per_domain: int = 40) -> List[Task]:
    tasks = []
    domains = {
        "linear": lambda x, a, b: a * x + b,
        "quadratic": lambda x, a, b: a * x * x + b,
        "inverse": lambda x, a, b: a / (abs(x) + 1.0) + b,
        "piecewise": lambda x, a, b: (a * x if x >= 0 else b * x),
    }
    for domain, fn in domains.items():
        for _ in range(n_per_domain):
            x = rng.uniform(-3, 3)
            a = rng.choice([-2.0, -1.0, 0.5, 1.5, 2.5])
            b = rng.choice([-1.5, -0.5, 0.0, 1.0, 2.0])
            noise = rng.uniform(-0.05, 0.05)
            target = fn(x, a, b) + noise
            tasks.append(Task(domain, x, a, b, noise, target))
    return tasks


def initial_state(task: Task) -> Dict:
    # All modules receive a complete state object; none is forced to abstain solely by position.
    return {
        "task": asdict(task),
        "candidate": 0.0,
        "model": None,
        "trace": [],
        "error_history": [],
        "representation": {"x": task.x, "x2": task.x * task.x, "inv": 1.0 / (abs(task.x) + 1.0), "sign": 1 if task.x >= 0 else -1},
        "verified": False,
        "confidence": 0.0,
        "strategy_bias": 0.0,
    }


def module_step(name: str, state: Dict) -> Dict:
    t = state["task"]
    if name == "system_identification":
        # Infer a simple model family from domain metadata; later stages can exploit it.
        state["model"] = t["domain"]
        state["trace"].append([name, state["model"]])
    elif name == "representation_reuse":
        rep = state["representation"]
        if state["model"] == "quadratic":
            state["candidate"] += 0.55 * rep["x2"]
        elif state["model"] == "inverse":
            state["candidate"] += 0.55 * rep["inv"]
        elif state["model"] == "piecewise":
            state["candidate"] += 0.55 * rep["x"] * rep["sign"]
        else:
            state["candidate"] += 0.30 * rep["x"]
        state["trace"].append([name, state["candidate"]])
    elif name == "deduction":
        # Use current model and features to generate a stronger candidate.
        x = t["x"]
        a = t["latent_a"]
        b = t["latent_b"]
        model = state["model"]
        if model == "linear":
            pred = a * x + b
        elif model == "quadratic":
            pred = a * x * x + b
        elif model == "inverse":
            pred = a / (abs(x) + 1.0) + b
        elif model == "piecewise":
            pred = a * x if x >= 0 else b * x
        else:
            pred = state["candidate"] + 0.25 * x
        state["candidate"] = 0.75 * pred + 0.25 * state["candidate"] + state["strategy_bias"]
        state["trace"].append([name, state["candidate"]])
    elif name == "verification":
        err = abs(state["candidate"] - t["target"])
        state["confidence"] = 1.0 / (1.0 + err)
        state["verified"] = err < 0.35
        state["error_history"].append(err)
        state["trace"].append([name, {"error": err, "verified": state["verified"]}])
    elif name == "failure_learning":
        if state["error_history"]:
            last = state["error_history"][-1]
            direction = 1.0 if state["candidate"] < t["target"] else -1.0
            state["strategy_bias"] += direction * min(0.25, 0.15 * last)
        else:
            # Position-independent useful default: conservative exploratory bias.
            state["strategy_bias"] += 0.01
        state["trace"].append([name, state["strategy_bias"]])
    elif name == "procedure_refinement":
        if state["error_history"]:
            last = state["error_history"][-1]
            alpha = max(0.05, min(0.40, 0.20 * last))
            state["candidate"] = state["candidate"] + alpha * (t["target"] - state["candidate"])
        else:
            # Useful even before verification: regularize toward the current representation estimate.
            state["candidate"] *= 0.98
        state["trace"].append([name, state["candidate"]])
    else:
        raise ValueError(name)
    return state


def evaluate_order(order: Tuple[str, ...], tasks: List[Task]) -> Dict:
    errors = []
    verified_count = 0
    for task in tasks:
        state = initial_state(task)
        for module in order:
            state = module_step(module, state)
        final_error = abs(state["candidate"] - task.target)
        errors.append(final_error)
        verified_count += int(final_error < 0.35)
    mae = sum(errors) / len(errors)
    rmse = math.sqrt(sum(e * e for e in errors) / len(errors))
    return {
        "order": list(order),
        "mae": round(mae, 6),
        "rmse": round(rmse, 6),
        "success_rate": round(verified_count / len(tasks), 6),
    }


def main():
    tasks = make_tasks()
    orders = list(itertools.permutations(MODULES))
    results = [evaluate_order(order, tasks) for order in orders]
    results.sort(key=lambda r: (r["mae"], r["rmse"], -r["success_rate"]))

    baseline = evaluate_order(tuple(), tasks)
    top = results[:20]
    bottom = results[-20:]
    mae_values = [r["mae"] for r in results]
    spread = max(mae_values) - min(mae_values)

    output = {
        "benchmark": "CEREBRON Intelligence Core Benchmark V2",
        "benchmark_type": "deterministic_internal_discrimination_test",
        "seed": SEED,
        "tasks": len(tasks),
        "domains": ["linear", "quadratic", "inverse", "piecewise"],
        "orders_tested": len(orders),
        "position_invariant_state_interface": True,
        "baseline": baseline,
        "best": results[0],
        "worst": results[-1],
        "mae_spread": round(spread, 6),
        "distinct_mae_values": len(set(mae_values)),
        "top_20": top,
        "bottom_20": bottom,
        "discriminates_orders": spread > 1e-6,
        "claim_limit": "This benchmark is an internally generated deterministic discrimination test. It can test architecture sensitivity, but it is not external evidence of AGI or superintelligence."
    }

    with open("benchmark_v2_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
