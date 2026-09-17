# CÉRÉBRON Ω — COLLATZ C166–C175
## MINIMAL EXCURSION WORD KRAFT LEMMA

Checkpoint inherited from C165.

Do not restart prior branches. Do not claim Collatz solved. CLAIM <= EVIDENCE.

We work with the accelerated Collatz map on positive odd integers:
T(x)=(3x+1)/2^{v2(3x+1)}.

Run decomposition: 1^r b, b>=2. For a run-start y:
v2(y+1)=r+1.
For fixed (r,b), y lies in a unique residue class modulo 2^{r+b+1}.
For a word W=((r0,b0),...,(r_{l-1},b_{l-1})), define V(W)=sum_i(r_i+b_i). A fixed word determines the start in a unique class modulo 2^{V(W)+1}.

For a dyadic band I_X=[X,2X), define a minimal excursion word W as follows:
- start y0 in I_X;
- first transition exits I_X;
- intermediate run-starts stay outside I_X;
- final transition is the first reentry into I_X.

Current target:
prove or refute a uniform Kraft contraction
SUM_{W in E_X} 2^{-V(W)} <= q_exc < 1
with q_exc independent of X,
or derive the strongest rigorously provable substitute.

Important established facts:
- same-band short-b words have a strict Kraft contraction (<3/4 in the relaxed bound used earlier);
- long valuations can be controlled separately by residue-class counting when B(X)~gamma log2 X;
- raw log-height is recyclable and not a valid non-recyclable excursion budget;
- exit count equals reentry count in a cycle, but this alone gives no sublinear bound.

Required attacks:
A. prove prefix-freeness or identify exactly why minimal excursion words are not prefix-free under the 2-adic coding;
B. derive exact cylinder disjointness conditions modulo 2^{V(W)+1};
C. count excursion words by total cost V and test whether their entropy base is <2;
D. separate high-exit and low-exit minimal words;
E. attack the claim with explicit formal words/pseudo-orbits and distinguish true-cycle constraints;
F. seek a transfer-operator/renewal generating function whose spectral radius <1 would imply the Kraft bound;
G. determine whether first-reentry minimality creates a genuine coding advantage absent for arbitrary outside words;
H. if uniform q_exc<1 is false, produce the best valid growth bound for the Kraft mass as a function of X or excursion depth.

Reject probability heuristics as proof.
Reject finite search as universal proof.
Reject any claim of CYCLES CLOSED unless arbitrary N is actually covered.

Return:
CLAIMS VERIFIED
NEW LEMMAS with proof
COUNTEREXAMPLES
KRAFT MASS BOUND
DEPENDENCE on X,V,length,B
CIRCULARITIES
MEILLEUR GAIN
RESIDUAL
NEXTLOCK UNIQUE
VERDICT CYCLES CLOSED / CYCLES OPEN
