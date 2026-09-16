# CÉRÉBRON Ω — Checkpoint and Roadmap

## 1. Current checkpoint
Program state: structural decomposition phase transitioning toward externally measurable capability tests.

Repository: dmaillot95-ui/Maillot-David-
Branch: main

### Verified recent GitHub Actions runs
- Intelligence Core ablation 2000: run 35118980372 — completed success.
- Intelligence Core dynamics 2000: run 35119612394 — completed success.
- Intelligence Core external benchmark: run 35121165980 — completed success, but benchmark design was non-discriminative and therefore NOT evidence for CMIV ordering.
- Superintelligence Task Funnel 2000: run 35122089680 — completed success.
- Superintelligence Core Ablation 10-to-4: run 35122324731 — launched; result must be checked before any claim about the minimal subset.

### Structural results to preserve as hypotheses
1. Recurring factors across internal funnels:
   verification, failure learning, transfer/representation reuse, policy selection, metacognition, contradiction detection, self-improvement.
2. Candidate 10-mechanism set:
   semantic compression, deduction, procedure refinement, system identification, result fusion, representation reuse, independence check, confidence estimation, failure learning, verification.
3. Dynamic hypothesis:
   contradiction detection → metacognition → self-improvement → verification → contradiction detection,
   with verification → metacognition feedback.
4. Do NOT treat the dynamic hypothesis as validated: the first external benchmark failed to discriminate orders.

## 2. Current unresolved question
What is the smallest executable subset of mechanisms that preserves all six required functions:
- verification
- learning
- transfer
- reasoning
- world model
- self-improvement
and still improves performance on held-out external tasks under resource control?

## 3. Immediate next sequence
P0 — Check run 35122324731 and extract the minimal structural subset. Do not overclaim.
P1 — Build benchmark V2 where all modules act meaningfully regardless of order.
P2 — Convert every surviving mechanism into executable operators with explicit state I/O.
P3 — Create hidden task families and adversarial corruption sets.
P4 — Compare full graph, minimal graph, random-order controls, compute-only controls, memory-only controls.
P5 — Run repeated seeded evaluations and compute confidence intervals.
P6 — Measure zero-shot transfer to unseen task families.
P7 — Add a failure-feedback episode and measure real improvement on later unseen instances.
P8 — Test whether the improved procedure transfers to a second domain without architecture retuning.
P9 — External or independent replication.

## 4. Required data model for each experiment
experiment_id
commit_sha
workflow_run_id
architecture_id
mechanisms
order/graph
seed
task_family
split
resource_budget
model_calls
tokens
cpu_time
gpu_time
memory
cost
raw_outputs
correctness
calibration
transfer_score
failure_before
failure_after
ablation_parent
artifact_digest
claim_level
notes

## 5. Stop conditions / Red Team
Reject a claimed capability improvement if:
- advantage vanishes under equal compute;
- advantage vanishes on hidden tasks;
- performance depends on task-family-specific hand rules;
- architecture was tuned on test data;
- self-improvement is only added memory or retries;
- multiple workers are counted as independent when using the same method/data;
- verification checks its own outputs without an independent criterion;
- transfer requires manual retuning;
- improvement is not reproducible across seeds.

## 6. Superintelligence threshold — operational definition
Do NOT use the label based on a benchmark maximum.
A future strong claim would require reproducible evidence that the system:
1. outperforms strong baselines across heterogeneous unseen domains;
2. transfers learned abstractions without manual retuning;
3. identifies and repairs its own failure modes;
4. improves its procedure and retains that improvement on later unseen tasks;
5. remains calibrated about uncertainty;
6. provides independently checkable evidence;
7. shows capability gains not explained by extra compute, memory, data, or worker count;
8. sustains these gains over repeated external evaluations.

## 7. Resume command
When continuing in a new session, resume from:
CHECKPOINT CEREBRON-SI-05 — MINIMAL CORE → EXECUTABLE OPERATORS → EXTERNAL BENCHMARK V2.

First action: inspect GitHub run 35122324731. If complete, read its artifact and record the actual minimal subset. Then build benchmark V2 without positional verification artifacts.

## 8. Absolute final rule
CÉRÉBRON Ω is a research program for discovering and validating general capability architecture. Until external evidence supports stronger claims, describe it as such — never as an achieved superintelligence.
