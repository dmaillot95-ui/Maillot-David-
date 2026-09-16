import json, math, random, statistics
from pathlib import Path

SEEDS=[20260916,20260917,20260918,20260919,20260920]
SOURCE=["affine","quadratic","cubic"]
TARGET=["absolute_affine","rational","mixed_sine"]
MODELS=["constant","linear","quadratic","cubic","absolute_linear","rational_linear","sine_linear","mixed_generic"]


def gen_params(rng,fam):
    if fam=="affine": return (rng.uniform(-2,2),rng.uniform(-2,2))
    if fam=="quadratic": return tuple(rng.uniform(-1.5,1.5) for _ in range(3))
    if fam=="cubic": return tuple(rng.uniform(-1,1) for _ in range(4))
    if fam=="absolute_affine": return (rng.uniform(-2,2),rng.uniform(-1.5,1.5),rng.uniform(-1,1))
    if fam=="rational": return (rng.uniform(-2,2),rng.uniform(-2,2),rng.uniform(0.6,1.8))
    if fam=="mixed_sine": return (rng.uniform(-2,2),rng.uniform(-1.5,1.5),rng.uniform(-1,1))
    raise ValueError(fam)


def f(x,fam,p):
    if fam=="affine": a,b=p; return a*x+b
    if fam=="quadratic": a,b,c=p; return a*x*x+b*x+c
    if fam=="cubic": a,b,c,d=p; return a*x**3+b*x*x+c*x+d
    if fam=="absolute_affine": a,b,c=p; return a*abs(x)+b*x+c
    if fam=="rational": a,b,c=p; return a/(c+abs(x))+b*x
    if fam=="mixed_sine": a,b,c=p; return a*math.sin(x)+b*x+c


def features(name,x):
    if name=="constant": return [1.0]
    if name=="linear": return [1.0,x]
    if name=="quadratic": return [1.0,x,x*x]
    if name=="cubic": return [1.0,x,x*x,x**3]
    if name=="absolute_linear": return [1.0,x,abs(x)]
    if name=="rational_linear": return [1.0,x,1.0/(1.0+abs(x))]
    if name=="sine_linear": return [1.0,x,math.sin(x)]
    if name=="mixed_generic": return [1.0,x,x*x,abs(x),1.0/(1.0+abs(x)),math.sin(x),math.cos(x)]
    raise ValueError(name)


def solve(A,b):
    n=len(b); M=[A[i][:]+[b[i]] for i in range(n)]
    for col in range(n):
        piv=max(range(col,n),key=lambda r:abs(M[r][col]))
        M[col],M[piv]=M[piv],M[col]
        if abs(M[col][col])<1e-10: M[col][col]=1e-10
        z=M[col][col]
        for j in range(col,n+1): M[col][j]/=z
        for r in range(n):
            if r==col: continue
            q=M[r][col]
            for j in range(col,n+1): M[r][j]-=q*M[col][j]
    return [M[i][n] for i in range(n)]


def fit_model(name,points):
    X=[features(name,x) for x,y in points]; y=[y for x,y in points]; d=len(X[0])
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
    p=gen_params(rng,fam)
    xs=[]
    while len(xs)<24:
        x=round(rng.uniform(-3,3),6)
        if all(abs(x-z)>1e-4 for z in xs): xs.append(x)
    vals=[(x,f(x,fam,p)) for x in xs]
    return vals[:14],vals[14:20],vals[20:24]  # final query target remains harness-only


def score_models(fitpts,valpts,weights,prior=None):
    out=[]
    for name in MODELS:
        beta=fit_model(name,fitpts)
        tr=mae_model(name,beta,fitpts); va=mae_model(name,beta,valpts)
        complexity=len(beta)
        instability=abs(va-tr)
        prior_rank=(prior or {}).get(name,0.0)
        # Observable-only selector. No final query target, latent params, or family label.
        score=(
            weights.get("verification",0)*va +
            weights.get("contradiction_detection",0)*instability +
            weights.get("complexity_penalty",0)*0.04*complexity +
            weights.get("uncertainty_penalty",0)*0.25*instability +
            weights.get("compute_penalty",0)*0.01*complexity -
            weights.get("transfer",0)*0.05*prior_rank -
            weights.get("evidence",0)*0.02*len(valpts)
        )
        out.append((score,name,beta,va))
    return sorted(out,key=lambda z:(z[0],z[1]))


