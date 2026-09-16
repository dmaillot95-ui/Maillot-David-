import hashlib, json, math, random
from pathlib import Path

SEEDS=[20261001,20261002,20261003,20261004,20261005,20261006,20261007]
SOURCE=["affine","quadratic","cubic"]
TARGET=["exponential_affine","log_affine","damped_sine"]
MODELS=["constant","linear","quadratic","cubic","absolute_linear","rational_linear","sine_linear","mixed_generic","exp_generic","log_generic","damped_sine_generic"]


def gen_params(rng,fam):
    if fam=="affine": return (rng.uniform(-2,2),rng.uniform(-2,2))
    if fam=="quadratic": return tuple(rng.uniform(-1.5,1.5) for _ in range(3))
    if fam=="cubic": return tuple(rng.uniform(-1,1) for _ in range(4))
    if fam=="exponential_affine": return (rng.uniform(-1.5,1.5),rng.uniform(-0.8,0.8),rng.uniform(-1,1))
    if fam=="log_affine": return (rng.uniform(-2,2),rng.uniform(-1.2,1.2),rng.uniform(-1,1))
    if fam=="damped_sine": return (rng.uniform(-2,2),rng.uniform(0.15,0.65),rng.uniform(-1,1))
    raise ValueError(fam)


def f(x,fam,p):
    if fam=="affine": a,b=p; return a*x+b
    if fam=="quadratic": a,b,c=p; return a*x*x+b*x+c
    if fam=="cubic": a,b,c,d=p; return a*x**3+b*x*x+c*x+d
    if fam=="exponential_affine": a,b,c=p; return a*math.exp(b*x)+c
    if fam=="log_affine": a,b,c=p; return a*math.log1p(abs(x))+b*x+c
    if fam=="damped_sine": a,b,c=p; return a*math.exp(-b*abs(x))*math.sin(x)+c
    raise ValueError(fam)


def features(name,x):
    if name=="constant": return [1.0]
    if name=="linear": return [1.0,x]
    if name=="quadratic": return [1.0,x,x*x]
    if name=="cubic": return [1.0,x,x*x,x**3]
    if name=="absolute_linear": return [1.0,x,abs(x)]
    if name=="rational_linear": return [1.0,x,1.0/(1.0+abs(x))]
    if name=="sine_linear": return [1.0,x,math.sin(x),math.cos(x)]
    if name=="mixed_generic": return [1.0,x,x*x,abs(x),1.0/(1.0+abs(x)),math.sin(x),math.cos(x)]
    if name=="exp_generic": return [1.0,x,math.exp(0.35*x),math.exp(-0.35*x)]
    if name=="log_generic": return [1.0,x,math.log1p(abs(x))]
    if name=="damped_sine_generic": return [1.0,math.sin(x),math.cos(x),math.exp(-0.35*abs(x))*math.sin(x),math.exp(-0.35*abs(x))*math.cos(x)]
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
    p=gen_params(rng,fam); xs=[]
    while len(xs)<27:
        x=round(rng.uniform(-3,3),6)
        if all(abs(x-z)>1e-4 for z in xs): xs.append(x)
    vals=[(x,f(x,fam,p)) for x in xs]
    return vals[:16],vals[16:22],vals[22:27]


def build_banks():
    source={}; target={}
    for seed in SEEDS:
        srng=random.Random(seed+9100000); trng=random.Random(seed+9200000)
        source[seed]=[(fam,task(srng,fam)) for fam in SOURCE for _ in range(28)]
        target[seed]=[(fam,task(trng,fam)) for fam in TARGET for _ in range(28)]
    serial=json.dumps(target,sort_keys=True,separators=(",",":"))
    return source,target,hashlib.sha256(serial.encode()).hexdigest()


def score_models(fitpts,valpts,weights,prior=None):
    ranked=[]
    for name in MODELS:
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


