# CÉRÉBRON Ω — COLLATZ C136–C145 AGENT MISSION

Checkpoint: C135 closed only to the extent explicitly proved. Full Collatz and arbitrary-cycle exclusion remain OPEN.

Verified inputs to use:
- Accelerated map on positive odds: T(x)=(3x+1)/2^{v2(3x+1)}.
- Runs are valuation blocks 1^r b with b>=2.
- For a run start y, v2(y+1)=r+1.
- For fixed (r,b), y lies in a unique residue class modulo 2^{r+b+1}.
- Exact transition: y' = [3^{r+1}/2^{r+b}](y+1)-2^{1-b}.
- Let beta=log2(3/2). If X<=y,y'<2X, then 1/2<lambda<2 and therefore (r+1)beta < b < (r+1)beta+2; hence at most two integer b values for each r.
- Writing f_r={(r+1)beta}, same-band log increment is f_r or f_r-1.
- For a fixed valuation word over k runs, the initial run-start lies in a unique residue class modulo 2^{V_k+1}, where V_k=sum_j(r_j+b_j).

Primary lock:
WORD-ENTROPY vs 2-ADIC MODULUS.
We need a rigorous upper bound on the number of admissible k-run words that can stay in or return repeatedly to a logarithmic dyadic window of width 1, strong enough compared with 2^{V_k} to yield sub-exponential dyadic packing.

Target C136–C145:
1. Short-b / same-band dynamics.
2. Count admissible choices of (r,b) under the width-1 log-walk constraint.
3. Determine whether the two-branch increments f_r and f_r-1 have a deterministic balancing restriction over repeated visits.
4. Exploit irrationality/equidistribution only if it yields a rigorous deterministic bound; no probabilistic orbit assumption.
5. Compare combinatorial word count with the exact modulus 2^{V_k+1}.
6. Search for a Kraft-type, coding, entropy, automaton, renewal, transfer-operator, discrepancy, Sturmian/Beatty, or Diophantine mechanism.
7. Falsify any proposed subexponential word-count bound by explicit formal words if possible, while separating formal words from realizable Collatz cycles.
8. Track dependence on X,m,N,A,k exactly.

Forbidden shortcuts:
- no finite computation as universal proof;
- no heuristic randomness of valuations;
- no assumption that different rotations are independent constraints;
- no claim that rare residue classes imply rare orbit events without injection/counting;
- no declaration CYCLES CLOSED unless N arbitrary is actually covered.

Required return:
CLAIMS VERIFIED; NEW LEMMAS with proof; COUNTEREXAMPLES; WORD COUNT BOUND; MODULUS GROWTH; consequence for |B_h|; gaps/circularities; BEST GAIN; RESIDUAL; NEXTLOCK; verdict CYCLES OPEN/CLOSED.