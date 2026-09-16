#!/usr/bin/env python3
"""Build an evidence-bounded memory packet from the persistent CEREBRON campaign.

This script does not pretend that COMPLETED means scientifically validated. It
indexes execution metadata, provenance references, recurring failure modes and
candidate records that can be reviewed by PROOF/REDTEAM/EVALUATOR workers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "federation" / "state" / "mission-queue.json"
LATEST = ROOT / "federation" / "state" / "latest-state.json"

REJECT_EVIDENCE = {"NO_EVIDENCE", "DETERMINISTIC_CHECK_REQUIRED"}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def inc(counter: Counter, value):
    counter[str(value if value is not None else "UNKNOWN")] += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="cerebron/civilization/memory")
    ap.add_argument("--sample", type=int, default=180)
    args = ap.parse_args()

    q = load(QUEUE)
    latest = load(LATEST)
    tasks = list(q.get("tasks", {}).values())

    by_status, by_evidence, by_role, by_model, by_civ = (Counter() for _ in range(5))
    failure_modes = Counter()
    role_success = defaultdict(lambda: Counter())
    candidates = []
    contradiction_candidates = []

    for t in tasks:
        status = t.get("status", "UNKNOWN")
        evidence = t.get("evidence_status", "UNREVIEWED")
        role = t.get("role", "UNKNOWN")
        model = t.get("model_family") or "UNKNOWN"
        civ = t.get("civilization_name") or t.get("civilization") or "UNKNOWN"
        inc(by_status, status); inc(by_evidence, evidence); inc(by_role, role); inc(by_model, model); inc(by_civ, civ)
        role_success[role][status] += 1

        if status in {"FAILED_RETRYABLE", "QUARANTINED", "REJECTED", "CANCELLED"}:
            reason = t.get("quarantine_reason") or status
            inc(failure_modes, reason)

        if status == "COMPLETED" and t.get("result_ref"):
            record = {
                "task_id": t.get("task_id"),
                "mission_id": t.get("mission_id"),
                "cycle": t.get("cycle"),
                "civilization": t.get("civilization"),
                "team": t.get("team"),
                "role": role,
                "model_family": model,
                "worker": t.get("worker"),
                "attempt": t.get("attempt", 0),
                "evidence_status": evidence,
                "result_ref": t.get("result_ref"),
            }
            raw = json.dumps(record, sort_keys=True, ensure_ascii=False).encode("utf-8")
            record["record_sha256"] = hashlib.sha256(raw).hexdigest()
            record["memory_status"] = "CANDIDATE_REQUIRES_REVIEW" if evidence == "UNREVIEWED" else (
                "CANDIDATE_WITH_EVIDENCE_LABEL" if evidence not in REJECT_EVIDENCE else "EXCLUDED_FROM_VALIDATED_MEMORY"
            )
            candidates.append(record)

        # These are routing candidates, not semantic contradictions: multiple
        # outcomes for the same role/cycle indicate where review is valuable.
    grouped = defaultdict(set)
    for t in tasks:
        key = (t.get("mission_id"), t.get("cycle"), t.get("role"))
        grouped[key].add(t.get("status", "UNKNOWN"))
    for (mid, cycle, role), statuses in grouped.items():
        if "COMPLETED" in statuses and any(s in statuses for s in ("FAILED_RETRYABLE", "QUARANTINED", "REJECTED")):
            contradiction_candidates.append({
                "mission_id": mid,
                "cycle": cycle,
                "role": role,
                "observed_statuses": sorted(statuses),
                "classification": "OUTCOME_DIVERGENCE_REVIEW_REQUIRED",
                "claim": "This is not a semantic contradiction; inspect underlying artifacts before drawing conclusions."
            })

    completed = by_status.get("COMPLETED", 0)
    total = len(tasks)
    summary = {
        "schema": "cerebron-campaign-memory-index-v1",
        "generated_at": now_iso(),
        "source_latest_state": latest,
        "tasks_total": total,
        "completed": completed,
        "completed_fraction": round(completed / total, 6) if total else 0,
        "status_counts": dict(by_status),
        "evidence_counts": dict(by_evidence),
        "role_counts": dict(by_role),
        "model_family_counts": dict(by_model),
        "civilization_counts": dict(by_civ),
        "failure_modes": dict(failure_modes.most_common()),
        "completed_with_result_ref": len(candidates),
        "outcome_divergence_groups": len(contradiction_candidates),
        "evidence_rule": "COMPLETED is execution success only. Integration into validated Strategy Memory requires artifact review plus PROOF/REDTEAM/EVALUATOR evidence.",
    }

    # Ranking is operational only: prioritize records with stronger evidence labels,
    # fewer attempts, then recent cycles. It is not a truth score.
    def rank_key(r):
        evid = 0 if r["memory_status"] == "CANDIDATE_WITH_EVIDENCE_LABEL" else 1
        return (evid, int(r.get("attempt") or 0), -int(r.get("cycle") or 0), str(r.get("task_id")))

    candidates_sorted = sorted(candidates, key=rank_key)
    sample = candidates_sorted[: max(1, args.sample)]

    role_table = []
    for role in sorted(role_success):
        c = role_success[role]
        n = sum(c.values())
        role_table.append({
            "role": role,
            "tasks": n,
            "completed": c.get("COMPLETED", 0),
            "completion_fraction": round(c.get("COMPLETED", 0) / n, 6) if n else 0,
            "failed_retryable": c.get("FAILED_RETRYABLE", 0),
            "quarantined": c.get("QUARANTINED", 0),
        })

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "campaign-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "strategy-candidates.json").write_text(json.dumps(sample, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "outcome-divergence.json").write_text(json.dumps(contradiction_candidates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "role-performance.json").write_text(json.dumps(role_table, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    packet = {
        "summary": summary,
        "role_performance": role_table,
        "top_failure_modes": failure_modes.most_common(20),
        "candidate_sample": sample[:60],
        "outcome_divergence_sample": contradiction_candidates[:60],
        "instructions": [
            "Use historical metadata to choose what to inspect/test next, not as proof of a scientific claim.",
            "Any candidate promoted to Strategy Memory must survive PROOF, REDTEAM and EVALUATOR gates.",
            "Resolve high-value outcome divergences before generating redundant ideas.",
            "Prefer measured role/model performance for routing; do not infer intelligence from task count."
        ]
    }
    (out / "memory-packet.json").write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
