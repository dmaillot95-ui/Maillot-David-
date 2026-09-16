import itertools, json, math, random
from collections import Counter

FACTORS = ["contradiction_detection","metacognition","self_improvement","verification"]

# Hypothesis-testing only: scores are methodological, not a claim about real intelligence.
EDGE_PRIOR = {
    ("contradiction_detection","metacognition"): 1.25,
    ("metacognition","self_improvement"): 1.35,
    ("self_improvement","verification"): 1.45,
    ("verification","contradiction_detection"): 1.30,
    ("verification","metacognition"): 1.15,
    ("contradiction_detection","verification"): 1.10,
}

BASE = {
    "contradiction_detection": 1.10,
    "metacognition": 1.25,
    "self_improvement": 1.35,
    "verification": 1.50,
}


def score_order(order, feedback_edges):
    s = sum(BASE[x] for x in order)
    for a,b in zip(order, order[1:]):
        s += EDGE_PRIOR.get((a,b), -0.25)
    # reward closed corrective loop only if feedback returns verification to an earlier diagnostic stage
    for e in feedback_edges:
        s += EDGE_PRIOR.get(e, -0.15)
    # penalties for bad sequencing
    if order.index("self_improvement") < order.index("metacognition"):
        s -= 0.70
    if order.index("verification") < order.index("self_improvement"):
        s -= 0.50
    if order.index("contradiction_detection") > order.index("self_improvement"):
        s -= 0.60
    return s

candidates = []
# Exhaustive 24 orders × selected feedback variants, then jittered to 2000 for robustness ranking.
feedback_pool = [
    tuple(),
    (("verification","contradiction_detection"),),
    (("verification","metacognition"),),
    (("contradiction_detection","verification"),),
    (("verification","contradiction_detection"),("verification","metacognition")),
]
for order in itertools.permutations(FACTORS):
    for fb in feedback_pool:
        candidates.append({"order": order, "feedback": fb, "base_score": score_order(order, fb)})

rng = random.Random(5601)
expanded = []
for i in range(2000):
    c = candidates[i % len(candidates)]
    # deterministic robustness perturbation around the structural score
    perturb = rng.uniform(-0.25, 0.25)
    expanded.append({
        "id": i,
        "order": c["order"],
        "feedback": c["feedback"],
        "score": c["base_score"] + perturb,
        "base_score": c["base_score"],
    })

stages = [2000,1000,500,250,100,50,20,10,3,1]
pool = expanded
funnel = []
for n in stages:
    pool = sorted(pool, key=lambda x:(x["score"],x["base_score"]), reverse=True)[:n]
    funnel.append({"n":n,"top_score":pool[0]["score"],"top_order":pool[0]["order"],"top_feedback":pool[0]["feedback"]})

# Stability among top 100
elite = sorted(expanded, key=lambda x:x["score"], reverse=True)[:100]
order_counts = Counter(tuple(x["order"]) for x in elite)
edge_counts = Counter()
for x in elite:
    for e in zip(x["order"], x["order"][1:]): edge_counts[e]+=1
    for e in x["feedback"]: edge_counts[e]+=1

winner = pool[0]
report = {
    "schema":"cerebron-intelligence-core-dynamics-2000-v1",
    "methodological_only": True,
    "claim_real_superintelligence": False,
    "factors": FACTORS,
    "candidate_count": 2000,
    "unique_orders": math.factorial(len(FACTORS)),
    "feedback_variants": len(feedback_pool),
    "funnel": funnel,
    "winner": winner,
    "top_100_order_counts": [{"order":list(k),"count":v} for k,v in order_counts.most_common(10)],
    "top_100_edge_counts": [{"edge":list(k),"count":v} for k,v in edge_counts.most_common(12)],
    "interpretation_limit":"Ranks causal-loop hypotheses under a hand-defined methodological score; does not establish a scientific law of intelligence."
}
with open("intelligence-core-dynamics-2000.json","w") as f:
    json.dump(report,f,indent=2)
print(json.dumps(report,indent=2))
