# CEREBRON OMEGA — COLLATZ C156-C165
## SHORT-b BAND-EXCURSION COUNT

Checkpoint input: C155.

Verified prior reductions:
- delta < sum_j 1/y_j <= (1/m) sum_h |B_h|/2^h.
- same-band short-b words admit strict Kraft contraction.
- long defects satisfy L_B(X) <= X 2^{-B} + O((log X)^2).
- with B(X)~gamma log_2 X, long defects are sublinear.
- remaining principal term is E_B(X): number of short-b exits from [X,2X).
- exits = reentries on a finite cycle.

UNIQUE MISSION:
Derive a rigorous universal upper bound on the number of short-b excursions
[X,2X) -> outside -> [X,2X)
with exit valuation b <= B(X)~gamma log_2 X.

Required independent routes:
A. Excursion energy/cost: prove every exit consumes a quantitatively non-recyclable log-height or valuation budget.
B. Residue-word coding: encode exit-to-reentry words by exact 2-adic classes and compare word entropy to modulus growth.
C. Crossing multiplicity: bound repeated crossings of one dyadic boundary.
D. Short-b upward exits vs downward exits; treat separately.
E. Falsifier: construct formal words/pseudo-orbits with many exits; distinguish local formal realizability from true cyclic realizability.
F. Red Team: attack any claimed sublinear E_B(X) bound, especially hidden probabilistic assumptions or circular dependence on packing.
G. Counter-auditor: validate or reject Red Team objections.
H. Replicator: independently derive any candidate bound.
I. Synthesizer: retain only supported lemmas.
J. Judge: classify PROVED/REFUTED/HOLD and verdict CYCLES OPEN/CLOSED.

No probability of valuations as proof. No finite testing as universal proof. No claim of solved Collatz without universal contradiction.

Target sufficient condition:
E_B(X)=o(X log log X / log X).
Stronger acceptable: E_B(X)=O(X^theta), theta<1.
