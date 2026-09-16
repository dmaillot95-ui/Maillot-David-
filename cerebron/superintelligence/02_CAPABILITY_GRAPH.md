# CÉRÉBRON Ω — Capability Graph

## 1. Decomposition strategy
Treat superintelligence as a graph of measurable micro-capabilities, not as one monolithic property.

Primary families:
1. Perception / observation
2. Representation / abstraction
3. World-model construction
4. Reasoning / deduction / induction
5. Contradiction detection
6. Verification
7. Uncertainty estimation / calibration
8. Metacognition
9. Failure analysis
10. Learning from failure
11. Strategy / policy selection
12. Self-improvement / procedure refinement
13. Transfer / representation reuse
14. Memory / semantic compression
15. Experiment design
16. Causal inference
17. Search / planning
18. Coordination / result fusion
19. Independence checking
20. Discovery / invention

## 2. Current recurring factors from previous funnels
Recurring high-value factors observed in internal structural campaigns include:
- verification
- failure learning
- representation reuse
- policy selection
- self-correction
- robustness
- adaptation
- transfer
- metacognition
- contradiction detection
- self-improvement

Important: recurrence under a hand-designed score is only hypothesis generation.

## 3. Current 10-mechanism candidate graph
The latest structural funnel produced a candidate set:
- semantic compression
- deduction
- procedure refinement
- system identification
- result fusion
- representation reuse
- independence check
- confidence estimation
- failure learning
- verification

This set must be treated as provisional until external ablation and task execution validate it.

## 4. Dynamic loop hypothesis
Earlier order-search experiments suggested the loop:

CONTRADICTION DETECTION
→ METACOGNITION
→ SELF-IMPROVEMENT
→ VERIFICATION
→ CONTRADICTION DETECTION

with a second feedback:
VERIFICATION → METACOGNITION.

This order was NOT validated by the first external benchmark because that benchmark was structurally too easy and produced a binary artifact. Preserve it only as a hypothesis.

## 5. Minimal-core search
Search all subsets by ablation. Required functional coverage:
- verification
- learning
- transfer
- reasoning
- world model
- self-improvement

For every subset S:
- measure coverage;
- measure task accuracy;
- measure transfer to held-out families;
- measure calibration;
- measure robustness to corrupted inputs;
- measure improvement after failure;
- record resource use.

Select not the highest raw score, but the Pareto-efficient frontier of capability versus compute, memory, latency, and complexity.
