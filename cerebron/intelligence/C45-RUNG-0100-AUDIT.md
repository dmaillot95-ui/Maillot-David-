# C45 — RUNG 0100 — AUDIT

Status: PASS
Run: 35134957386
Artifact: 10462458660
Artifact ZIP SHA256: adac66be33e06daa707a7cc3d5c0ed709cdc375d5938b7f614d0356334755a4c
Result SHA256: 6e4c62f3fe26d8e0207b2136e05a5d71ebf5518abe5d85c521ad8de7d00c1a99
Evidence ceiling: E3 synthetic verified simulation
Baseline: frozen C43/C44 pre-campaign baseline

## Aggregate

Baseline:
- mean residual: 6.080417028623859
- mean cost: 22.997520661157026
- mean verified: 10.015840220385675
- VCGC proxy: 0.43554584070604857

Candidate:
- mean residual: 1.5912238959355498
- mean cost: 26.925895316804407
- mean verified: 16.844214876033057
- VCGC proxy: 0.6255580259175266

Exact-cost-accounting sham:
- mean residual: 5.232532980116165
- mean cost: 26.925895316804407
- mean verified: 11.995867768595042
- VCGC proxy: 0.4455366719555272

## Gates

- candidate vs baseline, both metrics: 11/11 seeds — PASS
- candidate vs sham residual: 11/11 — PASS
- candidate vs sham verified work: 11/11 — PASS
- family robustness: PASS
- maximum reported candidate/sham cost mismatch: 0.0
- positive ablation signals: 4/5
- overall rung-100 gate: PASS

All 12 stress families showed positive VCGC relative change versus baseline.

## Ablations

Positive contributors retained:
- scar_guard_high_confidence_only
- adaptive_campaign_compiler
- verification_reservation
- dependency_router

Observed deduplication did not earn its place:
- removing dedupe reduced residual by 0.11571252540213228
- removing dedupe increased VCGC by 0.00777390822413182

Decision: REMOVE observed_deduplication from the candidate core for rung 250 unless redesigned under a new preregistered hypothesis.

## Methodological caveat

The current `exact_cost_sham` has exact parity in the reported synthetic cost metric by overriding its cost field to the candidate target cost. Its internal randomized units/coordination/evidence-path choices are not constrained to consume the exact same physical/computational resources. Therefore this is accounting-level cost parity, not strict execution-level resource parity.

Rung 250 MUST replace this with resource-isomorphic controls: same actual unit budget, same verification budget, and same coordination allowance, with only allocation/routing strategy randomized. No claim of equal-compute superiority is permitted before that repair.

## Decision

Rung 100 is closed PASS under its preregistered synthetic gates. Progression to rung 250 is authorized.

This result supports only the claim that the candidate campaign-control policy performs better in this hand-designed synthetic benchmark. It is not evidence of AGI, superintelligence, or general real-world capability.
