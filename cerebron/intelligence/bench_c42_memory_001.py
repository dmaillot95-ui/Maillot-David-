import json, math, random
from pathlib import Path

SEEDS=[20261201,20261202,20261203,20261204,20261205,20261206,20261207,20261208]
TRAIN_EPISODES=80
HIDDEN_EPISODES=120
ACTIONS=(0,1,2,3)


def make_task(rng):
    x=(rng.uniform(-1,1), rng.uniform(-1,1), rng.uniform(-1,1))
    scores=[
        1.10*x[0]-0.35*x[1]+0.20*x[2],
        -0.40*x[0]+1.25*x[1]-0.15*x[2],
        0.10*x[0]-0.20*x[1]+1.30*x[2],
        -0.55*x[0]-0.45*x[1]-0.50*x[2]+0.25*math.sin(3*x[0])
    ]
    best=max(range(4), key=lambda a:scores[a])
    return {"x":x,"best":best,"scores":scores}


def regret(task,a):
    return max(task["scores"])-task["scores"][a]


def nearest(experiences,x,k=7):
    ranked=[]
    for e in experiences:
        d=sum((a-b)**2 for a,b in zip(e["x"],x))
        ranked.append((d,e))
    return [e for _,e in sorted(ranked,key=lambda z:z[0])[:k]]


def raw_memory_policy(mem,x):
    if not mem: return 0
    ns=nearest(mem,x,7)
    votes=[0]*4
    for e in ns: votes[e["best"]]+=1
    return max(range(4), key=lambda a:(votes[a],-a))


def compress_rules(mem):
    # Per-action centroid: compact rule representation learned from training data.
    out={}
    for a in ACTIONS:
        pts=[e["x"] for e in mem if e["best"]==a]
        if pts:
            out[a]=tuple(sum(p[i] for p in pts)/len(pts) for i in range(3))
    return out


def rule_policy(rules,x,blocked=None):
    blocked=blocked or set()
    candidates=[]
    for a,c in rules.items():
        if a in blocked: continue
        d=sum((u-v)**2 for u,v in zip(c,x))
        candidates.append((d,a))
    return min(candidates)[1] if candidates else 0


def build_scars(mem,rules):
    # Scar = region where compressed rule repeatedly fails; boundary = radius around failure cluster.
    scars=[]
    for e in mem:
        p=rule_policy(rules,e["x"])
        if p!=e["best"]:
            scars.append({"x":e["x"],"bad_action":p,"good_action":e["best"]})
    return scars


def d_policy(rules,scars,x):
    near=nearest(scars,x,5) if scars else []
    blocked=set()
    rescue_votes=[0]*4
    for s in near:
        d=sum((a-b)**2 for a,b in zip(s["x"],x))
        if d<0.20:
            blocked.add(s["bad_action"])
            rescue_votes[s["good_action"]]+=1
    if max(rescue_votes,default=0)>0:
        best=max(range(4), key=lambda a:(rescue_votes[a],-a))
        if best not in blocked: return best
    return rule_policy(rules,x,blocked)


def evaluate_group(group,train,hidden):
    if group=="C":
        policy=lambda x:0
        mem_cost=0
    elif group=="A":
        policy=lambda x:raw_memory_policy(train,x)
        mem_cost=len(train)*4
    elif group=="B":
        rules=compress_rules(train)
        policy=lambda x:rule_policy(rules,x)
        mem_cost=len(rules)*4
    elif group=="D":
        rules=compress_rules(train)
        scars=build_scars(train,rules)
        policy=lambda x:d_policy(rules,scars,x)
        mem_cost=len(rules)*4+len(scars)*5
    else:
        raise ValueError(group)
    rs=[regret(t,policy(t["x"])) for t in hidden]
    acc=sum(1 for t in hidden if policy(t["x"])==t["best"])/len(hidden)
    return {"mean_regret":sum(rs)/len(rs),"accuracy":acc,"memory_units":mem_cost}


def main():
    per_seed=[]
    agg={g:[] for g in "ABCD"}
    for seed in SEEDS:
        trng=random.Random(seed*1009+11)
        hrng=random.Random(seed*1013+29)
        train=[]
        for _ in range(TRAIN_EPISODES):
            t=make_task(trng)
            train.append({"x":t["x"],"best":t["best"]})
        hidden=[make_task(hrng) for _ in range(HIDDEN_EPISODES)]
        row={"seed":seed}
        for g in "ABCD":
            r=evaluate_group(g,train,hidden)
            row[g]=r
            agg[g].append(r)
        per_seed.append(row)
    summary={}
    for g,vals in agg.items():
        summary[g]={
            "mean_regret":sum(v["mean_regret"] for v in vals)/len(vals),
            "accuracy":sum(v["accuracy"] for v in vals)/len(vals),
            "memory_units":sum(v["memory_units"] for v in vals)/len(vals)
        }
    d_wins_b=sum(1 for r in per_seed if r["D"]["mean_regret"]<r["B"]["mean_regret"])
    d_wins_a=sum(1 for r in per_seed if r["D"]["mean_regret"]<r["A"]["mean_regret"])
    ordering=sorted("ABCD", key=lambda g:summary[g]["mean_regret"])
    out={
        "benchmark_id":"BENCH-C42-MEMORY-001",
        "benchmark_type":"memory_not_learning_hidden_future_regret",
        "evidence_ceiling":"E3_verified_simulation",
        "seeds":SEEDS,
        "train_episodes":TRAIN_EPISODES,
        "hidden_episodes":HIDDEN_EPISODES,
        "groups":{
            "A":"raw_memory",
            "B":"compressed_rules",
            "C":"no_cumulative_memory",
            "D":"rules_scars_boundaries_causal_credit_proxy"
        },
        "summary":summary,
        "ordering_lowest_regret_first":ordering,
        "D_seed_wins_vs_B":d_wins_b,
        "D_seed_wins_vs_A":d_wins_a,
        "preregistered_hypothesis_D_gt_B_gt_A_gt_C": ordering==["D","B","A","C"],
        "claim_limit":"Synthetic benchmark of future decision quality under four memory regimes; not evidence of general intelligence or autonomous learning."
    }
    Path("bench_c42_memory_001_results.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))

if __name__=="__main__":
    main()
