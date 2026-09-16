#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
ROUTING = ROOT / "routing"
if str(ROUTING) not in sys.path:
    sys.path.insert(0, str(ROUTING))

from provider_router import load_state, save_state, record_result, snapshot


def read_results(root: Path) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(root.rglob("result-*.json")):
        try:
            rows.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception as exc:
            rows.append({"_parse_error": str(exc), "_path": str(path)})
    return rows


def reduce(rows: list[dict], runtime_path: Path) -> tuple[dict, dict]:
    state = load_state(runtime_path)
    statuses = Counter()
    providers = Counter()
    models = Counter()
    attempt_models = Counter()
    error_types = Counter()
    addresses: set[str] = set()
    external_successes = 0
    external_failures = 0
    quota_hits = 0
    parsed = 0

    for row in rows:
        if row.get("_parse_error"):
            statuses["PARSE_ERROR"] += 1
            continue
        parsed += 1
        if row.get("federated_address"):
            addresses.add(str(row["federated_address"]))
        for result in row.get("worker_results", []):
            status = str(result.get("execution_status") or "UNKNOWN")
            statuses[status] += 1
            provider = result.get("provider")
            model = result.get("model_id")
            if provider:
                providers[str(provider)] += 1
            if model:
                models[str(model)] += 1

            # Record every attempted external call. A provider can have both a
            # quota hit and a later success in the same task; both signals matter.
            attempts = result.get("attempted_models") or []
            if attempts:
                for attempt in attempts:
                    route = str(attempt.get("provider") or provider or "")
                    if not route:
                        continue
                    attempt_model = attempt.get("model_id")
                    if attempt_model:
                        attempt_models[str(attempt_model)] += 1
                    ok = bool(attempt.get("ok"))
                    err = attempt.get("error_type")
                    record_result(state, route, ok=ok, error_type=err)
                    if ok:
                        external_successes += 1
                    else:
                        external_failures += 1
                    if err:
                        error_types[str(err)] += 1
                    if err == "QUOTA":
                        quota_hits += 1
            elif provider:
                ok = bool(result.get("ok"))
                err = result.get("error_type")
                record_result(state, str(provider), ok=ok, error_type=err)
                external_successes += int(ok)
                external_failures += int(not ok)
                if err:
                    error_types[str(err)] += 1
                quota_hits += int(err == "QUOTA")

    available = [
        "groq_free",
        "cloudflare_workers_ai_free",
        "huggingface_public_spaces",
    ]
    route_snapshot = snapshot(state, available)
    summary = {
        "schema": "cerebron-federated-wave-summary-v1",
        "artifact_rows": len(rows),
        "parsed_rows": parsed,
        "unique_addresses": len(addresses),
        "statuses": dict(statuses),
        "successful_tasks": int(statuses.get("COMPLETED", 0)),
        "external_call_attempts": external_successes + external_failures,
        "successful_external_calls": external_successes,
        "failed_external_calls": external_failures,
        "quota_hits": quota_hits,
        "providers": dict(providers),
        "terminal_models": dict(models),
        "attempted_models": dict(attempt_models),
        "error_types": dict(error_types),
        "provider_order_next_wave": route_snapshot["ordered"],
        "provider_scores_next_wave": route_snapshot["scores"],
        "claim_note": "Logical shard count is not physical concurrency; external outputs remain unreviewed evidence until audited.",
    }
    return summary, state


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--artifacts", required=True)
    p.add_argument("--runtime", default=str(ROOT / "state" / "provider-runtime.json"))
    p.add_argument("--summary", default=str(ROOT / "state" / "wave-summary-latest.json"))
    args = p.parse_args()

    rows = read_results(Path(args.artifacts))
    summary, state = reduce(rows, Path(args.runtime))
    save_state(Path(args.runtime), state)
    out = Path(args.summary)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
