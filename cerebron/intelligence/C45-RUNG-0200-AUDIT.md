# C45 — RUNG 0200 — AUDIT

Status: PASS
Evidence ceiling: E3 verified synthetic deterministic benchmark
Run: 35140017885
Artifact: 10464766732
Artifact digest: sha256:750af3b22c38e70b5f401abb31a45c41e7bf0899442cd1a7b5ad7ef96c352180

## Frozen protocol

Same frozen C45 baseline, same seeds, families, scoring rules and gates as rung 125; UNITS changed from 125 to 200. Candidate and matched sham receive identical per-task budgets.

## Results

- Units: 200
- Seeds: 11
- Families: 10
- Baseline residual: 1.292650118705297
- Candidate residual: 0.08542482958829535
- Matched-sham residual: 0.5630719297393548
- Baseline verified work: 0.9104761061414743
- Candidate verified work: 1.4571024132518917
- Matched-sham verified work: 1.246679059054058
- Baseline VCGC: 0.6151865582036988
- Candidate VCGC: 0.9845286576026295
- Matched-sham VCGC: 0.8423507155770662
- Candidate vs baseline: 11/11 seeds
- Candidate vs matched sham: 11/11 seeds
- Family non-regression: 10/10
- Resource parity: PASS
- Global gate: PASS

## Comparison with rung 125

Rung 125 also passed 11/11 vs baseline, 11/11 vs sham, 10/10 family non-regression and resource parity. Rung 200 therefore shows no synthetic degradation at this scale under the same harness.

## Critical limitation

This benchmark executes 200 deterministic synthetic work units. It does NOT execute 200 real LLM messages and does NOT model context-window pressure, model-call latency, semantic coordination loss, fusion loss, or true multi-agent reasoning overhead. Therefore it cannot establish that 200 complex ChatGPT-equivalent messages are better than 125.

## Decision

KEEP 125 and 200 as validated synthetic throughput points. Do not infer an optimal real-message frequency from this benchmark alone. The next meaningful experiment should be overhead-aware and calibrate work units against a real sequential baseline before using the term message-equivalent.
