#!/usr/bin/env python3
import json, hashlib, random, statistics
from dataclasses import dataclass

SEEDS=[20261801,20261802,20261803,20261804,20261805,20261806,20261807,20261808,20261809,20261810,20261811,20261812,20261813]
FAMILIES=["standard","false_simple","scar_inversion","mixed_shift","high_uncertainty","dependency_spike","tight_budget","duplicate_mismatch","evidence_scarcity","nonreducible_easy","reducible_hard","compound_adversarial","budget_dependency_collision","evidence_inversion","router_trap"]

@dataclass
class Task:
    family:str; difficulty:int; dependencies:int; uncertainty:float; true_reducible:bool; observed_reducible:bool; reducibility_confidence:float; negative_trigger:bool; observed_negative_trigger:bool; scar_confidence:float; evidence_required:bool; evidence_availability:float; budget_cap:int

def make_tasks(seed,n_per_family=60):
    r=random.Random(seed); out=[]
    for fam in FAMILIES:
        for _ in range(n_per_family):
            d=r.randint(1,5); dep=r.randint(0,4); u=r.random(); tr=r.random()<.35; obs=tr; rc=r.uniform(.55,.98); neg=r.random()<.18; oneg=neg; sc=r.uniform(.55,.98); ev=r.random()<.70; ea=r.uniform(.55,1); cap=30
            if fam=="false_simple":
                if r.random()<.72: obs=not tr
                rc=r.uniform(.40,.92)
            elif fam=="scar_inversion":
                if r.random()<.68: oneg=not neg
                sc=r.uniform(.40,.92)
            elif fam=="mixed_shift":
                if r.random()<.45: obs=not tr
                if r.random()<.45: oneg=not neg
            elif fam=="high_uncertainty": u=r.uniform(.78,1); ev=True
            elif fam=="dependency_spike": dep=r.randint(4,8)
            elif fam=="tight_budget": cap=r.choice([12,14,16,18])
            elif fam=="evidence_scarcity": ev=True; ea=r.uniform(.15,.45)
            elif fam=="nonreducible_easy": tr=False; obs=r.random()<.40; d=r.choice([1,2]); u=r.uniform(.1,.5)
            elif fam=="reducible_hard": tr=True; obs=r.random()<.80; d=r.choice([4,5]); u=r.uniform(.55,.95)
            elif fam=="compound_adversarial":
                dep=r.randint(3,7); u=r.uniform(.65,1); ev=True; cap=r.choice([16,18,20,22]); ea=r.uniform(.25,.65)
                if r.random()<.55: obs=not tr
                if r.random()<.55: oneg=not neg
            elif fam=="budget_dependency_collision": dep=r.randint(5,9); cap=r.choice([12,14,16]); u=r.uniform(.55,.9)
            elif fam=="evidence_inversion": ev=True; ea=r.uniform(.2,.75); u=r.uniform(.6,1); obs=not tr if r.random()<.5 else tr
            elif fam=="router_trap": dep=r.randint(2,8); u=r.uniform(.35,.95); d=r.choice([2,3,4,5]); oneg=not neg if r.random()<.4 else neg
            out.append(Task(fam,d,dep,u,tr,obs,rc,neg,oneg,sc,ev,ea,cap))
    return out

def neutral_plan(t):
    return min(20,t.budget_cap),max(0,t.dependencies-1)*2,(2 if t.evidence_required else 0)

def candidate_plan(t):
    units=20
    if t.difficulty>=4 or t.uncertainty>.78: units+=8
    elif t.difficulty<=2 and t.uncertainty<.30: units=max(8,units-4)
    units=min(28,units,t.budget_cap)
    coord=0 if t.dependencies<=1 else t.dependencies
    ep=3 if t.evidence_required and t.evidence_availability<.5 else (2 if t.evidence_required else 0)
    return units,coord,ep

def execute(t,plan,semantic,rng):
    units,coord,ep=plan; useful=max(0,units-coord)
    if semantic:
        scar_avoid=t.observed_negative_trigger and t.scar_confidence>=.90
        evidence_focus=t.evidence_required and t.evidence_availability>=.30
        reducible_focus=t.observed_reducible and t.reducibility_confidence>=.85
    else:
        scar_avoid=rng.random()<.20
        evidence_focus=rng.random()<.50
        reducible_focus=rng.random()<.35
    if t.negative_trigger: useful-=1 if scar_avoid else 4
    if t.true_reducible: useful+=2 if reducible_focus else 0
    else: useful-=1 if reducible_focus else 0
    useful=max(0,useful)
    evidence_gain=0
    if t.evidence_required:
        if ep==0: useful=max(0,useful-3)
        else:
            base=round(ep*t.evidence_availability)
            evidence_gain=base + (1 if evidence_focus and base>0 else 0)
    verified=min(units,max(0,useful+evidence_gain))
    cost=float(units+coord+ep)
    target=t.difficulty*4+t.uncertainty*5
    return {"units":units,"coord":coord,"evidence_path":ep,"verified":verified,"cost":cost,"residual":max(0.0,target-verified)}

def metric(rows):
    return {"mean_residual":statistics.mean(x["residual"] for x in rows),"mean_cost":statistics.mean(x["cost"] for x in rows),"mean_verified":statistics.mean(x["verified"] for x in rows),"vcgc_proxy":sum(x["verified"] for x in rows)/sum(x["cost"] for x in rows)}