def learn_prior(rng,weights):
    wins={m:0 for m in MODELS}
    total=0
    for fam in SOURCE:
        for _ in range(24):
            fitpts,valpts,_=task(rng,fam)
            ranked=score_models(fitpts,valpts,weights,None)
            for rank,(_,name,_,_) in enumerate(ranked): wins[name]+=len(MODELS)-rank
            total+=1
    mx=max(wins.values()) or 1
    return {m:wins[m]/mx for m in MODELS}


def evaluate(weights,use_transfer=True,ablate=None):
    per_seed=[]; family_all={f:[] for f in TARGET}
    for seed in SEEDS:
        rng=random.Random(seed)
        w=dict(weights)
        if ablate: w[ablate]=0.0
        prior=learn_prior(rng,w) if use_transfer else None
        errs=[]; famerrs={f:[] for f in TARGET}; success=0; n=0
        for fam in TARGET:
            for _ in range(24):
                fitpts,valpts,query=task(rng,fam)
                ranked=score_models(fitpts,valpts,w,prior)
                _,name,beta,_=ranked[0]
                for x,y in query:
                    e=abs(pred(name,beta,x)-y); errs.append(e); famerrs[fam].append(e); n+=1
                    if e<=0.5: success+=1
        for fam in TARGET: family_all[fam].extend(famerrs[fam])
        per_seed.append({"seed":seed,"mae":sum(errs)/len(errs),"success_rate":success/n})
    return {
        "mae":sum(d["mae"] for d in per_seed)/len(per_seed),
        "success_rate":sum(d["success_rate"] for d in per_seed)/len(per_seed),
        "per_seed":per_seed,
        "per_family_mae":{f:sum(v)/len(v) for f,v in family_all.items()}
    }


def neutral_weights():
    return {"verification":1.0,"contradiction_detection":0.0,"transfer":0.0,"evidence":0.0,"uncertainty_penalty":0.0,"complexity_penalty":0.0,"compute_penalty":0.0}


def main():
    cfg=json.loads(Path("cerebron/intelligence/cognitive_weights.json").read_text())
    a0=cfg["weights"]
    baseline=evaluate(neutral_weights(),False)
    no_transfer=evaluate(a0,False)
    full=evaluate(a0,True)
    used=["verification","contradiction_detection","transfer","evidence","uncertainty_penalty","complexity_penalty","compute_penalty"]
    ablations={}
    for k in used:
        r=evaluate(a0,True,k)
        ablations[k]={"mae":r["mae"],"delta_mae_vs_full":r["mae"]-full["mae"]}
    seed_wins=sum(1 for b,f in zip(baseline["per_seed"],full["per_seed"]) if f["mae"]<b["mae"])
    transfer_gain=no_transfer["mae"]-full["mae"]
    leakage_audit={
        "final_target_visible_to_selector":False,
        "latent_parameters_visible_to_selector":False,
        "domain_label_visible_to_selector":False,
        "verification_uses_final_target":False,
        "transfer_uses_target_tasks_for_prior":False
    }
    out={
        "benchmark_id":"BENCH-003",
        "benchmark_type":"deterministic_synthetic_leak_resistant_meta_weight_test",
        "evidence_ceiling":"E3_verified_simulation",
        "seeds":SEEDS,
        "source_families":SOURCE,
        "heldout_target_families":TARGET,
        "same_candidate_model_budget":True,
        "baseline":baseline,
        "a0_no_transfer":no_transfer,
        "a0_full":full,
        "transfer_gain_mae":transfer_gain,
        "full_beats_baseline_seed_count":seed_wins,
        "weight_ablations":ablations,
        "weight_coverage":{"used":used,"not_exercised":[k for k in a0 if k not in used]},
        "leakage_audit":leakage_audit,
        "H1_full_beats_neutral":full["mae"]<baseline["mae"],
        "H2_transfer_positive":transfer_gain>0,
        "H3_any_ablation_effect":any(abs(v["delta_mae_vs_full"])>1e-9 for v in ablations.values()),
        "claim_limit":"Synthetic deterministic benchmark only; not evidence of AGI, superintelligence, neural-weight learning, or external generalization."
    }
    Path("benchmark_v2_1_results.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))

if __name__=="__main__": main()
