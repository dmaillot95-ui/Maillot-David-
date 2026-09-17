# CEREBRON OMEGA — COLLATZ C196-C205
## STATE-AWARE SPECTRAL DEFICIT / FORBIDDEN-TRANSITION LOCK

CHECKPOINT: after C186-C195.

VERIFIED INPUTS:
- accelerated odd Collatz T(x)=(3x+1)/2^a, a=v2(3x+1)>=1.
- run symbols are (r,b) with r>=0, b>=2 and exact symbol weight 2^{-(r+b)}.
- full scalar Kraft mass is exactly sum_{r>=0,b>=2}2^{-(r+b)}=1.
- therefore any scalar renewal operator that forgets state is critical and cannot give strict contraction merely from total 2-adic mass.
- small 2-adic mass alone does not imply sparse integer points in [X,2X).
- CYCLES OPEN.

MISSION:
Do NOT claim Collatz solved. Attack only the next lock:

Can a minimal STATE-AWARE first-return operator have spectral radius <1 because some symbol/state transitions are arithmetically or dynamically forbidden?

Candidate state components (use the minimum sufficient subset):
1. dyadic band offset / log-height class;
2. sign of multiplicative drift lambda-1;
3. low 2-adic residue class;
4. run-start congruence v2(y+1)=r+1;
5. first-return status (inside/outside target band);
6. previous symbol if truly necessary.

TASKS:
A. Define a finite or countable transfer matrix/operator M with exact branch weights, without inventing probabilities.
B. Prove which transitions are truly impossible; do not use heuristic rarity.
C. Quantify lost row mass or a Doeblin/spectral deficit if any.
D. Determine whether rho(M)<1, rho(M)=1, or UNKNOWN.
E. If finite-state truncations are used, prove truncation error and monotone control.
F. Search for strongly connected critical subgraphs of total weight 1; if one exists, produce it as a no-go/counterexample.
G. Separate Haar-mass contraction from finite-interval point counting.
H. Seek any nonrecyclable invariant/resource only if rigorously defined.

OUTPUT EXACTLY:
CLAIMS VERIFIED;
NEW LEMMAS + proofs;
FORBIDDEN TRANSITIONS proved;
STATE DEFINITION;
OPERATOR / MATRIX;
ROW-MASS BOUNDS;
SPECTRAL-RADIUS BOUND;
COUNTEREXAMPLES;
FINITE-INTERVAL CONSEQUENCE (if any);
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