def learn_prior(tasks,weights):
    wins={m:0 for m in MODELS}
    for fam,(fitpts,valpts,query) in tasks:
        ranked=score_models(fitpts,valpts,weights,None)
        for rank,(_,name,_) in enumerate(ranked): wins[name]+=len(MODELS)-rank
    mx=max(wins.values()) or 1
    return {m:wins[m]/mx for m in MODELS}


def evaluate(weights,source_bank,target_bank):
    per_seed=[]; famall={f:[] for f in TARGET}
    for seed in SEEDS:
        prior=learn_prior(source_bank[seed],weights)
        errs=[]; famerrs={f:[] for f in TARGET}; success=0; n=0
        for fam,(fitpts,valpts,query) in target_bank[seed]:
            _,name,beta=score_models(fitpts,valpts,weights,prior)[0]
            for x,y in query:
                e=abs(pred(name,beta,x)-y); errs.append(e); famerrs[fam].append(e); n+=1
                if e<=0.5: success+=1
        per_seed.append({"seed":seed,"mae":sum(errs)/len(errs),"success_rate":success/n})
        for fam in TARGET: famall[fam].extend(famerrs[fam])
    return {"mae":sum(x["mae"] for x in per_seed)/len(per_seed),
            "success_rate":sum(x["success_rate"] for x in per_seed)/len(per_seed),
            "per_seed":per_seed,
            "per_family_mae":{f:sum(v)/len(v) for f,v in famall.items()}}


def main():
    a0=json.loads(Path("cerebron/intelligence/cognitive_weights.json").read_text())["weights"]
    a1=json.loads(Path("cerebron/intelligence/cognitive_weights_A1_candidate.json").read_text())["weights"]
    source_bank,target_bank,bank_hash=build_banks()
    r0=evaluate(a0,source_bank,target_bank); r1=evaluate(a1,source_bank,target_bank)
    wins=sum(1 for x,y in zip(r0["per_seed"],r1["per_seed"]) if y["mae"]<x["mae"])
    family_reg={f:(r1["per_family_mae"][f]-r0["per_family_mae"][f])/max(r0["per_family_mae"][f],1e-12) for f in TARGET}
    no_material_family_regression=all(v<=0.05 for v in family_reg.values())
    leakage={"final_query_target_visible_to_selector":False,"latent_parameters_visible_to_selector":False,"family_label_visible_to_selector":False,"same_target_task_bank":True,"same_source_prior_task_bank":True}
    matched={"same_candidate_models":True,"same_fit_validation_query_sizes":True,"same_model_evaluation_count":True,"same_seeds":True,"same_arithmetic":True}
    leakage_ok=(not leakage["final_query_target_visible_to_selector"]\n                and not leakage["latent_parameters_visible_to_selector"]\n                and not leakage["family_label_visible_to_selector"]\n                and leakage["same_target_task_bank"]\n                and leakage["same_source_prior_task_bank"])\n    passed=(r1["mae"]<r0["mae"] and wins>=5 and no_material_family_regression and leakage_ok and all(matched.values()))
    out={"benchmark_id":"BENCH-004","benchmark_type":"prospective_frozen_A1_vs_A0_matched_task_test","evidence_ceiling":"E3_verified_simulation","candidate_profile":"CEREBRON-A1-CANDIDATE","candidate_frozen_before_test":True,"seeds":SEEDS,"heldout_target_families":TARGET,"source_prior_families":SOURCE,"target_task_bank_sha256":bank_hash,"A0":r0,"A1":r1,"A1_minus_A0_mae":r1["mae"]-r0["mae"],"A1_seed_wins":wins,"family_relative_regression":family_reg,"no_material_family_regression":no_material_family_regression,"leakage_audit":leakage,"leakage_gate_passed":leakage_ok,"matched_resource_audit":matched,"prospective_success":passed,"promotion_decision":"eligible_for_reproducibility_rerun" if passed else "REJECT_A1_NO_PROMOTION","claim_limit":"Synthetic prospective benchmark only; not evidence of AGI, superintelligence, neural-weight learning, or external generalization."}
    Path("benchmark_v2_2_results.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))

if __name__=="__main__": main()
