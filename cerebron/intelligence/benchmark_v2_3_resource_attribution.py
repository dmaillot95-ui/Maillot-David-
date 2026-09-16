import hashlib, json, math, random
from pathlib import Path

SEEDS=[20261101,20261102,20261103,20261104,20261105,20261106,20261107,20261108,20261109]
SOURCE=["affine","quadratic","cubic"]
TARGET=["chirp_affine","saturating_tanh","inverse_quadratic"]
MODELS=["constant","linear","quadratic","cubic","absolute_linear","rational_linear","sine_linear","mixed_generic","tanh_generic","invquad_generic","chirp_generic"]
BUDGETS=[("low",4,2),("medium",7,4),("full",11,6)]


def gen_params(rng,fam):
    if fam=="affine": return (rng.uniform(-2,2),rng.uniform(-2,2))
    if fam=="quadratic": return tuple(rng.uniform(-1.5,1.5) for _ in range(3))
    if fam=="cubic": return tuple(rng.uniform(-1,1) for _ in range(4))
    if fam=="chirp_affine": return (rng.uniform(-2,2),rng.uniform(0.35,0.9),rng.uniform(-1,1))
    if fam=="saturating_tanh": return (rng.uniform(-2,2),rng.uniform(0.45,1.35),rng.uniform(-1,1))
    if fam=="inverse_quadratic": return (rng.uniform(-2,2),rng.uniform(0.3,1.1),rng.uniform(-1,1))
    raise ValueError(fam)


def f(x,fam,p):
    if fam=="affine": a,b=p; return a*x+b
    if fam=="quadratic": a,b,c=p; return a*x*x+b*x+c
    if fam=="cubic": a,b,c,d=p; return a*x**3+b*x*x+c*x+d
    if fam=="chirp_affine":
        a,b,c=p; return a*math.sin(x+b*x*abs(x))+c
    if fam=="saturating_tanh":
        a,b,c=p; return a*math.tanh(b*x)+c
    if fam=="inverse_quadratic":
        a,b,c=p; return a/(1.0+b*x*x)+c
    raise ValueError(fam)


def features(name,x):
    if name=="constant": return [1.0]
    if name=="linear": return [1.0,x]
    if name=="quadratic": return [1.0,x,x*x]
    if name=="cubic": return [1.0,x,x*x,x**3]
    if name=="absolute_linear": return [1.0,x,abs(x)]
    if name=="rational_linear": return [1.0,x,1.0/(1.0+abs(x))]
    if name=="sine_linear": return [1.0,x,math.sin(x),math.cos(x)]
    if name=="mixed_generic": return [1.0,x,x*x,abs(x),math.sin(x),math.cos(x),1.0/(1.0+abs(x))]
    if name=="tanh_generic": return [1.0,math.tanh(0.5*x),math.tanh(x),math.tanh(1.5*x)]
    if name=="invquad_generic": return [1.0,1.0/(1.0+0.35*x*x),1.0/(1.0+0.7*x*x),1.0/(1.0+1.1*x*x)]
    if name=="chirp_generic": return [1.0,math.sin(x+0.35*x*abs(x)),math.sin(x+0.6*x*abs(x)),math.sin(x+0.9*x*abs(x))]
    raise ValueError(name)


def solve(A,b):
    n=len(b); M=[A[i][:]+[b[i]] for i in range(n)]
    for col in range(n):
        piv=max(range(col,n),key=lambda r:abs(M[r][col])); M[col],M[piv]=M[piv],M[col]
        if abs(M[col][col])<1e-10: M[col][col]=1e-10
        z=M[col][col]
        for j in range(col,n+1): M[col][j]/=z
        for r in range(n):
            if r==col: continue
            q=M[r][col]
            for j in range(col,n+1): M[r][j]-=q*M[col][j]
    return [M[i][n] for i in range(n)]


def fit_model(name,pts):
    X=[features(name,x) for x,y in pts]; y=[y for x,y in pts]; d=len(X[0])
    A=[[0.0]*d for _ in range(d)]; b=[0.0]*d
    for row,yy in zip(X,y):
        for i in range(d):
            b[i]+=row[i]*yy
            for j in range(d): A[i][j]+=row[i]*row[j]
    for i in range(d): A[i][i]+=1e-6
    return solve(A,b)


def pred(name,beta,x): return sum(a*b for a,b in zip(beta,features(name,x)))
def mae_model(name,beta,pts): return sum(abs(pred(name,beta,x)-y) for x,y in pts)/len(pts)


def task(rng,fam):
    p=gen_params(rng,fam); xs=[]
    while len(xs)<28:
        x=round(rng.uniform(-3,3),6)
        if all(abs(x-z)>1e-4 for z in xs): xs.append(x)
    vals=[(x,f(x,fam,p)) for x in xs]
    return vals[:16],vals[16:22],vals[22:28]


def build_banks():
    source={}; target={}
    for seed in SEEDS:
        srng=random.Random(seed+11100000); trng=random.Random(seed+11200000)
        source[seed]=[(fam,task(srng,fam)) for fam in SOURCE for _ in range(20)]
        target[seed]=[(fam,task(trng,fam)) for fam in TARGET for _ in range(30)]
    serial=json.dumps(target,sort_keys=True,separators=(",",":"))
    return source,target,hashlib.sha256(serial.encode()).hexdigest()


