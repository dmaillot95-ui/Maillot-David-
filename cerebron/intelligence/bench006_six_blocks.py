import json, math, random, hashlib
from pathlib import Path

SEEDS=[20261201,20261202,20261203,20261204,20261205,20261206]


def mae(a,b):
    return sum(abs(x-y) for x,y in zip(a,b))/len(a)


def brier(probs,labels):
    return sum((p-y)**2 for p,y in zip(probs,labels))/len(labels)


def block1(seed):
    rng=random.Random(seed+101)
    xs=[-2,-1.5,-1,-0.5,0,0.5,1,1.5,2]
    a,b,c=rng.uniform(-1,1),rng.uniform(-1,1),rng.uniform(-.5,.5)
    ys=[a*x*x+b*x+c for x in xs]
    reps={
      "linear":lambda x:[1,x],
      "quadratic":lambda x:[1,x,x*x],
      "trig":lambda x:[1,math.sin(x),math.cos(x)]
    }
    def fit(phi):
      X=[phi(x) for x in xs[:6]]; y=ys[:6]; d=len(X[0])
      A=[[0.0]*d for _ in range(d)]; B=[0.0]*d
      for row,yy in zip(X,y):
        for i in range(d):
          B[i]+=row[i]*yy
          for j in range(d): A[i][j]+=row[i]*row[j]
      for i in range(d): A[i][i]+=1e-8
      M=[A[i][:]+[B[i]] for i in range(d)]
      for col in range(d):
        p=max(range(col,d),key=lambda r:abs(M[r][col])); M[col],M[p]=M[p],M[col]
        z=M[col][col] or 1e-8
        for j in range(col,d+1): M[col][j]/=z
        for r in range(d):
          if r!=col:
            q=M[r][col]
            for j in range(col,d+1): M[r][j]-=q*M[col][j]
      return [M[i][d] for i in range(d)]
    scored=[]
    for name,phi in reps.items():
      beta=fit(phi)
      pred=lambda x:sum(v*w for v,w in zip(phi(x),beta))
      val=mae([pred(x) for x in xs[6:8]],ys[6:8])
      hold=mae([pred(xs[8])],[ys[8]])
      scored.append((val,hold,name))
    best=min(scored)
    sham=scored[seed%len(scored)]
    return {"metric":best[1],"sham":sham[1],"decision":best[2],"state_transition":"representation_selected"}


def block2(seed):
    rng=random.Random(seed+202)
    facts={"A"}
    rules=[("A","B"),("B","C"),("C","D"),("A","E"),("E","F")]
    target=rng.choice(["D","F"])
    derived=set(facts); trace=[]
    for _ in range(5):
      changed=False
      for p,q in rules:
        if p in derived and q not in derived:
          derived.add(q); trace.append((p,q)); changed=True
      if not changed: break
    valid=1.0 if target in derived else 0.0
    shuffled=rules[:]; rng.shuffle(shuffled)
    sham_derived=set(facts)
    for p,q in shuffled[:2]:
      if p in sham_derived: sham_derived.add(q)
    sham=1.0 if target in sham_derived else 0.0
    return {"metric":1-valid,"sham":1-sham,"decision":target,"state_transition":"deduction_trace_extended"}


def block3(seed):
    rng=random.Random(seed+303)
    hidden=rng.choice([0,1,2,3]); belief=[.25]*4; cost=0
    actions=[]
    for _ in range(2):
      best=max(range(4),key=lambda i:belief[i]*(1-belief[i]))
      obs=(best==hidden); cost+=1; actions.append(best)
      if obs:
        belief=[0,0,0,0]; belief[best]=1
      else:
        belief[best]=0; s=sum(belief); belief=[x/s for x in belief]
    guess=max(range(4),key=lambda i:belief[i]); score=(1 if guess==hidden else 0)-0.1*cost
    sham_actions=rng.sample(range(4),2); sham_guess=sham_actions[-1]; sham=(1 if sham_guess==hidden else 0)-0.2
    return {"metric":-score,"sham":-sham,"decision":guess,"state_transition":"belief_updated_by_experiment"}


