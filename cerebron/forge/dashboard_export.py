#!/usr/bin/env python3
"""Export a read-only CEREBRON FORGE snapshot for dashboards such as Floot.

This module never submits work and never calls a paid API. It only reads the
local Forge database and emits a compact JSON status document.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from cerebron.forge.core import connect, status


def build_snapshot(db_path: str) -> dict:
    db = connect(db_path)
    snapshot = status(db)
    snapshot.update({
        "schema": "cerebron-forge-dashboard-v1",
        "read_only": True,
        "compute_provider": False,
        "spend_limit_eur": 0,
        "paid_fallback": False,
    })
    return snapshot


def main() -> None:
    db_path = os.getenv("CEREBRON_FORGE_DB", "out/cerebron-forge.db")
    out_path = Path(os.getenv("CEREBRON_DASHBOARD_OUT", "out/cerebron-dashboard.json"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot = build_snapshot(db_path)
    out_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(snapshot, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
