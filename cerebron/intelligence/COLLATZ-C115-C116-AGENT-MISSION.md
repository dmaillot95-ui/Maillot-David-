# CÉRÉBRON Ω — COLLATZ C115/C116 AGENT MISSION

Status: ACTIVE
Date: 2026-09-17

## Absolute rules
CLAIM <= EVIDENCE
COMPUTATION != PROOF
FINITE TEST != UNIVERSAL PROOF
CONSENSUS != TRUTH
EQUIVALENT REFORMULATION != NEW OBSTRUCTION
ABSENCE OF NONTRIVIAL CYCLES != FULL COLLATZ

Do not claim Collatz solved. N arbitrary remains open.

## Hypothetical cycle framework
Accelerated Collatz on positive odd integers:
T(x_i)=(3x_i+1)/2^{a_i}, a_i=v2(3x_i+1)>=1.
For a hypothetical cycle of N odd terms:
A=sum a_i, D=2^A-3^N, m=min x_i, delta=A ln2-N ln3>0.
Verified identity:
delta=sum_i ln(1+1/(3x_i)).

## Current best run compression
Decompose valuation word into maximal runs 1^{r_j} b_j with b_j>=2. Let y_j be the start of run j and z_j its last odd before the terminal descent. Then
z_j+1=(3/2)^{r_j}(y_j+1),
y_{j+1}=(3 z_j+1)/2^{b_j},
and therefore
y_{j+1}=3^{r_j+1}/2^{r_j+b_j}*(y_j+1)-2^{1-b_j}.
Also verified:
delta < sum_j 1/y_j.

## Dyadic packing target
For X=2^h m define
B_h={j: X<=y_j<2X}.
Then
delta < (1/m) sum_{h>=0} |B_h|/2^h.
It is enough to prove a universal bound |B_h| <= C 2^{(1-eps)h} for some eps>0 and controlled C; polynomial is stronger than necessary.

## Known obstruction to naive valuation rarity
If y in [X,2X) is produced with terminal valuation b, its predecessor is
z=(2^b y-1)/3,
so z lies in an interval of length about 2^b X/3. Exact valuation imposes one class mod 2^{b+1}, but the interval expands by the same 2^b factor. Therefore valuation sparsity alone gives only O(X) candidates and is not a closing argument.

## Priority question
Prove, weaken, or refute a strong universal packing bound for
#{j: X<=y_j<2X}.
Exploit the coupled pair (r_j,b_j), cyclicity, distinctness, exact congruences, and global budgets. Do not use probabilistic valuation heuristics as proof.

## Parallel tasks
DECOMPOSER: isolate minimal lemmas needed for a subexponential-in-h packing bound.
PROOF_A: derive a rigorous deterministic bound using the exact run transition and same-band constraints.
PROOF_B: seek an independent arithmetic/congruence proof.
ALTERNATIVE_ROUTE: try transfer/operator/product/log-walk methods not equivalent to A/B.
FALSIFIER: construct formal or genuine counterexamples to |B_h|<=poly(h), clearly separating pseudo-orbits from true cycles.
RED_TEAM: attack hidden assumptions, especially same-band approximations and dependence on m,N,A.
COUNTER_AUDITOR: audit the Red Team and identify correlated errors.
REPLICATOR: independently rederive every claimed new lemma.
SYNTHESIZER: merge only supported claims and contradictions.
JUDGE: classify each claim PROVED / REFUTED / HOLD and state exact missing step.

## Required output
CLAIMS VERIFIED
NEW LEMMAS with proof
COUNTEREXAMPLES
BOUND on |B_h|
exact dependence on h,m,N,A
consequence for sum 1/x_i and delta
collision or no collision with a rigorous Diophantine lower bound
circularities
BEST GAIN
RESIDUAL
NEXTLOCK UNIQUE
verdict CYCLES CLOSED / CYCLES OPEN
