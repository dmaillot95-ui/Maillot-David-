# CÉRÉBRON Ω — COLLATZ C146–C155 AGENT MISSION

Checkpoint: C145. Full Collatz and arbitrary-cycle exclusion remain OPEN.

Verified inputs:
- Accelerated map T(x)=(3x+1)/2^{v2(3x+1)} on positive odds.
- Run block 1^r b, b>=2.
- For fixed (r,b), run-start y lies in one residue class mod 2^{r+b+1}.
- Same-band short-b words satisfy a Kraft-type contraction: q_B=sum_{(r,b) admissible, b<=B}2^{-(r+b)}<3/4.
- Hence long same-band short-b survivor sets are sublinear: |S_{B,k(X)}(X)|=O(X^{alpha_B}) with alpha_B<1 for k~c log X.
- Defect decomposition: if D_B(X) counts run-starts in [X,2X) whose next transition either has b>B or exits [X,2X), then |B(X)| <= O(log X) D_B(X) + O(X^{alpha_B}).

Primary lock:
DEFECT PACKING.
Need a rigorous sublinear bound on D_B(X)=D_B^long(X)+D_B^exit(X), or a stronger weighted defect bound sufficient to force sublinear dyadic run-start packing.

Target C146–C155:
1. Derive exact arithmetic bounds for long valuations b>B inside a fixed band [X,2X).
2. Count exits and reentries without treating them as independent.
3. Exploit that a cycle is finite and every exit must later reenter some dyadic scale.
4. Seek charging/injection schemes from exits to multiplicative height gain, valuation budget, or distinct states.
5. Optimize B=B(X) if useful, but track all dependencies.
6. Test whether D_B^long(X) can be bounded by O(X/2^{epsilon B}) after exact predecessor/run-start coding; reject if interval expansion cancels it.
7. Seek a deterministic excursion lemma controlling how often an orbit can cross [X,2X) boundaries.
8. Combine long-b and exit terms only if logically independent.
9. Falsify any proposed sublinear defect bound by explicit formal words or pseudo-orbits, while separating them from true cycles.
10. Return only proved lemmas; no probabilistic valuation assumptions.

Required return:
CLAIMS VERIFIED; NEW LEMMAS with proof; COUNTEREXAMPLES; bound on D_B^long(X); bound on D_B^exit(X); combined D_B(X); dependence on X,m,N,A,B; consequence for |B_h|; BEST GAIN; RESIDUAL; NEXTLOCK; verdict CYCLES OPEN/CLOSED.
