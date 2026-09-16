# C45 OVERHEAD FRONTIER 001 — RESULT AUDIT

Status: CLOSED — VERIFIED SYNTHETIC RUN
Date: 2026-09-16
Evidence ceiling: E3 verified synthetic simulation

## Frozen preregistration

Preregistration commit: `d35ffb9cced30ffc959325ec1b794a879b4ee4f4`
Executable commit: `70b9a61438bdc7e9dfc5b5aed4699220add215a5`
Workflow commit: `8876339b6eaee95173307bd55b986316537f6fab`

Selection rule frozen before execution:

> Best operating point = scale with maximum mean `net_vcgc` among scales passing every gate.

Tested scales: 50, 75, 100, 125, 150, 175, 200, 225, 250, 300.

## Real execution evidence

GitHub Actions run: `35140496570`
Job: `104943506138`
Conclusion: SUCCESS
Runner: Ubuntu 24.04.5 / Python 3.12.14
Artifact: `cerebron-c45-overhead-frontier-001-results`
Artifact ID: `10465151919`
Artifact ZIP SHA256: `8f1033e13dacbbb69742f81badd5e43eb58029f2fa219fa4e14c5ff8ffe2d5cf`
Artifact uploaded bytes: 45,836

## Results

| Scale | residual | net_verified_work | net_vcgc | overhead_fraction | context_penalty | Gate |
|---:|---:|---:|---:|---:|---:|:---:|
| 50 | 0.082898 | 68.8530 | **0.853626** | 0.268530 | 0.00000 | PASS |
| 75 | 0.088335 | 102.4527 | 0.835161 | 0.278578 | 0.00000 | PASS |
| 100 | 0.085694 | 134.8933 | 0.815115 | 0.286965 | 0.00000 | PASS |
| 125 | 0.090297 | 169.4558 | 0.810616 | 0.294413 | 0.00175 | PASS |
| 150 | 0.106308 | 201.3086 | 0.794724 | 0.301241 | 0.00700 | PASS |
| 175 | 0.136956 | 232.0616 | 0.778083 | 0.307623 | 0.01575 | PASS |
| 200 | 0.175724 | 261.8660 | 0.761562 | 0.313661 | 0.02800 | PASS |
| 225 | 0.232485 | 287.7520 | 0.737615 | 0.319425 | 0.04375 | PASS |
| 250 | 0.288678 | 312.6662 | 0.715466 | 0.324959 | 0.06300 | PASS |
| 300 | 0.442207 | 352.2133 | 0.661179 | 0.335467 | 0.11200 | PASS |

Every scale achieved 13/13 candidate wins versus matched sham, 10/10 family non-regression, and resource parity.

## Decision

Under the preregistered selection rule, the best operating point is **50 work units**, with mean `net_vcgc = 0.8536261400364052`.

This does **not** mean 50 maximizes total work. `net_verified_work` continues rising through the largest tested scale, reaching 352.2133 at scale 300. Therefore two objectives must remain distinct:

- efficiency / verified gain per cognitive-cost proxy: best tested point = 50;
- total verified work produced: still rising at 300 in this model.

The 125-vs-200 comparison is therefore resolved under this synthetic overhead model: 125 is more efficient (`net_vcgc 0.810616` vs `0.761562`), while 200 produces more total net verified work (`261.8660` vs `169.4558`).

## Claim boundary

This benchmark is a deterministic synthetic overhead model. It does not measure actual LLM context limits, real multi-agent intelligence, or real GPT-message throughput. No claim of AGI or superintelligence follows.

## Next experimental lock

The next useful experiment is a Pareto frontier benchmark that explicitly separates two campaign modes:

1. EFFICIENCY MODE — maximize verified gain per controlled cost;
2. THROUGHPUT MODE — maximize total verified work subject to quality/error gates.

A later real-LLM calibration is required before translating these work-unit scales into message-equivalent productivity.
