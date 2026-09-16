#!/usr/bin/env python3
import json, itertools, math, random, hashlib
from collections import Counter

SEED=56016
random.seed(SEED)

REGROUPING = [
    'generalization','transfer','causal_modeling','abstraction','decomposition',
    'invention','verification','metacognition','strategy_memory','contradiction_detection',
    'failure_learning','experiment_design','self_improvement','uncertainty_calibration',
    'proof_generation','tool_use','planning','compression','representation_change','world_modeling'
]

DISSOCIATING = [
    'raw_compute','raw_memory','agent_count','benchmark_overfit','data_volume',
    'memorization','prompt_length','latency_advantage','duplicate_sampling','majority_vote',
    'retrieval_only','external_human_scaffolding','hidden_labels','train_test_leakage','resource_scaling'
]

# Mechanisms that should co-occur in a serious capability core.
SYNERGY = {
    ('generalization','transfer'): 4.0,
    ('invention','verification'): 5.0,
    ('metacognition','uncertainty_calibration'): 4.5,
    ('contradiction_detection','verification'): 4.0,
    ('failure_learning','self_improvement'): 4.5,
    ('experiment_design','causal_modeling'): 4.0,
    ('abstraction','representation_change'): 3.5,
    ('planning','world_modeling'): 3.5,
    ('proof_generation','verification'): 4.5,
}

FUNDAMENTAL = {
    'generalization','transfer','invention','verification','metacognition',
    'uncertainty_calibration','contradiction_detection','failure_learning',
    'self_improvement','experiment_design'
}


def h(x:str)->float:
    z=int(hashlib.sha256(x.encode()).hexdigest()[:12],16)
    return (z % 1000000)/1000000.0


def generate_candidate(i):
    # 5..10 regrouping mechanisms, 0..5 dissociating explanations.
    rs = sorted(random.sample(REGROUPING, random.randint(5,10)))
    ds = sorted(random.sample(DISSOCIATING, random.randint(0,5)))
    return {'id':f'cand-{i:04d}','regrouping':rs,'dissociating':ds}


def score(c):
    rs=set(c['regrouping']); ds=set(c['dissociating'])
    fundamental=len(rs & FUNDAMENTAL)
    synergy=0.0
    for (a,b),w in SYNERGY.items():
        if a in rs and b in rs: synergy += w
    breadth=len(rs)
    # Penalize explanations that can fake capability gain.
    diss_penalty=2.75*len(ds)
    resource_penalty=3.5*len(ds & {'raw_compute','raw_memory','agent_count','data_volume','resource_scaling'})
    leakage_penalty=7.0*len(ds & {'benchmark_overfit','hidden_labels','train_test_leakage'})
    complexity_penalty=max(0,breadth-8)*0.7
    novelty=h(c['id']+'|'+','.join(c['regrouping']))
    return 3.0*fundamental + synergy + 0.8*breadth + novelty - diss_penalty - resource_penalty - leakage_penalty - complexity_penalty


def funnel(items, schedule):
    hist=[]
    cur=items
    for k in schedule:
        ranked=sorted(cur,key=score,reverse=True)[:k]
        hist.append({'size':k,'best_score':score(ranked[0]),'best_id':ranked[0]['id']})
        cur=ranked
    return cur,hist

cands=[generate_candidate(i) for i in range(2000)]

# Funnel 1: suppress dissociating explanations first.
def dissociation_score(c):
    return -len(c['dissociating'])*10 + len(c['regrouping']) + score(c)*0.1

def generic_funnel(items, schedule, keyfn):
    hist=[]; cur=items
    for k in schedule:
        cur=sorted(cur,key=keyfn,reverse=True)[:k]
        hist.append({'size':k,'best_id':cur[0]['id'],'best_score':keyfn(cur[0])})
    return cur,hist

schedule=[1000,500,250,100,50,20,10,3,1]
diss_survivors,diss_hist=generic_funnel(cands,schedule,dissociation_score)
reg_survivors,reg_hist=funnel(cands,schedule)

# Cross-factor pool from top 100 under final score and low-dissociation top 100.
top_reg=sorted(cands,key=score,reverse=True)[:100]
top_diss=sorted(cands,key=dissociation_score,reverse=True)[:100]
intersection={c['id']:c for c in top_reg if c['id'] in {x['id'] for x in top_diss}}
if len(intersection)<20:
    # union with heavy penalty on dissociation, to ensure a sufficiently sized cross-pool
    pool=sorted(cands,key=lambda c: score(c)-8*len(c['dissociating']),reverse=True)[:200]
else:
    pool=list(intersection.values())

cross_schedule=[100,50,20,10,3,1]
cross_survivors,cross_hist=funnel(pool,cross_schedule)

# Mine recurring factors and pairs in the 50 strongest low-dissociation architectures.
elite=sorted(cands,key=lambda c: score(c)-8*len(c['dissociating']),reverse=True)[:50]
factor_counts=Counter()
pair_counts=Counter()
for c in elite:
    for x in c['regrouping']:
        factor_counts[x]+=1
    for a,b in itertools.combinations(sorted(c['regrouping']),2):
        pair_counts[(a,b)]+=1

winner=cross_survivors[0]
report={
    'schema':'cerebron-intelligence-core-funnel-v1',
    'claim':'methodological factor-mining experiment; not evidence of superintelligence',
    'seed':SEED,
    'initial_candidates':2000,
    'dissociation_funnel':diss_hist,
    'regrouping_funnel':reg_hist,
    'cross_factor_funnel':cross_hist,
    'winner':winner,
    'winner_score':score(winner),
    'top_common_factors':factor_counts.most_common(12),
    'top_common_pairs':[[list(k),v] for k,v in pair_counts.most_common(15)],
    'elite_count':len(elite),
    'paid_api_calls':0,
    'spend_eur':0.0
}
print(json.dumps(report,indent=2))
with open('intelligence-core-funnel.json','w') as f:
    json.dump(report,f,indent=2)
