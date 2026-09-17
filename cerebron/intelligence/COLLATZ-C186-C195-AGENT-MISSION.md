# CEREBRON OMEGA — COLLATZ C186-C195 AGENT MISSION

CHECKPOINT: after C176-C185 audit.

VERDICT SO FAR: CYCLES OPEN.

ESTABLISHED:
- Minimal first-reentry words are prefix-free and their exact 2-adic cylinders are disjoint.
- Kraft controls weighted 2-adic mass, not finite-interval point count.
- For initial b<=B, first-symbol Kraft mass q_B <= 1-2^{1-B}.
- Long-valuation starts obey L_B(X) <= X 2^{-B}+O((log X)^2).
- Choosing B~c log_2 log X makes both the Kraft gap and long-valuation density scale on the same order 2^{-B}.

NEW AUDITED NO-GO TO TEST/USE:
A small total 2-adic cylinder mass does NOT by itself imply few integer points in [X,2X): arbitrarily deep disjoint cylinders can be centered on many prescribed finite integers while total Haar mass is arbitrarily small. Therefore weighted mass -> finite count needs an additional depth/entropy/dynamics mechanism.

PRIMARY LOCK:
JOINT RENEWAL / LONG-DEFECT BALANCE.
Do not try to prove E_B(X)=o(X) from one-step q_B alone.

Investigate sequences of repeated first-return excursions to I_X, integrating BOTH:
1. short-b excursion contraction;
2. long-b events inside the same renewal operator, rather than union-bounding them as separate defects.

Key issue: q-gap ~ 2^{-B} while long-b density ~2^{-B}. A crude k-step union bound cannot win, because obtaining q_B^k ~ X^{-eps} requires k 2^{-B} ≳ log X, while k L_B(X) then loses the same logarithmic factor.

TARGETS:
A. Prove/refute a joint transfer/renewal operator with spectral radius rho<1 uniformly or with quantified X-dependence.
B. Derive an exact generating function including all b>=2, not truncating long b as external errors.
C. Determine whether long-b symbols can increase or decrease the weighted spectral radius.
D. Seek a conserved/nonrecyclable resource per first-return episode.
E. Produce a rigorous no-go if every renewal/Kraft strategy collapses to radius 1.

STRICT OUTPUT:
CLAIMS VERIFIED; NEW LEMMAS with proofs; COUNTEREXAMPLES; exact dependence on X,B,V,k; best spectral/generating-function bound; consequence for E_B(X), |B_h| and delta; circularities; MEILLEUR GAIN; RESIDUAL; NEXTLOCK UNIQUE; verdict CYCLES CLOSED/CYCLES OPEN.

Do not declare CYCLES CLOSED without an arbitrary-N contradiction.