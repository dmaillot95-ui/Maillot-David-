# CEREBRON OMEGA — COLLATZ C176-C185 AGENT MISSION

Checkpoint: after C166-C175 audit.

STRICT RULES:
- CLAIM <= EVIDENCE.
- COMPUTATION != PROOF.
- FINITE TEST != UNIVERSAL PROOF.
- Do not declare Collatz solved or CYCLES CLOSED without a contradiction for arbitrary N.
- External agent agreement is not proof.

ESTABLISHED INPUTS FOR THIS MISSION:
1. Accelerated odd Collatz map T(x)=(3x+1)/2^{v2(3x+1)}.
2. Runs have form 1^r b with b>=2 and run-start y satisfies v2(y+1)=r+1.
3. A finite exact valuation/run word W of total valuation cost V(W)=sum(r_i+b_i) fixes at most one odd 2-adic cylinder/residue class modulo 2^{V(W)+1}; relative density among odd residues is 2^{-V(W)}.
4. Minimal excursion word for I_X=[X,2X): starts at y_0 in I_X, first transition exits I_X, intermediate run-starts stay outside I_X, final transition is the FIRST reentry to I_X.
5. Symbolically, minimal first-reentry words are prefix-free: if a completed first-reentry word were a strict prefix of another, the longer word would already have reentered before its declared first reentry.
6. Therefore the corresponding exact valuation cylinders are pairwise disjoint and the basic Kraft inequality gives only sum_W 2^{-V(W)} <= 1. This DOES NOT by itself give a uniform strict gap q<1.
7. For starts whose INITIAL terminal valuation satisfies 2<=b_0<=B, the union of all possible first-symbol cylinders has relative 2-adic mass at most
   q_B = sum_{r>=0} sum_{b=2}^B 2^{-(r+b)} = 1-2^{1-B} < 1.
   Hence the minimal excursion family with initial b_0<=B has Kraft mass <= q_B. For B growing, q_B -> 1.
8. Long-valuation starts in [X,2X) obey previously derived deterministic count L_B(X) <= X*2^{-B}+O((log X)^2).
9. Choosing B(X)=c log_2 log X gives L_B(X)=O(X/(log X)^c)+polylog(X)=o(X), while q_B=1-O((log X)^{-c}). This tradeoff may be more useful than B~gamma log X.
10. The unresolved issue is converting weighted cylinder mass into a sharp count of actual short-b exits/excursions in a finite band without losing control through the per-word +1 term / word multiplicity.

PRIMARY TARGET:
Derive the strongest rigorous bound possible on the number E_B(X) of short-b exits or minimal first-return excursions from I_X by combining:
- prefix-free/disjoint 2-adic cylinders;
- q_B=1-2^{1-B};
- B(X) optimized, especially c log_2 log X;
- exact finite-interval counting;
- depth/cost truncation;
- entropy of excursion words;
- renewal/transfer-operator if rigorously constructed.

PARALLEL QUESTIONS:
A. Prove the finite-word cylinder lemma carefully, including the exact modulus and measure.
B. Prove the prefix-free => disjoint-cylinder Kraft bound rigorously, and identify whether any stronger strict gap follows from first-reentry itself.
C. Optimize B(X): constant, log log X, sqrt(log X), log X. Balance long-valuation count against Kraft gap.
D. Eliminate or control the +1 per cylinder in finite interval counts. Try grouping by V, truncating V<=K and V>K, or using exact spacing of residue classes.
E. Bound N_V(X)=#{minimal excursion words W realizable from [X,2X): V(W)=V}. Determine whether N_V(X)<=C rho^V with rho<2, or a weaker bound sufficient for E_B(X)=o(X).
F. Construct a valid renewal/generating function F_X(s)=sum_W s^{V(W)} or transfer operator only if all states/transitions are explicitly defined; do not assume spectral radius <1.
G. FALSIFY: attempt formal/pseudo-orbit families showing q_B is sharp or showing E_B(X) can remain linear under local constraints. Distinguish pseudo-orbits from true cyclic realizability.
H. Determine whether B(X)=c log log X plus a nonuniform q_B gap can still yield a sublinear exit count after optimized depth K(X).

OUTPUT EXACTLY:
- CLAIMS VERIFIED
- NEW LEMMAS + proofs
- COUNTEREXAMPLES
- exact dependence on X,B,V,length
- best bound for E_B(X)
- consequence for |B_h| and delta upper bound
- circularities/invalid prior claims
- MEILLEUR GAIN
- RESIDUAL
- NEXTLOCK UNIQUE
- verdict CYCLES OPEN / CYCLES CLOSED

Default verdict is CYCLES OPEN unless arbitrary-N contradiction is genuinely proved.