arms=["A00","A10","A01","A11"]
seed_results=[]; family_rows={a:{f:[] for f in FAMILIES} for a in arms}; mismatch={"neutral_pair":0,"candidate_pair":0}
for seed in SEEDS:
    rows={a:[] for a in arms}; tasks=make_tasks(seed)
    for i,t in enumerate(tasks):
        np=neutral_plan(t); cp=candidate_plan(t)
        a00=execute(t,np,False,random.Random(seed*100000+i)); a01=execute(t,np,True,random.Random(0))
        a10=execute(t,cp,False,random.Random(seed*200000+i)); a11=execute(t,cp,True,random.Random(0))
        for name,val in [("A00",a00),("A10",a10),("A01",a01),("A11",a11)]: rows[name].append(val); family_rows[name][t.family].append(val)
        mismatch["neutral_pair"]=max(mismatch["neutral_pair"],max(abs(a00[k]-a01[k]) for k in ["units","coord","evidence_path","cost"]))
        mismatch["candidate_pair"]=max(mismatch["candidate_pair"],max(abs(a10[k]-a11[k]) for k in ["units","coord","evidence_path","cost"]))
    m={a:metric(rows[a]) for a in arms}
    seed_results.append({"seed":seed,"metrics":m,"semantic_win_neutral":m["A01"]["mean_residual"]<m["A00"]["mean_residual"] and m["A01"]["vcgc_proxy"]>m["A00"]["vcgc_proxy"],"semantic_win_candidate":m["A11"]["mean_residual"]<m["A10"]["mean_residual"] and m["A11"]["vcgc_proxy"]>m["A10"]["vcgc_proxy"]})
aggregate={a:{k:statistics.mean(s["metrics"][a][k] for s in seed_results) for k in seed_results[0]["metrics"][a]} for a in arms}
family_metrics={a:{f:metric(family_rows[a][f]) for f in FAMILIES} for a in arms}
family_semantic_change={f:min((family_metrics["A01"][f]["vcgc_proxy"]-family_metrics["A00"][f]["vcgc_proxy"])/family_metrics["A00"][f]["vcgc_proxy"],(family_metrics["A11"][f]["vcgc_proxy"]-family_metrics["A10"][f]["vcgc_proxy"])/family_metrics["A10"][f]["vcgc_proxy"]) for f in FAMILIES}
w_neutral=sum(s["semantic_win_neutral"] for s in seed_results); w_candidate=sum(s["semantic_win_candidate"] for s in seed_results)
sem_res_neutral=aggregate["A01"]["mean_residual"]<aggregate["A00"]["mean_residual"]; sem_v_neutral=aggregate["A01"]["vcgc_proxy"]>aggregate["A00"]["vcgc_proxy"]
sem_res_candidate=aggregate["A11"]["mean_residual"]<aggregate["A10"]["mean_residual"]; sem_v_candidate=aggregate["A11"]["vcgc_proxy"]>aggregate["A10"]["vcgc_proxy"]
family_gate=all(v>=-.03 for v in family_semantic_change.values()); parity=(mismatch["neutral_pair"]==0 and mismatch["candidate_pair"]==0)
passed=w_neutral>=9 and w_candidate>=9 and sem_res_neutral and sem_v_neutral and sem_res_candidate and sem_v_candidate and family_gate and parity
result={"campaign":"C45","stage":"0250-R1","evidence_ceiling":"E3 synthetic verified simulation","aggregate":aggregate,"semantic_seed_wins":{"neutral_allocator":w_neutral,"candidate_allocator":w_candidate},"resource_pair_mismatch":mismatch,"family_semantic_vcgc_min_relative_change":family_semantic_change,"allocation_effect":{"neutral_semantics_vcgc_delta":aggregate["A10"]["vcgc_proxy"]-aggregate["A00"]["vcgc_proxy"],"candidate_semantics_vcgc_delta":aggregate["A11"]["vcgc_proxy"]-aggregate["A01"]["vcgc_proxy"]},"semantic_effect":{"neutral_allocator_vcgc_delta":aggregate["A01"]["vcgc_proxy"]-aggregate["A00"]["vcgc_proxy"],"candidate_allocator_vcgc_delta":aggregate["A11"]["vcgc_proxy"]-aggregate["A10"]["vcgc_proxy"],"neutral_allocator_residual_delta":aggregate["A01"]["mean_residual"]-aggregate["A00"]["mean_residual"],"candidate_allocator_residual_delta":aggregate["A11"]["mean_residual"]-aggregate["A10"]["mean_residual"]},"family_gate":family_gate,"strict_pair_resource_parity":parity,"r250_r1_gate":passed,"seed_results":seed_results,"next":"rung_500" if passed else "repair_250_r2","claim_limit":"Synthetic factorial causal benchmark only. PASS cannot establish AGI, superintelligence, general intelligence, or autonomous self-improvement."}
blob=json.dumps(result,sort_keys=True,separators=(",",":")); result["sha256"]=hashlib.sha256(blob.encode()).hexdigest()
with open("c45_stage_0250_r1_results.json","w") as f: json.dump(result,f,indent=2)
print(json.dumps(result,indent=2))
