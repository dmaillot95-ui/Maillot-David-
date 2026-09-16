#!/usr/bin/env python3
import json, math, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent
CFG = ROOT / "cognitive_weights.json"
REQUIRED = {
    "verification", "contradiction_detection", "failure_learning", "transfer",
    "world_model", "reasoning", "self_improvement", "metacognition",
    "evidence", "uncertainty_penalty", "complexity_penalty", "compute_penalty"
}

def load():
    with CFG.open("r", encoding="utf-8") as f:
        return json.load(f)

def validate(cfg):
    errors = []
    weights = cfg.get("weights", {})
    missing = sorted(REQUIRED - set(weights))
    extra = sorted(set(weights) - REQUIRED)
    if missing: errors.append(f"missing weights: {missing}")
    if extra: errors.append(f"unexpected weights: {extra}")
    lo = float(cfg.get("constraints", {}).get("min_weight", 0.0))
    hi = float(cfg.get("constraints", {}).get("max_weight", 2.0))
    for k, v in weights.items():
        if not isinstance(v, (int, float)) or not math.isfinite(float(v)):
            errors.append(f"{k}: non-finite/non-numeric")
            continue
        if not lo <= float(v) <= hi:
            errors.append(f"{k}: {v} outside [{lo}, {hi}]")
    gates = cfg.get("acceptance_gates", {})
    mandatory = [
        "require_equal_resource_baseline", "require_heldout_gain",
        "require_transfer_gain", "require_ablation", "require_no_target_leakage",
        "require_no_material_regression", "require_reproducible_rerun"
    ]
    for g in mandatory:
        if gates.get(g) is not True:
            errors.append(f"acceptance gate disabled/missing: {g}")
    return errors

def main():
    cfg = load()
    errors = validate(cfg)
    report = {
        "profile_id": cfg.get("profile_id"),
        "status": cfg.get("status"),
        "valid": not errors,
        "errors": errors,
        "weight_count": len(cfg.get("weights", {})),
        "claim_limit": cfg.get("claim_limit")
    }
    out = ROOT / "weight_validation_report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if not errors else 1

if __name__ == "__main__":
    sys.exit(main())
