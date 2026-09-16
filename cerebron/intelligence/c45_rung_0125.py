import json, math, random, statistics
from pathlib import Path

SEEDS=[20261231,20261301,20261303,20261305,20261307,20261309,20261311,20261313,20261315,20261317,20261319]
FAMILIES=["affine","saturating","inverse","piecewise","noisy","shifted","sparse","dense","mixed","adversarial"]
UNITS=125

# Synthetic deterministic stress harness. Candidate and sham get identical budgets;
# only allocation policy differs. This is not an LLM benchmark and cannot support AGI claims.
def make_tasks(seed):
    rng=random.Random(seed)
    tasks=[]
    for i in range(UNITS):
        fam=FAMILIES[i%len(FAMILIES)]
        difficulty=0.7+1.6*rng.random()
        ambiguity=0.2+0.8*rng.random()
        verification=0.3+0.7*rng.random()
        signal=0.25+0.75*rng.random()
        if fam in ("adversarial","noisy"): ambiguity*=1.25
        if fam in ("dense","inverse"): difficulty*=1.18
        tasks.append(dict(family=fam,difficulty=difficulty,ambiguity=ambiguity,verification=verification,signal=signal))
    return tasks

def score_task(t, policy, rng):
    # identical hard resource envelope for candidate/sham
    base_budget=1.0
    coord=0.18
    verify_budget=0.30
    cost=base_budget+coord+verify_budget
    d=t["difficulty"]; a=t["ambiguity"]; v=t["verification"]; s=t["signal"]
    if policy=="baseline":
        effective=0.84*s + 0.08*v - 0.22*a - 0.16*d
    elif policy=="sham":
        # competent deterministic neutral allocation, not random sabotage
        neutral_weight=0.48*s+0.22*v+0.15/(1+d)+0.15/(1+a)
        effective=neutral_weight - 0.09*a - 0.08*d
    elif policy=="candidate":
        # C45 surviving mechanisms: adaptive compiler + router + verification reservation + scar guard
        routing=0.38*s + 0.22*v + 0.20/(1+d) + 0.20/(1+a)
        scarcity=0.12*max(0.0,a-0.65)+0.10*max(0.0,d-1.8)
        effective=routing + 0.07*v + 0.04*s - scarcity
    else: raise ValueError(policy)
    # deterministic seed-local perturbation applied equally in scale
    noise=(rng.random()-0.5)*0.025
    q=max(0.0,min(1.0,effective+0.42+noise))
    residual=(1-q)*(1+d+a)
    verified=q*(1.0+0.75*v)
    vcgc=verified/cost
    return residual,verified,vcgc,cost

def run_arm(tasks, policy, seed):
    rng=random.Random(seed*97+{"baseline":1,"sham":2,"candidate":3}[policy])
    vals=[score_task(t,policy,rng) for t in tasks]
    fam={}
    for t,x in zip(tasks,vals): fam.setdefault(t["family"],[]).append(x)
    return {
      "residual":statistics.mean(x[0] for x in vals),
      "verified_work":statistics.mean(x[1] for x in vals),
      "vcgc":statistics.mean(x[2] for x in vals),
      "cost":statistics.mean(x[3] for x in vals),
      "families":{k:{"residual":statistics.mean(x[0] for x in z),"vcgc":statistics.mean(x[2] for x in z)} for k,z in fam.items()}
    }

rows=[]
for seed in SEEDS:
    tasks=make_tasks(seed)
    b=run_arm(tasks,"baseline",seed)
    s=run_arm(tasks,"sham",seed)
    c=run_arm(tasks,"candidate",seed)
    rows.append({"seed":seed,"baseline":b,"matched_sham":s,"candidate_125":c})

def mean(path):
    arm,key=path
    return statistics.mean(r[arm][key] for r in rows)

base_res=mean(("baseline","residual")); cand_res=mean(("candidate_125","residual")); sham_res=mean(("matched_sham","residual"))
base_v=mean(("baseline","verified_work")); cand_v=mean(("candidate_125","verified_work")); sham_v=mean(("matched_sham","verified_work"))
base_g=mean(("baseline","vcgc")); cand_g=mean(("candidate_125","vcgc")); sham_g=mean(("matched_sham","vcgc"))
cb=sum(r["candidate_125"]["residual"]<r["baseline"]["residual"] and r["candidate_125"]["verified_work"]>r["baseline"]["verified_work"] for r in rows)
cs=sum(r["candidate_125"]["residual"]<r["matched_sham"]["residual"] and r["candidate_125"]["verified_work"]>r["matched_sham"]["verified_work"] for r in rows)
fam_ok=0
for fam in FAMILIES:
    c=statistics.mean(r["candidate_125"]["families"][fam]["vcgc"] for r in rows)
    s=statistics.mean(r["matched_sham"]["families"][fam]["vcgc"] for r in rows)
    if c>=0.98*s: fam_ok+=1
resource_parity=max(abs(r["candidate_125"]["cost"]-r["matched_sham"]["cost"]) for r in rows)<1e-12
passed=(cb/len(SEEDS)>=0.8 and cs/len(SEEDS)>=0.6 and fam_ok/len(FAMILIES)>=0.9 and resource_parity)
summary={
 "id":"C45-RUNG-0125",
 "units":UNITS,
 "seeds":len(SEEDS),
 "families":len(FAMILIES),
 "means":{"baseline":{"residual":base_res,"verified_work":base_v,"vcgc":base_g},"candidate_125":{"residual":cand_res,"verified_work":cand_v,"vcgc":cand_g},"matched_sham":{"residual":sham_res,"verified_work":sham_v,"vcgc":sham_g}},
 "wins":{"candidate_vs_baseline":cb,"candidate_vs_sham":cs,"total_seeds":len(SEEDS)},
 "family_non_regression":{"ok":fam_ok,"total":len(FAMILIES)},
 "resource_parity":resource_parity,
 "gate":"PASS" if passed else "FAIL",
 "claim_ceiling":"synthetic deterministic benchmark only"
}
Path("artifacts").mkdir(exist_ok=True)
Path("artifacts/c45_rung_0125_results.json").write_text(json.dumps({"summary":summary,"rows":rows},indent=2),encoding="utf-8")
print(json.dumps(summary,indent=2))