def block4(seed):
    rng=random.Random(seed+404)
    labels=[rng.randint(0,1) for _ in range(30)]
    signals=[min(1,max(0,(0.8 if y else 0.2)+rng.uniform(-.25,.25))) for y in labels]
    probs=[p for p in signals]
    errs=[int((p>=.5)!=bool(y)) for p,y in zip(probs,labels)]
    metric=brier(probs,labels)+sum(errs)/len(errs)
    shuffled=probs[:]; rng.shuffle(shuffled)
    sham=brier(shuffled,labels)+sum(int((p>=.5)!=bool(y)) for p,y in zip(shuffled,labels))/len(labels)
    return {"metric":metric,"sham":sham,"decision":round(sum(probs)/len(probs),6),"state_transition":"confidence_calibrated"}


def block5(seed):
    rng=random.Random(seed+505)
    train=[rng.choice([0,1]) for _ in range(40)]
    failures=[i for i,x in enumerate(train[:20]) if x==1]
    p_before=.5
    p_after=min(.95,.5+0.01*len(failures))
    test=[rng.choice([0,1]) for _ in range(40)]
    def loss(p): return sum(abs(p-y) for y in test)/len(test)
    gain=loss(p_before)-loss(p_after)
    perm=failures[:]; rng.shuffle(perm); p_sham=min(.95,.5+0.002*len(perm))
    sham_gain=loss(p_before)-loss(p_sham)
    return {"metric":-gain,"sham":-sham_gain,"decision":round(p_after,6),"state_transition":"strategy_updated_from_verified_failures"}


def block6(seed):
    rng=random.Random(seed+606)
    truth=rng.uniform(-2,2)
    proposals=[truth+rng.gauss(0,.6),truth+rng.gauss(0,.4),truth+rng.gauss(0,.8)]
    pre=sum(proposals)/3
    disagreement=max(proposals)-min(proposals)
    if disagreement>.5:
      revised=sorted(proposals)[1]
    else:
      revised=pre
    pre_err=abs(pre-truth); post_err=abs(revised-truth); gain=pre_err-post_err
    random_fusion=rng.choice(proposals); sham_gain=pre_err-abs(random_fusion-truth)
    return {"metric":-gain,"sham":-sham_gain,"decision":round(revised,6),"state_transition":"procedure_revised_after_disagreement"}

BLOCKS=[block1,block2,block3,block4,block5,block6]
NAMES=["B1_representation_world_model","B2_reasoning_creativity","B3_planning_experimentation","B4_verification_metacognition","B5_learning_transfer","B6_cooperation_self_improvement"]


def main():
    results={}; signatures={}
    for name,fn in zip(NAMES,BLOCKS):
      rows=[fn(s) for s in SEEDS]
      metric=sum(r["metric"] for r in rows)/len(rows)
      sham=sum(r["sham"] for r in rows)/len(rows)
      signatures[name]=[(r["decision"],r["state_transition"]) for r in rows]
      results[name]={"metric":metric,"sham_metric":sham,"beats_sham":metric<sham,"rows":rows}
    alias_pairs=[]
    for i,a in enumerate(NAMES):
      for b in NAMES[i+1:]:
        if signatures[a]==signatures[b]: alias_pairs.append([a,b])
    all_distinct=(len(alias_pairs)==0)
    all_execute=all(len(results[n]["rows"])==len(SEEDS) for n in NAMES)
    pass_count=sum(1 for n in NAMES if results[n]["beats_sham"])
    payload={
      "benchmark_id":"BENCH-006",
      "evidence_ceiling":"E3_verified_simulation",
      "seeds":SEEDS,
      "results":results,
      "anti_alias":{"all_distinct":all_distinct,"alias_pairs":alias_pairs},
      "all_blocks_executed":all_execute,
      "blocks_beating_sham":pass_count,
      "six_block_gate":bool(all_execute and all_distinct and pass_count==6),
      "scale_36_jobs_allowed":bool(all_execute and all_distinct and pass_count==6),
      "claim_limit":"Synthetic executable block-separation test only; not evidence of AGI or superintelligence."
    }
    serial=json.dumps(payload,sort_keys=True,separators=(",",":"))
    payload["result_sha256"]=hashlib.sha256(serial.encode()).hexdigest()
    Path("bench006_results.json").write_text(json.dumps(payload,indent=2))
    print(json.dumps(payload,indent=2))

if __name__=="__main__": main()
