#!/usr/bin/env python3
"""CÉRÉBRON Ω deterministic hierarchy reducer.

Consumes immutable shard JSONL outputs and builds evidence-aware packages at
team, civilization and federal levels. It does not perform inference and never
promotes an unsupported consensus. Semantic chief agents can be enabled later
only after these deterministic gates are validated.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HIERARCHY_PATH = ROOT / "hierarchy-v1.json"
STATE_PATH = ROOT / "state" / "hierarchy-state.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=False)
            f.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def read_rows(root: Path):
    rows = []
    for path in sorted(root.rglob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            row["_artifact_file"] = str(path)
            rows.append(row)
    return rows


def success(row) -> bool:
    return row.get("execution_status") == "COMPLETED" and bool(row.get("ok"))


def team_package(rows, required_roles, min_required, min_families):
    by_role = defaultdict(list)
    families = set()
    successful_rows = []
    for r in rows:
        by_role[str(r.get("role"))].append(r)
        if success(r):
            successful_rows.append(r)
            fam = r.get("model_family")
            if fam:
                families.add(str(fam))

    successful_required = [
        role for role in required_roles
        if any(success(r) for r in by_role.get(role, []))
    ]
    missing_required = [role for role in required_roles if role not in successful_required]
    enough_roles = len(successful_required) >= int(min_required)
    enough_families = len(families) >= int(min_families)
    ready = enough_roles and enough_families and not missing_required

    refs = []
    for r in rows:
        refs.append({
            "task_id": r.get("task_id"),
            "role": r.get("role"),
            "status": r.get("execution_status"),
            "ok": bool(r.get("ok")),
            "model_id": r.get("model_id"),
            "model_family": r.get("model_family"),
            "response_sha256": r.get("response_sha256"),
            "artifact_file": r.get("_artifact_file"),
        })

    return {
        "status": "READY" if ready else "WAITING",
        "successful_outputs": len(successful_rows),
        "required_roles": list(required_roles),
        "successful_required_roles": successful_required,
        "missing_required_roles": missing_required,
        "independent_model_families": sorted(families),
        "independent_family_count": len(families),
        "promotion_checks": {
            "all_required_roles_success": not missing_required,
            "minimum_required_roles_met": enough_roles,
            "minimum_independent_model_families_met": enough_families,
        },
        "result_refs": refs,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--results-dir", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--state", default=str(STATE_PATH))
    p.add_argument("--report", required=True)
    args = p.parse_args()

    cfg = load(HIERARCHY_PATH)
    l2 = next(x for x in cfg["levels"] if x["id"] == "L2_TEAM")
    l3 = next(x for x in cfg["levels"] if x["id"] == "L3_CIVILIZATION")
    l4 = next(x for x in cfg["levels"] if x["id"] == "L4_FEDERAL_COUNCIL")

    rows = read_rows(Path(args.results_dir))
    smoke_rows = [r for r in rows if str(r.get("task_id", "")).startswith("SMOKE-")]
    queue_rows = [r for r in rows if not str(r.get("task_id", "")).startswith("SMOKE-")]

    grouped = defaultdict(list)
    for r in queue_rows:
        key = (
            str(r.get("mission_id")),
            int(r.get("cycle") or 0),
            str(r.get("civilization")),
            int(r.get("team") or 0),
        )
        grouped[key].append(r)

    teams = {}
    civ_members = defaultdict(list)
    for (mission_id, cycle, civ, team), items in sorted(grouped.items()):
        key = f"{mission_id}:CYCLE-{cycle}:{civ}:TEAM-{team:02d}"
        pack = team_package(
            items,
            l2["required_roles"],
            l2["minimum_successful_required_roles"],
            l2["minimum_independent_model_families"],
        )
        pack.update({
            "mission_id": mission_id,
            "cycle": cycle,
            "civilization": civ,
            "team": team,
            "logical_chief_role": l2["logical_chief_role"],
        })
        teams[key] = pack
        civ_members[(mission_id, cycle, civ)].append(pack)

    civilizations = {}
    fed_members = defaultdict(list)
    for (mission_id, cycle, civ), packs in sorted(civ_members.items()):
        ready_teams = [x for x in packs if x["status"] == "READY"]
        families = sorted({
            fam for x in packs for fam in x.get("independent_model_families", [])
        })
        ready = (
            len(ready_teams) >= int(l3["minimum_ready_teams"])
            and len(families) >= int(l3["minimum_independent_model_families"])
        )
        key = f"{mission_id}:CYCLE-{cycle}:{civ}"
        pack = {
            "mission_id": mission_id,
            "cycle": cycle,
            "civilization": civ,
            "logical_chief_role": l3["logical_chief_role"],
            "status": "READY" if ready else "WAITING",
            "team_packages_seen": len(packs),
            "ready_teams": len(ready_teams),
            "required_ready_teams": int(l3["minimum_ready_teams"]),
            "independent_model_families": families,
            "independent_family_count": len(families),
            "promotion_checks": {
                "all_ten_teams_ready": len(ready_teams) >= int(l3["minimum_ready_teams"]),
                "minimum_independent_model_families_met": len(families) >= int(l3["minimum_independent_model_families"]),
            },
        }
        civilizations[key] = pack
        fed_members[(mission_id, cycle)].append(pack)

    federal = {}
    for (mission_id, cycle), packs in sorted(fed_members.items()):
        ready_civs = [x for x in packs if x["status"] == "READY"]
        ready = len(ready_civs) >= int(l4["minimum_ready_civilizations"])
        key = f"{mission_id}:CYCLE-{cycle}"
        federal[key] = {
            "mission_id": mission_id,
            "cycle": cycle,
            "logical_roles": l4["logical_roles"],
            "status": "READY" if ready else "WAITING",
            "civilization_packages_seen": len(packs),
            "ready_civilizations": len(ready_civs),
            "required_ready_civilizations": int(l4["minimum_ready_civilizations"]),
            "promotion_checks": {
                "all_twelve_civilizations_ready": ready,
            },
            "handoff_to_chatgpt": ready,
        }

    smoke = {
        "rows": len(smoke_rows),
        "successful_external_calls": sum(1 for r in smoke_rows if success(r)),
        "failed_external_calls": sum(1 for r in smoke_rows if not success(r)),
        "model_families": sorted({str(r.get("model_family")) for r in smoke_rows if r.get("model_family")}),
        "roles": sorted({str(r.get("role")) for r in smoke_rows if r.get("role")}),
        "promotion_attempted": False,
        "reason": "SMOKE outputs validate transport/routing only and are never promoted as mission evidence."
    }

    state = {
        "schema": "cerebron-hierarchy-state-v1",
        "run_id": str(args.run_id),
        "updated_at": now_iso(),
        "semantic_chief_agents_enabled": bool(cfg.get("semantic_chief_policy", {}).get("enabled", False)),
        "source_rows": len(rows),
        "queue_rows": len(queue_rows),
        "smoke": smoke,
        "teams": teams,
        "civilizations": civilizations,
        "federal": federal,
    }
    atomic_write(Path(args.state), state)

    report = {
        "schema": "cerebron-hierarchy-run-report-v1",
        "run_id": str(args.run_id),
        "at": now_iso(),
        "source_rows": len(rows),
        "smoke_rows": len(smoke_rows),
        "team_packages": len(teams),
        "ready_teams": sum(1 for x in teams.values() if x["status"] == "READY"),
        "civilization_packages": len(civilizations),
        "ready_civilizations": sum(1 for x in civilizations.values() if x["status"] == "READY"),
        "federal_packages": len(federal),
        "ready_federal_packages": sum(1 for x in federal.values() if x["status"] == "READY"),
        "handoff_to_chatgpt": any(x.get("handoff_to_chatgpt") for x in federal.values()),
        "semantic_chief_agents_enabled": state["semantic_chief_agents_enabled"],
    }
    atomic_write(Path(args.report), report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
