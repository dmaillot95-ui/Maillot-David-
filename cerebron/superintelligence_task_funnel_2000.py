import json, random, itertools, math
from collections import Counter, defaultdict

# CEREBRON Ω — Superintelligence task decomposition funnel
# Methodological decomposition only. This does NOT create or prove superintelligence.
# Goal: generate 2000 atomic capability-task candidates, cluster by function,
# reduce redundancy, and search for compact capability graphs with broad coverage.

SEED = 20260916
rng = random.Random(SEED)

DOMAINS = {
    'PERCEPTION': ['signal_extraction','anomaly_detection','state_estimation','feature_binding','temporal_segmentation'],
    'WORLD_MODEL': ['causal_modeling','counterfactual_modeling','latent_structure','system_identification','uncertainty_modeling'],
    'REASONING': ['deduction','induction','abduction','constraint_solving','decomposition'],
    'CRITIQUE': ['contradiction_detection','verification','calibration','adversarial_check','error_localization'],
    'LEARNING': ['failure_learning','few_shot_update','strategy_update','representation_learning','credit_assignment'],
    'TRANSFER': ['cross_domain_transfer','analogy','invariant_extraction','representation_reuse','task_reformulation'],
    'PLANNING': ['goal_decomposition','search_control','resource_allocation','branch_pruning','contingency_planning'],
    'CREATIVITY': ['hypothesis_generation','representation_change','experiment_design','concept_composition','novel_operator_search'],
    'META': ['metacognition','self_model','confidence_estimation','unknown_detection','policy_selection'],
    'SELF_IMPROVEMENT': ['self_improvement','tool_creation','procedure_refinement','benchmark_creation','automated_ablation'],
    'MEMORY': ['episodic_retrieval','semantic_compression','strategy_memory','provenance_tracking','forgetting_control'],
    'COORDINATION': ['task_routing','consensus_check','independence_check','conflict_resolution','result_fusion'],
}

# externally desirable properties, kept distinct from implementation mechanisms
PROPERTIES = ['accuracy','robustness','transfer','sample_efficiency','calibration','novelty','verification','adaptation','compression','self_correction']

# Factors that can fake progress if mistaken for intelligence gain.
DISSOCIATORS = ['more_compute','more_memory','more_agents','more_training_data','benchmark_leakage','memorization','longer_context','prompt_overfitting']

# Each atomic candidate is a task definition rather than an "agent".
def make_candidate(i):
    domain = rng.choice(list(DOMAINS))
    mechanism = rng.choice(DOMAINS[domain])
    primary = rng.choice(PROPERTIES)
    secondary = rng.choice([p for p in PROPERTIES if p != primary])
    difficulty = rng.randint(1,10)
    observability = rng.randint(1,10)
    transfer_span = rng.randint(1,10)
    verifiability = rng.randint(1,10)
    diss = rng.sample(DISSOCIATORS, rng.randint(0,2))
    # A deterministic structural score for funneling; not a scientific intelligence metric.
    coverage = 2.0 + 0.7*transfer_span + 0.8*verifiability + 0.35*difficulty + 0.25*observability
    coverage += 1.2*(primary in ('transfer','verification','self_correction','adaptation'))
    coverage += 0.6*(secondary in ('transfer','verification','self_correction','adaptation'))
    penalty = 1.8*len(diss)
    score = coverage - penalty
    return {
        'id': f'T{i:04d}', 'domain':domain, 'mechanism':mechanism,
        'primary_property':primary,'secondary_property':secondary,
        'difficulty':difficulty,'observability':observability,'transfer_span':transfer_span,
        'verifiability':verifiability,'dissociators':diss,'score':round(score,4)
    }

candidates = [make_candidate(i) for i in range(1,2001)]

# De-duplicate near-equivalent atomic tasks by structural signature; retain best representative.
best_by_sig = {}
for c in candidates:
    sig=(c['domain'],c['mechanism'],c['primary_property'],c['secondary_property'])
    if sig not in best_by_sig or c['score'] > best_by_sig[sig]['score']:
        best_by_sig[sig]=c
unique=list(best_by_sig.values())
unique.sort(key=lambda x:x['score'], reverse=True)

