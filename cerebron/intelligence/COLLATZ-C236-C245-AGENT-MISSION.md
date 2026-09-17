# CEREBRON OMEGA — COLLATZ C236-C245
## BALANCED DISCREPANCY PROFILE FEASIBILITY

CHECKPOINT: after C226-C235.

VERIFIED INPUTS:
- For a valuation word a_0,...,a_{n-1}, A_k=sum_{i<k}a_i, Lambda_k=3^k/2^{A_k}, E_k=k ln3-A_k ln2.
- Exact affine prefix formula: 2^{A_k}x_k=3^k x_0+C_k, C_0=0, C_{k+1}=3C_k+2^{A_k}.
- For fixed word, every band/first-exit/stay-out/first-reentry condition is a linear inequality in x_0; the real start set is therefore an interval or empty after intersection.
- Every finite positive valuation word is locally realizable by infinitely many positive trajectories.
- Define alpha=log_2 3 and A_k=floor(k alpha+1/2). Then a_k=A_{k+1}-A_k is in {1,2} and E_k=ln2(k alpha-A_k) lies in [-ln2/2,ln2/2). Hence Lambda_k lies in [2^{-1/2},2^{1/2}) for arbitrarily long finite words. Therefore the discrepancy path need not escape every fixed critical strip.
- This local balanced-word construction does NOT yet prove first-exit/first-reentry feasibility in a fixed dyadic band, because affine offsets C_k and the real start interval may make the episode start set empty.
- CYCLES OPEN.

MISSION:
Determine whether the balanced/mechanical valuation words above (or nearby balanced words) can satisfy the exact first-exit/stay-out/first-reentry inequalities for arbitrarily long episodes with a nonempty integer start set in the required 2-adic cylinder. If yes, formalize the resulting no-go theorem for uniform archimedean profile barriers. If no, isolate the exact obstruction created by affine offsets and/or cylinder-versus-interval intersection.

MANDATORY 20-FUNCTION POLYMORPHIC TEAM:
THEORETICAL_MATHEMATICIAN, NUMBER_THEORIST, DYNAMICAL_SYSTEMS_SPECIALIST, COMBINATORICS_SPECIALIST, ERGODIC_SPECTRAL_SPECIALIST, P_ADIC_SPECIALIST, ARCHIMEDEAN_ANALYST, DIOPHANTINE_SPECIALIST, FORMAL_PROOF_AUDITOR, COUNTEREXAMPLE_HUNTER, COMPUTATIONAL_EXPERIMENTER, PROOF_SYNTHESIST, POLYMORPHIC_MATHEMATICIAN, CREATOR_A, CREATOR_B, VERIFIER, AUDITOR, COUNTER_AUDITOR, JUDGE, META_COORDINATOR.

TASKS:
A. Prove the balanced-word lemma rigorously using A_k=floor(k alpha+1/2).
B. For a fixed balanced word, derive exact C_k and all x_0 inequalities for one full band episode.
C. Show the real episode start set is one interval (possibly empty), and derive exact endpoints.
D. Intersect that interval with the unique exact valuation residue class modulo the correct power of 2; derive an exact integer-existence criterion.
E. Determine whether nonempty episode starts exist for arbitrarily large word lengths.
F. If yes, prove a no-go theorem: no uniform path-profile barrier based only on bounded E_k can close Collatz.
G. If no, isolate the first universally failing inequality and prove it.
H. Quantify the role of affine offsets C_k/2^{A_k}; do not drop them asymptotically without proof.
I. Distinguish local valuation-word realizability from realizability with the specified archimedean episode constraints.
J. Test nearby balanced sequences and phase shifts A_k=floor(k alpha+theta), theta in [0,1), without treating finite search as proof.
K. Seek a theorem on cylinder spacing versus interval width that forces existence or nonexistence uniformly.
L. CYCLES CLOSED only with an arbitrary-N contradiction.

OUTPUT:
CLAIMS VERIFIED;
BALANCED-WORD LEMMA;
EXACT AFFINE OFFSETS;
EPISODE START INTERVAL;
2-ADIC RESIDUE CLASS;
INTEGER-EXISTENCE CRITERION;
ARBITRARY-LENGTH FEASIBILITY OR OBSTRUCTION;
NO-GO THEOREM IF ANY;
FORMAL AUDIT;
MEILLEUR GAIN;
RESIDUAL;
NEXTLOCK UNIQUE;
VERDICT CYCLES CLOSED / CYCLES OPEN.

RULES:
REALITY > COHERENCE.
CLAIM <= EVIDENCE.
FINITE TEST != UNIVERSAL PROOF.
SIMULATION != TEST.
NO PROBABILISTIC VALUATION ASSUMPTION.
CONSENSUS != TRUTH.
