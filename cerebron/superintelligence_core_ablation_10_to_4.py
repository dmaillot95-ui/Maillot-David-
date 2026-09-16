import itertools, json

NODES = [
    'semantic_compression','deduction','procedure_refinement','system_identification',
    'result_fusion','representation_reuse','independence_check','confidence_estimation',
    'failure_learning','verification'
]

CAPS = {
    'semantic_compression': {'memory','abstraction'},
    'deduction': {'reasoning'},
    'procedure_refinement': {'self_improvement'},
    'system_identification': {'world_model'},
    'result_fusion': {'coordination'},
    'representation_reuse': {'transfer'},
    'independence_check': {'robustness','verification'},
    'confidence_estimation': {'metacognition','uncertainty'},
    'failure_learning': {'learning','self_correction'},
    'verification': {'verification','robustness'},
}

REQUIRED = {'verification','learning','transfer','reasoning','world_model','self_improvement'}

# Pair synergies inherited from prior funnels; these are model assumptions, not empirical laws.
SYNERGY = {
    frozenset(('failure_learning','verification')): 2.2,
    frozenset(('representation_reuse','deduction')): 1.3,
    frozenset(('procedure_refinement','verification')): 1.6,
    frozenset(('system_identification','deduction')): 1.2,
    frozenset(('confidence_estimation','verification')): 1.1,
    frozenset(('independence_check','verification')): 1.0,
    frozenset(('result_fusion','independence_check')): 0.8,
    frozenset(('semantic_compression','representation_reuse')): 0.7,
}

def score(sub):
    caps=set()
    for n in sub: caps |= CAPS[n]
    coverage=len(caps & REQUIRED)/len(REQUIRED)
    breadth=len(caps)
    syn=sum(v for k,v in SYNERGY.items() if k.issubset(sub))
    redundancy=max(0, len(sub)-6)*0.18
    missing=len(REQUIRED - caps)
    return round(10*coverage + 0.22*breadth + syn - redundancy - 3.0*missing, 6), sorted(caps), sorted(REQUIRED-caps)

rows=[]
for k in range(4,11):
    for sub in itertools.combinations(NODES,k):
        s,caps,missing=score(set(sub))
        rows.append({'k':k,'nodes':list(sub),'score':s,'caps':caps,'missing_required':missing})

rows.sort(key=lambda r:(r['score'],-r['k']), reverse=True)

best_by_k={}
for r in rows:
    best_by_k.setdefault(str(r['k']), r)

full=next(r for r in rows if r['k']==10)
ablations=[]
for n in NODES:
    sub=set(NODES)-{n}
    s,caps,missing=score(sub)
    ablations.append({'removed':n,'score':s,'delta_vs_full':round(full['score']-s,6),'missing_required':missing})
ablations.sort(key=lambda x:x['delta_vs_full'], reverse=True)

minimal_full=[r for r in rows if not r['missing_required']]
minimal_k=min(r['k'] for r in minimal_full)
best_minimal=next(r for r in minimal_full if r['k']==minimal_k)

out={
    'candidate_subsets': len(rows),
    'range':'10_to_4',
    'required_capabilities':sorted(REQUIRED),
    'full_graph':full,
    'best_by_size':best_by_k,
    'ablation_importance':ablations,
    'minimal_full_coverage_size':minimal_k,
    'best_minimal_full_coverage':best_minimal,
    'note':'Deterministic structural ablation over a hand-specified capability map and synergy model; not empirical evidence of intelligence or superintelligence.'
}
print(json.dumps(out,indent=2))
open('superintelligence_core_ablation_10_to_4.json','w').write(json.dumps(out,indent=2))
