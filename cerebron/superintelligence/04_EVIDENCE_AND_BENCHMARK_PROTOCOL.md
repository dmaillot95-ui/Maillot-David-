# CÉRÉBRON Ω — Evidence and Benchmark Protocol

## 1. Scientific objective
Replace hand-designed structural scores with external, objective, reproducible tasks.

A claim of improved intelligence requires at least:
- equalized or accounted resources;
- held-out task families;
- exact or independently verifiable targets;
- repeated runs;
- ablation;
- transfer;
- adversarial corruption;
- calibration measurement.

## 2. Benchmark families
Use heterogeneous families so no single heuristic dominates:
- arithmetic / symbolic reasoning
- program synthesis and debugging
- theorem / proof checking
- causal inference
- system identification
- planning under constraints
- noisy pattern induction
- scientific hypothesis discrimination
- experiment design
- transfer between representational domains
- adversarial contradiction detection
- calibration / abstention
- continual learning without catastrophic loss

## 3. Split design
For every family create:
- development set
- hidden validation set
- held-out transfer set
- adversarial set

Never tune architecture on the final transfer/adversarial sets.

## 4. Metrics
Primary:
- exact-answer accuracy
- externally verified success rate
- transfer gain
- error-correction gain after feedback
- calibration error
- robustness under corruption
- capability retained after ablation

Efficiency:
- success per model call
- success per token
- success per CPU/GPU second
- success per euro/dollar where relevant
- latency

Generalization:
- in-family score
- out-of-family score
- zero-shot transfer score
- post-failure improvement score

## 5. Critical controls
Controls must include:
- baseline architecture without feedback loops
- same architecture with random module order
- same compute with fewer mechanisms
- more compute without architectural change
- memory-only expansion
- multi-worker expansion without independence

A real architectural gain should survive these controls.

## 6. Ablation protocol
For N mechanisms:
1. evaluate full graph;
2. remove one mechanism at a time;
3. test all small subsets when tractable;
4. measure interaction terms, not only individual importance;
5. repeat on held-out families;
6. retain only mechanisms whose contribution survives transfer.

## 7. Synergy test
For mechanisms A and B define:

Synergy(A,B) = C(A+B) - C(A) - C(B) + C(base).

Positive synergy must be replicated across seeds and task families before being treated as evidence of an emergent interaction.

## 8. Current benchmark lesson
The first external benchmark of the C/M/I/V order produced 16 orders with 240/240 and 8 orders with 0/240 abstention behavior. Root cause: verification emitted only if a candidate had already been selected. This created a positional artifact. Therefore that benchmark does not validate CMIV or any order. The benchmark must be redesigned so each module has meaningful state effects regardless of position and task difficulty separates architectures.

## 9. Evidence hierarchy
STRUCTURAL SCORE = hypothesis only.
DETERMINISTIC BENCHMARK = finite evidence.
HELD-OUT MULTI-FAMILY BENCHMARK = stronger finite evidence.
INDEPENDENT REPLICATION = stronger.
REAL-WORLD REPRESENTATIVE TASK = stronger.
SUSTAINED TRANSFER + SELF-IMPROVEMENT UNDER RESOURCE CONTROL = required before any strong superintelligence claim.
