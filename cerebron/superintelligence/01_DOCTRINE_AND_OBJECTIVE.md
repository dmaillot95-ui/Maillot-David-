# CÉRÉBRON Ω — Superintelligence Research Program

## 1. Objective
CÉRÉBRON Ω is not to be labeled superintelligent by declaration. The program objective is to construct and verify an architecture whose measured capability gains cannot be explained solely by more compute, more memory, more agents, benchmark leakage, or hand-coded scoring.

Target principle:

CAPABILITY GAIN > COMPUTE-EXPLAINED GAIN

A candidate system must demonstrate: open-world generalization, transfer, self-correction, calibrated uncertainty, discovery, strategy improvement, and verification under fixed or explicitly accounted resources.

## 2. Absolute doctrine
- REALITY > COHERENCE
- EVIDENCE > CONFIDENCE
- CLAIM <= EVIDENCE
- VERIFY BEFORE COMMIT
- SIMULATION != TEST
- MEMORY != LEARNING
- TRAINING != CAPABILITY
- CONSENSUS != TRUTH
- AGENT COUNT != INTELLIGENCE
- A deterministic worker is not an AI agent.
- A simulated role is not an external agent.
- More compute is not evidence of more intelligence.
- A benchmark score is not general intelligence.

## 3. Core scientific question
Find the smallest executable graph of cognitive mechanisms such that, across heterogeneous unseen tasks, the graph produces reproducible capability improvement beyond what is explained by resource scaling.

Formal sketch:
Let A be an architecture, E an environment/task distribution, and R a resource vector. Define capability C(A,E,R).
The research target is not merely maximizing C, but finding transformations F such that:

C(F(A), E_new, R') - C(A, E_new, R) > G(R'-R)

where G estimates the gain attributable to added resources alone, and E_new includes held-out task families.

## 4. Falsification conditions
CÉRÉBRON Ω does not count as progress if gains disappear when:
- compute is equalized;
- memory is equalized;
- training data are isolated;
- task families change;
- prompt wording changes;
- evaluation is blinded;
- modules are ablated;
- repeated runs are seeded differently.

## 5. Current epistemic status
The current program has produced structural hypotheses, funnels, ablations, deterministic benchmarks and GitHub Actions executions. These are research instruments, not evidence of AGI or superintelligence. The next threshold is external task performance with reproducible gains under controlled resources.
