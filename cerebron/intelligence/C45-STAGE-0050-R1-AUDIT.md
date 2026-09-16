# C45 — STAGE 0050-R1 — AUDIT

Run: 35134780452
Artifact: 10462942474
Result SHA256: bbb3b3339ab525f29813dde264acc20705d7807248f8e8cb83a461b125629f24
Evidence ceiling: E3 synthetic verified simulation
Baseline: frozen C43/C44 pre-campaign baseline

## Frozen result

- Candidate mean residual: 1.6011311929547578
- Baseline mean residual: 5.9256436282255285
- Candidate mean verified: 16.93888888888889
- Baseline mean verified: 10.043915343915344
- Candidate mean cost: 26.373280423280423
- Exact-cost sham mean cost: 26.373280423280423
- Candidate VCGC: 0.6422747903064616
- Baseline VCGC: 0.44573099369503477
- Exact-cost sham VCGC: 0.46117198427523215
- Candidate vs baseline both-metric seed wins: 9/9
- Candidate vs exact-cost sham residual seed wins: 9/9
- Candidate vs exact-cost sham verified-output seed wins: 9/9
- Maximum candidate/sham cost mismatch: 0.0
- Family robustness gate: PASS
- Positive ablation signals: 4
- R50-R1 gate: PASS

## Mechanism decisions

KEEP: adaptive_campaign_compiler — strong positive ablation signal.
KEEP: verification_reservation — strong positive ablation signal.
KEEP: batch_sequence_router — positive ablation signal.
KEEP/NARROW: scar_guard — small but positive effect after redesign.
REMOVE FROM CORE: conservative_simple — its ablation slightly improves residual and VCGC, so SIMPLE-FIRST is not justified as a core execution mechanism in this benchmark. It may remain a hypothesis or optional routing heuristic pending independent evidence.

## Decision

Rung 50 repair is closed. Progression to rung 100 is authorized under the same fixed-baseline campaign.

This is evidence about a hand-designed synthetic campaign-control system only. It does not establish AGI or superintelligence.
