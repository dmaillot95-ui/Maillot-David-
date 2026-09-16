import itertools, json, math, random
from collections import Counter

CORE = [
    "verification",
    "metacognition",
    "self_improvement",
    "contradiction_detection",
    "failure_learning",
]

# This is a methodological ablation simulator over an explicit scoring model.
# It does NOT measure real AGI/superintelligence.
WEIGHT = {
    "verification": 1.35,
    "metacognition": 1.20,
    "self_improvement": 1.15,
    "contradiction_detection": 1.05,
    "failure_learning": 1.00,
}
PAIR_SYNERGY = {
    tuple(sorted(("verification","metacognition"))): 0.55,
    tuple(sorted(("verification","self_improvement"))): 0.42,
    tuple(sorted(("verification","contradiction_detection"))): 0.38,
    tuple(sorted(("verification","failure_learning"))): 0.33,
    tuple(sorted(("metacognition","self_improvement"))): 0.30,
    tuple(sorted(("contradiction_detection","failure_learning"))): 0.28,
}

random.seed(5601)

def score(subset):
    s = sum(WEIGHT[x] for x in subset)
    for a,b in itertools.combinations(sorted(subset),2):
        s += PAIR_SYNERGY.get((a,b),0)
    # small diminishing-return penalty keeps minimal sets competitive
    s -= 0.10 * max(0, len(subset)-3)**2
    return round(s, 6)

full = set(CORE)
full_score = score(full)

# exact exhaustive ablation over 31 non-empty subsets
exact = []
for k in range(1, len(CORE)+1):
    for comb in itertools.combinations(CORE,k):
        ss=set(comb)
        sc=score(ss)
        exact.append({
            "subset": sorted(ss),
            "size": len(ss),
            "score": sc,
            "retention": round(sc/full_score,6),
        })

# 2000 perturbation candidates: exact subset + tiny deterministic/noise-free context penalties
# Used only to stress ranking stability, not to create evidence.
candidates=[]
for i in range(2000):
    base = exact[i % len(exact)]
    subset=set(base["subset"])
    context=((i*37)%101)/1000.0
    robustness = score(subset) - context
    candidates.append({
        "id": i,
        "subset": sorted(subset),
        "size": len(subset),
        "robustness_score": round(robustness,6),
    })

funnel_sizes=[2000,1000,500,250,100,50,20,10,3,1]
stages=[]
current=candidates
for n in funnel_sizes[1:]:
    current=sorted(current,key=lambda x:(x["robustness_score"],-x["size"]),reverse=True)[:n]
    stages.append({"survivors":n,"best":current[0]})

# Leave-one-out necessity proxy under this model
loo=[]
for x in CORE:
    ss=full-{x}
    sc=score(ss)
    loo.append({
        "removed":x,
        "score_without":sc,
        "drop":round(full_score-sc,6),
        "retention":round(sc/full_score,6),
    })
loo.sort(key=lambda x:x["drop"], reverse=True)

# Minimal subsets retaining >= thresholds of modeled full capability
minimal_by_threshold={}
for thr in [0.70,0.80,0.90,0.95]:
    feasible=[x for x in exact if x["retention"]>=thr]
    min_size=min(x["size"] for x in feasible)
    best=sorted([x for x in feasible if x["size"]==min_size],key=lambda x:x["score"],reverse=True)[:10]
    minimal_by_threshold[str(thr)]={"min_size":min_size,"sets":best}

freq=Counter()
for x in sorted(candidates,key=lambda x:x["robustness_score"], reverse=True)[:100]:
    freq.update(x["subset"])

report={
    "schema":"cerebron-intelligence-core-ablation-2000-v1",
    "claim_scope":"methodological scoring-model ablation only; not evidence of AGI or superintelligence",
    "core":CORE,
    "full_score":full_score,
    "exact_subsets_evaluated":len(exact),
    "perturbation_candidates":len(candidates),
    "funnel":funnel_sizes,
    "stages":stages,
    "leave_one_out_ranked":loo,
    "minimal_sets_by_retention":minimal_by_threshold,
    "top100_factor_frequency":dict(freq),
    "final_candidate":current[0],
}

with open("intelligence-core-ablation-2000.json","w") as f:
    json.dump(report,f,indent=2)
print(json.dumps(report,indent=2))
