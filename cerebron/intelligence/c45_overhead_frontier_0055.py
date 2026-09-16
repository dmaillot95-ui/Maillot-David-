import json, math, random, statistics
from pathlib import Path

SCALES=[55]
SEEDS=[20261401,20261403,20261405,20261407,20261409,20261411,20261413,20261415,20261417,20261419,20261421,20261423,20261425]
FAMILIES=["affine","saturating","inverse","piecewise","noisy","shifted","sparse","dense","mixed","adversarial"]

# Exact frozen model from C45-OVERHEAD-FRONTIER-001; only scale 55 is inserted.
def make_tasks(seed,n):
    rng=random.Random(seed+n*1009)
    tasks=[]
    for i in range(n):
        fam=FAMILIES[i%len(FAMILIES)]
        d=0.7+1.6*rng.random(); a=0.2+0.8*rng.random(); v=0.3+0.7*rng.random(); s=0.25+0.75*rng.random()
        if fam in ("adversarial","noisy"): a*=1.25
        if fam in ("dense","inverse"): d*=1.18
        tasks.append((fam,d,a,v,s))
    return tasks

def unit_quality(t, policy, rng):
    fam,d,a,v,s=t
    if policy=="sham":
        eff=0.48*s+0.22*v+0.15/(1+d)+0.15/(1+a)-0.09*a-0.08*d
    else:
        routing=0.38*s+0.22*v+0.20/(1+d)+0.20/(1+a)
        scarcity=0.12*max(0.0,a-0.65)+0.10*max(0.0,d-1.8)
        eff=routing+0.07*v+0.04*s-scarcity
    q=max(0.0,min(1.0,eff+0.42+(rng.random()-0.5)*0.025))
    return q

def overhead(n):
    coord=0.018*n*math.log2(max(n,2))
    verify=0.30*n*(1+0.0015*n)
    fusion=0.0045*(n**1.18)
    context_penalty=0.0 if n<=100 else 0.0000028*((n-100)**2)
    return coord,verify,fusion,context_penalty

def run(seed,n,policy):
    tasks=make_tasks(seed,n)
    rng=random.Random(seed*97+n*13+(1 if policy=="sham" else 2))
    coord,verify_cost,fusion,ctx=overhead(n)
    raw=[]; famvals={k:[] for k in FAMILIES}
    for t in tasks:
        q=unit_quality(t,policy,rng)
        q=max(0.0,q-ctx)
        fam,d,a,v,s=t
        residual=(1-q)*(1+d+a)
        verified=q*(1+0.75*v)
        raw.append((residual,verified))
        famvals[fam].append((residual,verified))
    base_unit_cost=1.18*n
    total_cost=base_unit_cost+coord+verify_cost+fusion
    overhead_total=coord+verify_cost+fusion
    overhead_fraction=overhead_total/total_cost
    verified_total=sum(x[1] for x in raw)
    net_verified=max(0.0,verified_total-0.28*coord-0.16*verify_cost-0.35*fusion)
    return {
      "residual":statistics.mean(x[0] for x in raw),
      "verified_total":verified_total,
      "net_verified_work":net_verified,
      "net_vcgc":net_verified/total_cost,
      "total_cost":total_cost,
      "coordination_cost":coord,
      "verification_cost":verify_cost,
      "fusion_cost":fusion,
      "overhead_fraction":overhead_fraction,
      "context_penalty":ctx,
      "families":{f:{"net_proxy":statistics.mean(x[1] for x in z)} for f,z in famvals.items()}
    }

rows=[]; summaries=[]
for n in SCALES:
    local=[]
    for seed in SEEDS:
        s=run(seed,n,"sham"); c=run(seed,n,"candidate")
        local.append({"seed":seed,"sham":s,"candidate":c})
    wins=sum(r["candidate"]["net_vcgc"]>r["sham"]["net_vcgc"] and r["candidate"]["residual"]<r["sham"]["residual"] for r in local)
    fam_ok=0
    for fam in FAMILIES:
        cv=statistics.mean(r["candidate"]["families"][fam]["net_proxy"] for r in local)
        sv=statistics.mean(r["sham"]["families"][fam]["net_proxy"] for r in local)
        if cv>=0.98*sv: fam_ok+=1
    mean=lambda arm,key: statistics.mean(r[arm][key] for r in local)
    parity=max(abs(r["candidate"]["total_cost"]-r["sham"]["total_cost"]) for r in local)<1e-12
    oh=mean("candidate","overhead_fraction")
    passed=(wins/len(SEEDS)>=0.6 and fam_ok/len(FAMILIES)>=0.9 and oh<=0.35 and parity)
    summaries.append({
      "scale":n,
      "candidate":{"residual":mean("candidate","residual"),"net_verified_work":mean("candidate","net_verified_work"),"net_vcgc":mean("candidate","net_vcgc"),"overhead_fraction":oh,"context_penalty":mean("candidate","context_penalty")},
      "sham":{"residual":mean("sham","residual"),"net_verified_work":mean("sham","net_verified_work"),"net_vcgc":mean("sham","net_vcgc")},
      "wins_vs_sham":wins,
      "seeds":len(SEEDS),
      "family_non_regression":{"ok":fam_ok,"total":len(FAMILIES)},
      "resource_parity":parity,
      "gate":"PASS" if passed else "FAIL"
    })
    rows.append({"scale":n,"rows":local})

result={
 "id":"C45-OVERHEAD-FRONTIER-0055",
 "summaries":summaries,
 "claim_ceiling":"synthetic deterministic overhead model only; not actual LLM message throughput"
}
Path("artifacts").mkdir(exist_ok=True)
Path("artifacts/c45_overhead_frontier_0055_results.json").write_text(json.dumps({"result":result,"rows":rows},indent=2),encoding="utf-8")
print(json.dumps(result,indent=2))
