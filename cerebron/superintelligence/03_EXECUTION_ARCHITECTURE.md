# CÉRÉBRON Ω — Execution Architecture

## 1. Principle
The system must separate proposal, execution, verification, audit, memory, and decision. No component may mark its own unverified output as evidence.

## 2. Canonical execution cycle
1. OBSERVE — ingest task, constraints, evidence, unknowns.
2. DECOMPOSE — split into measurable subproblems.
3. MODEL — build explicit hypotheses / representations.
4. PROPOSE — generate candidate solutions, proofs, experiments, or strategies.
5. CONTRADICT — search for internal conflicts and counterexamples.
6. VERIFY — independently check calculations, logic, code, sources, and predictions.
7. CALIBRATE — estimate uncertainty and identify unsupported claims.
8. IMPROVE — modify the strategy, representation, or procedure based on failures.
9. TRANSFER — reuse validated structure on a different task family.
10. COMMIT — write only validated results to persistent evidence memory.

Loop:
VERIFY → CONTRADICT → MODEL/IMPROVE → VERIFY.

## 3. Roles are functions, not fake agents
Logical functions:
- Research
- Analysis
- Invention
- Audit / Counter-audit
- Synthesis / Memory
- Coordinator

A function can be implemented by one model, multiple real model calls, deterministic code, or human review. Do not call these 'agents' unless actual external model instances are executed.

## 4. Evidence stores
Maintain independent banks:
- Source Bank
- Data Bank
- Formula Bank
- Model Bank
- Simulation Bank
- Unknown Bank U1→U5
- Contradiction Bank
- Failure Bank
- Test Bank
- Evidence Bank
- Capability Bank
- Transfer Bank
- Ablation Bank

Every entry needs: ID, provenance, date, method, assumptions, status, reproducibility information, and links to artifacts/runs where applicable.

## 5. Capability maturity scale
E0 idea
E1 architecture
E2 calculation
E3 verified simulation
E4 controlled benchmark / HIL-like test
E5 integrated subsystem
E6 demonstrator
E7 representative external evaluation
E8 sustained operational history

CLAIM <= EVIDENCE. A capability at E3 must never be described as E7/E8.

## 6. Multi-worker execution
Parallelism is useful only when it increases independence or coverage.
Workers should be assigned to different evidence paths, e.g.:
- independent derivations;
- counterexample search;
- formal verification;
- benchmark design;
- ablation;
- transfer evaluation;
- adversarial testing.

Do not count multiple workers using identical data/methods as independent evidence.

## 7. Resource accounting
For every run log:
- model/provider/version if any;
- number of model calls;
- tokens if available;
- CPU/GPU time;
- wall time;
- memory;
- external data used;
- cost;
- task count;
- accuracy / calibration / transfer metrics.

The central test is capability efficiency, not raw scale.
