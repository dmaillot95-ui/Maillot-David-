# C45 — RUNG 125 — AUDIT

Status: PASS

Run: 35139356956
Artifact: 10464423288
Artifact digest: sha256:d0bdc52e4e22837bc0f673d18471092f1d2a2ccf91bd22071589b8e77eed3292

## Frozen protocol

- 125 units
- 11 seeds
- 10 stress families
- arms: frozen baseline / candidate_125 / matched_sham
- candidate and sham receive identical per-task unit, coordination and verification budgets
- claim ceiling: synthetic deterministic benchmark only

## Results

Baseline:
- residual: 1.3042683028
- verified_work: 0.9022631158
- VCGC: 0.6096372404

Candidate 125:
- residual: 0.0885988344
- verified_work: 1.4526300674
- VCGC: 0.9815068023

Matched sham:
- residual: 0.5717241360
- verified_work: 1.2398645834
- VCGC: 0.8377463401

Wins:
- candidate vs baseline: 11/11 seeds
- candidate vs sham: 11/11 seeds
- family non-regression: 10/10
- resource parity: PASS

Global gate: PASS

## Interpretation

125 is a validated operating point inside this synthetic deterministic harness. It is not evidence that 125 complex LLM messages have been executed, and it does not establish AGI or superintelligence. It does justify using 125 as the current tested batch size before probing 200 under the same baseline and evidence rules.

Next command: SUITE -> rung 200.