funnel_sizes=[2000,1000,500,250,100,50,20,10]
stages={}
current=sorted(candidates,key=lambda x:x['score'],reverse=True)
for n in funnel_sizes:
    current=current[:min(n,len(current))]
    stages[str(n)]=[x['id'] for x in current]

# Build domain/mechanism frequency among elite 100 and elite 50.
elite100=sorted(unique,key=lambda x:x['score'],reverse=True)[:100]
elite50=elite100[:50]
domain_freq=Counter(x['domain'] for x in elite100)
mechanism_freq=Counter(x['mechanism'] for x in elite100)
property_freq=Counter(p for x in elite100 for p in (x['primary_property'],x['secondary_property']))

# Search compact capability graphs. One node per selected mechanism.
# Reward broad functional coverage, external properties, verifiability, transfer; penalize size and dissociators.
pool=[]
seen=set()
for c in unique:
    key=(c['domain'],c['mechanism'])
    if key not in seen:
        pool.append(c); seen.add(key)

# retain strongest 3 mechanisms per domain for tractable combinatorial search
by_domain=defaultdict(list)
for c in pool: by_domain[c['domain']].append(c)
for d in by_domain: by_domain[d].sort(key=lambda x:x['score'],reverse=True)
small_pool=[c for d in DOMAINS for c in by_domain[d][:3]]

CORE_DOMAINS={'WORLD_MODEL','REASONING','CRITIQUE','LEARNING','TRANSFER','META','SELF_IMPROVEMENT'}

def graph_score(nodes):
    domains={n['domain'] for n in nodes}
    props={n['primary_property'] for n in nodes}|{n['secondary_property'] for n in nodes}
    mechs={n['mechanism'] for n in nodes}
    base=sum(n['score'] for n in nodes)/len(nodes)
    coverage=3.0*len(domains & CORE_DOMAINS)+1.0*len(domains-CORE_DOMAINS)
    propcov=0.9*len(props)
    special=0
    for m in ['verification','contradiction_detection','metacognition','self_improvement','causal_modeling','cross_domain_transfer','representation_change','failure_learning']:
        if m in mechs: special += 1.3
    penalty=0.75*len(nodes)
    return base+coverage+propcov+special-penalty

# 2000 graph candidates sampled at sizes 5..10, constrained to at least 4 distinct core domains.
graphs=[]
for i in range(2000):
    k=rng.randint(5,10)
    nodes=rng.sample(small_pool,k)
    if len({n['domain'] for n in nodes}&CORE_DOMAINS)<4:
        continue
    gs=graph_score(nodes)
    graphs.append({'id':f'G{i:04d}','score':round(gs,4),'nodes':[n['mechanism'] for n in nodes],'domains':sorted({n['domain'] for n in nodes})})
graphs.sort(key=lambda g:g['score'],reverse=True)

# Funnel graphs
sizes=[2000,1000,500,250,100,50,20,10,3,1]
graph_funnel={}
for n in sizes:
    graph_funnel[str(n)]=[g['id'] for g in graphs[:min(n,len(graphs))]]

winner=graphs[0] if graphs else None
# Common factors in top50 graphs
common=Counter()
pairs=Counter()
for g in graphs[:50]:
    ns=sorted(set(g['nodes']))
    common.update(ns)
    pairs.update(itertools.combinations(ns,2))

result={
    'claim':'methodological decomposition only; not AGI/superintelligence evidence',
    'seed':SEED,
    'atomic_candidates':len(candidates),
    'unique_structural_tasks':len(unique),
    'atomic_funnel':stages,
    'elite100_domain_frequency':domain_freq.most_common(),
    'elite100_mechanism_frequency':mechanism_freq.most_common(20),
    'elite100_property_frequency':property_freq.most_common(),
    'graph_candidates_evaluated':len(graphs),
    'graph_funnel':graph_funnel,
    'winner':winner,
    'top50_common_mechanisms':common.most_common(20),
    'top50_common_pairs':[[list(k),v] for k,v in pairs.most_common(20)],
    'next_test':'replace structural score with executable benchmark tasks and perform ablations under equal compute/data budgets.'
}
open('superintelligence_task_funnel_2000.json','w').write(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
