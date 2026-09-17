# CEREBRON OMEGA — COLLATZ C256 LIVE-WEB LITERATURE BRIEF

SOURCE STATUS: externally researched by ChatGPT live web, not by GitHub workers.
DATE: 2026-09-17.

## 1. STURMIAN / IRRATIONAL ROTATION PRIOR ART
Mechanical words of irrational slope are Sturmian codings of irrational circle rotations. Classical return-word theory states that every factor of a Sturmian word has exactly two return words. Relevant sources identified:
- Jacques Justin, Laurent Vuillon, Return words in Sturmian and episturmian words, RAIRO 34(5), 2000, pp. 343-356, DOI 10.1051/ita:2000121.
- M. Lothaire, Algebraic Combinatorics on Words, chapter Sturmian Words.

Use: do not reinvent return-word combinatorics. Translate the Collatz balanced mechanical family into this framework and identify whether the first-exit / stay-out / first-reentry condition corresponds to return words to a factor/interval or to a stricter affine-threshold condition.

## 2. COLLATZ EXPONENT-CODE PRIOR ART (2026)
Oliver Kramer, Adaptive Search in Collatz Exponent-Code Space via 2-adic and 3-adic Constraints, arXiv:2607.10041, 2026-07-10.
Key facts from the paper:
- finite accelerated exponent code determines real drift 3^k/2^{A_k}, a 2-adic start representative, and a 3-adic endpoint representative;
- for a genuine infinite code from one fixed positive start, both normalized residue-growth rates must asymptotically vanish;
- mechanical critical codes a_i in {1,2} were tested at lengths 100, 200, 400 and retained positive residue rates in experiments;
- authors explicitly state this is diagnostic evidence, not a proof of Collatz.

Use: C256 must include endpoint 3-adic compatibility alongside 2-adic start cylinder and archimedean first-return window. Finite experiments are falsification only.

## 3. RESEARCH RULE
WEB SOURCE != PROOF.
Any imported theorem must be re-derived in the exact notation used here before inclusion in the proof chain.
Any numerical experiment from the literature is evidence for search prioritization only.

## 4. C256 ADJUSTMENT
Next state must consider at least:
- balanced/Sturmian phase state theta under alpha=log2(3);
- exact archimedean episode window I_W(X);
- exact 2-adic start residue rho_W mod 2^{A_n+1};
- exact 3-adic endpoint residue or equivalent endpoint congruence mod 3^n;
- return-word/first-return combinatorics;
- affine offsets C_k/2^{A_k}.

Unique target: prove or refute a uniform obstruction for arbitrarily long balanced first-return episodes once ALL real + 2-adic + 3-adic constraints are imposed.