def score_models(fitpts,valpts,weights,prior,candidates):
    ranked=[]
    for name in candidates:
        beta=fit_model(name,fitpts); tr=mae_model(name,beta,fitpts); va=mae_model(name,beta,valpts)
        complexity=len(beta); instability=abs(va-tr); prior_rank=(prior or {}).get(name,0.0)
        score=(weights.get("verification",0)*va
               +weights.get("contradiction_detection",0)*instability
               +weights.get("complexity_penalty",0)*0.04*complexity
               +weights.get("uncertainty_penalty",0)*0.25*instability
               +weights.get("compute_penalty",0)*0.01*complexity
               -weights.get("transfer",0)*0.05*prior_rank
               -weights.get("evidence",0)*0.02*len(valpts))
        ranked.append((score,name,beta))
    return sorted(ranked,key=lambda z:(z[0],z[1]))


def learn_prior(tasks,weights,candidates,val_n):
    wins={m:0 for m in candidates}
    for fam,(fitpts,valpts,query) in tasks:
        ranked=score_models(fitpts,valpts[:val_n],weights,None,candidates)
        for rank,(_,name,_) in enumerate(ranked): wins[name]+=len(candidates)-rank
    mx=max(wins.values()) or 1
    return {m:wins[m]/mx for m in candidates}


def evaluate(weights,source_bank,target_bank,model_n,val_n):
    candidates=MODELS[:model_n]
    per_seed=[]; famall={f:[] for f in TARGET}
    for seed in SEEDS:
        prior=learn_prior(source_bank[seed],weights,candidates,val_n)
        errs=[]; famerrs={f:[] for f in TARGET}; success=0; n=0
        for fam,(fitpts,valpts,query) in target_bank[seed]:
            _,name,beta=score_models(fitpts,valpts[:val_n],weights,prior,candidates)[0]
            for x,y in query:
                e=abs(pred(name,beta,x)-y); errs.append(e); famerrs[fam].append(e); n+=1
                if e<=0.5: success+=1
        per_seed.append({"seed":seed,"mae":sum(errs)/len(errs),"success_rate":success/n})
        for fam in TARGET: famall[fam].extend(famerrs[fam])
    return {
        "mae":sum(x["mae"] for x in per_seed)/len(per_seed),
        "success_rate":sum(x["success_rate"] for x in per_seed)/len(per_seed),
        "per_seed":per_seed,
        "per_family_mae":{f:sum(v)/len(v) for f,v in famall.items()},
        "resource_units_per_target_task":model_n*val_n,
        "candidate_models":model_n,
        "validation_points":val_n
    }


def neutral_weights():
    return {"verification":1.0,"contradiction_detection":0.0,"transfer":0.0,"evidence":0.0,"uncertainty_penalty":0.0,"complexity_penalty":0.0,"compute_penalty":0.0}


def main():
    a0=json.loads(Path("cerebron/intelligence/cognitive_weights.json").read_text())["weights"]
    a1=json.loads(Path("cerebron/intelligence/cognitive_weights_A1_candidate.json").read_text())["weights"]
    source,target,bank_hash=build_banks()
    profiles={"neutral":neutral_weights(),"A0":a0,"A1":a1}
    results={}
    for label,mn,vn in BUDGETS:
        results[label]={k:evaluate(w,source,target,mn,vn) for k,w in profiles.items()}
        r0=results[label]["A0"]; r1=results[label]["A1"]
        results[label]["A1_minus_A0_mae"]=r1["mae"]-r0["mae"]
        results[label]["A1_seed_wins"]=sum(1 for x,y in zip(r0["per_seed"],r1["per_seed"]) if y["mae"]<x["mae"])
    full=results["full"]
    family_reg={f:(full["A1"]["per_family_mae"][f]-full["A0"]["per_family_mae"][f])/max(full["A0"]["per_family_mae"][f],1e-12) for f in TARGET}
    no_material_regression=all(v<=0.05 for v in family_reg.values())
    equal_budget_pass=(full["A1"]["mae"]<full["A0"]["mae"] and full["A1_seed_wins"]>=6 and no_material_regression)
    all_equal=all(results[b]["A0"]["resource_units_per_target_task"]==results[b]["A1"]["resource_units_per_target_task"]==results[b]["neutral"]["resource_units_per_target_task"] for b,_,_ in BUDGETS)
    signs=[results[b]["A1_minus_A0_mae"]<0 for b,_,_ in BUDGETS]
    out={
        "benchmark_id":"BENCH-005",
        "benchmark_type":"sealed_resource_attribution_equal_budget_test",
        "evidence_ceiling":"E3_verified_simulation",
        "target_task_bank_sha256":bank_hash,
        "seeds":SEEDS,
        "target_families":TARGET,
        "results_by_budget":results,
        "full_budget_family_relative_regression_A1_vs_A0":family_reg,
        "no_material_family_regression":no_material_regression,
        "all_conditions_equal_resource_within_budget":all_equal,
        "A1_beats_A0_at_all_budget_levels":all(signs),
        "equal_full_budget_gate":equal_budget_pass,
        "interpretation":"reject_resource_only_explanation_within_this_benchmark" if equal_budget_pass and all_equal else "resource_only_explanation_not_rejected",
        "claim_limit":"This test can only assess whether a local A1-vs-A0 advantage survives deterministic equal-resource controls in this synthetic benchmark. It is not evidence of AGI or superintelligence."
    }
    Path("benchmark_v2_3_resource_attribution_results.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))

if __name__=="__main__": main()
