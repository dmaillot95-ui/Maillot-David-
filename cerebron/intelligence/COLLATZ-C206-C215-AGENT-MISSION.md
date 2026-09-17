# CEREBRON OMEGA — COLLATZ C206-C215
## ARCHIMEDEAN-CONDITIONED FIRST-RETURN OPERATOR

CHECKPOINT: after C196-C205.

VERIFIED INPUTS:
- accelerated odd Collatz T(x)=(3x+1)/2^a, a=v2(3x+1)>=1.
- run symbols (r,b), r>=0, b>=2.
- every finite valuation word is locally realizable by infinitely many positive trajectories.
- therefore symbol-only transition graphs are complete and have no forbidden (r,b)->(r',b') edges.
- scalar/full-symbol Kraft mass is critical: sum 2^{-(r+b)}=1.
- symbol-only spectral contraction is NON-CLOSING.
- for a run start y in [X,2X), y' = lambda(y+1)-2^{1-b}, lambda=3^{r+1}/2^{r+b}.
- same-band condition is exact interval intersection:
  y in [X,2X) intersect [ (X+2^{1-b})/lambda -1, (2X+2^{1-b})/lambda -1 ).
- CYCLES OPEN.

MISSION:
Attack ONLY the archimedean-conditioned first-return lock.

Use normalized position u=y/X in [1,2). Determine whether adding exact interval geometry / first-exit / first-reentry constraints creates a genuine state-aware loss of admissible branches and a rigorous spectral or counting deficit.

TASKS:
A. Derive exact branch domains in u for each (r,b), keeping the finite-X correction term exactly.
B. Define the minimal transfer/first-return operator on u (or a rigorous finite/countable partition) with exact branch weights; no probabilistic assumptions.
C. Prove any branch/domain exclusions caused by interval geometry, not by local valuation congruences.
D. Determine whether the union of branch domains covers [1,2) with full critical mass or leaves a uniform/nonuniform gap.
E. For first-exit and first-reentry words, derive exact domain intersections and test whether a true contraction q<1 occurs.
F. If using partitions/truncations, prove monotone error control and do not infer universality from finite tests.
G. Try to construct critical recurrent subgraphs / interval subsystems as falsifiers.
H. Keep Haar-mass contraction separate from integer-point counting in [X,2X).
I. If no uniform spectral gap exists, identify the exact obstruction and next minimal missing state.

OUTPUT EXACTLY:
CLAIMS VERIFIED;
NEW LEMMAS + proofs;
EXACT BRANCH DOMAINS;
STATE DEFINITION;
OPERATOR;
DOMAIN-COVERAGE / LOST-MASS BOUNDS;
SPECTRAL OR FIRST-RETURN BOUND;
COUNTEREXAMPLES;
FINITE-INTERVAL CONSEQUENCE;
CIRCULARITIES;
MEILLEUR GAIN;
RESIDUAL;
NEXTLOCK UNIQUE;
VERDICT CYCLES CLOSED / CYCLES OPEN.

RULES:
CLAIM <= EVIDENCE.
COMPUTATION != PROOF.
FINITE TEST != UNIVERSAL PROOF.
NO PROBABILISTIC VALUATION ASSUMPTION.
NO CYCLES CLOSED without arbitrary-N contradiction.
