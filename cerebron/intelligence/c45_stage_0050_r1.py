#!/usr/bin/env python3
import json, hashlib, random, statistics
from dataclasses import dataclass

SEEDS=[20261501,20261502,20261503,20261504,20261505,20261506,20261507,20261508,20261509]
FAMILIES=["false_simple","scar_inversion","mixed_shift","high_uncertainty","dependency_spike","tight_budget"]

@dataclass
class Task:
    family:str
    difficulty:int
    dependencies:int
    uncertainty:float
    true_reducible:bool
    observed_reducible:bool
    reducibility_confidence:float
    duplicate_fraction:float
    observed_duplicate_fraction:float
    negative_trigger:bool
    observed_negative_trigger:bool
    scar_confidence:float
    evidence_required:bool
    budget_cap:int


def make_tasks(seed,n_per_family=70):
    r=random.Random(seed); out=[]
    for fam in FAMILIES:
        for _ in range(n_per_family):
            d=r.randint(1,5); dep=r.randint(0,4); u=r.random()
            tr=r.random()<0.35; obs=tr; rconf=r.uniform(.55,.98)
            dup=r.choice([0.0,0.1,0.2,0.3]); odup=dup
            neg=r.random()<0.18; oneg=neg; sconf=r.uniform(.55,.98)
            ev=r.random()<0.70; cap=30
            if fam=="false_simple":
                if r.random()<0.70: obs=not tr
                rconf=r.uniform(.45,.92)
            elif fam=="scar_inversion":
                if r.random()<0.65: oneg=not neg
                sconf=r.uniform(.45,.92)
            elif fam=="mixed_shift":
                if r.random()<0.45: obs=not tr
                if r.random()<0.45: oneg=not neg
                odup=max(0.0,min(.4,dup+r.choice([-.2,.2,.3])))
            elif fam=="high_uncertainty":
                u=r.uniform(.70,1.0); ev=True
            elif fam=="dependency_spike":
                dep=r.randint(3,7)
            elif fam=="tight_budget":
                cap=r.choice([12,14,16,18])
            out.append(Task(fam,d,dep,u,tr,obs,rconf,dup,odup,neg,oneg,sconf,ev,cap))
    return out


def finalize(task,units,coord,evidence_path,dedupe_fraction,scar_avoid=False,cost_override=None):
    units=max(4,min(task.budget_cap,units))
    effective=max(0,round(units*(1-dedupe_fraction)))
    useful=max(0,effective-coord)
    if task.negative_trigger:
        useful-=1 if scar_avoid else 4
    useful=max(0,useful)
    verified=max(0,useful-(3 if task.evidence_required and evidence_path==0 else 0))
    if task.evidence_required and evidence_path>0 and verified>0:
        verified=min(effective,verified+evidence_path)
    cost=units+coord+evidence_path if cost_override is None else cost_override
    target=task.difficulty*4+task.uncertainty*5
    residual=max(0.0,target-verified)
    return {"units":units,"verified":verified,"cost":float(cost),"residual":residual}


def baseline(task):
    units=min(20,task.budget_cap); coord=max(0,task.dependencies-1)*2
    return finalize(task,units,coord,0,task.duplicate_fraction,False)


def candidate(task,ablate=None):
    # Repair 1: simplify only on a high-confidence cue and only when the task itself is not hard/uncertain.
    conservative_simple=(task.observed_reducible and task.reducibility_confidence>=.85 and task.difficulty<=3 and task.uncertainty<.60)
    units=20
    if ablate!="conservative_simple" and conservative_simple: units=12
    if ablate!="adaptive_compiler":
        if task.difficulty>=4 or task.uncertainty>.78: units+=8
        elif task.difficulty<=2 and task.uncertainty<.30: units=max(8,units-4)
    units=min(28,units)
    # Repair 2: scar signal never shrinks total budget; it only avoids part of the known-bad branch when confidence is high.
    scar_avoid=(ablate!="scar_guard" and task.observed_negative_trigger and task.scar_confidence>=.88)
    coord=(max(0,task.dependencies-1)*2) if ablate=="router" else (0 if task.dependencies<=1 else task.dependencies)
    dedupe=task.observed_duplicate_fraction
    evidence_path=0 if ablate=="verification_reservation" else (2 if task.evidence_required else 0)
    return finalize(task,units,coord,evidence_path,dedupe,scar_avoid)


def exact_cost_sham(task,target_cost,rng):
    # Random allocation/control policy, but accounting cost is exactly matched to candidate per task.
    units=max(4,min(task.budget_cap,rng.choice([8,12,16,20,24,28])))
    coord=rng.choice([0,max(0,task.dependencies),max(0,task.dependencies-1)*2])
    evidence_path=2 if rng.random()<0.70 else 0
    dedupe=rng.choice([0.0,0.1,0.2,0.3])
    scar_avoid=rng.random()<0.25
    return finalize(task,units,coord,evidence_path,dedupe,scar_avoid,cost_override=target_cost)


def metric(rows):
    n=len(rows)
    return {"mean_residual":sum(x["residual"] for x in rows)/n,
            "mean_cost":sum(x["cost"] for x in rows)/n,
            "mean_verified":sum(x["verified"] for x in rows)/n,
            "vcgc_proxy":sum(x["verified"] for x in rows)/max(1e-12,sum(x["cost"] for x in rows))}

CONDS=["baseline","candidate","cost_matched_sham","ablate_conservative_simple","ablate_scar_guard","ablate_adaptive_compiler","ablate_verification_reservation","ablate_router"]
seed_results=[]; fam_acc={c:{f:[] for f in FAMILIES} for c in CONDS}; max_cost_mismatch=0.0
for seed in SEEDS:
    tasks=make_tasks(seed); rows={c:[] for c in CONDS}
    for i,t in enumerate(tasks):
        b=baseline(t); c=candidate(t); s=exact_cost_sham(t,c["cost"],random.Random(seed*100000+i))
        rows["baseline"].append(b); rows["candidate"].append(c); rows["cost_matched_sham"].append(s)
        max_cost_mismatch=max(max_cost_mismatch,abs(c["cost"]-s["cost"]))
        rows["ablate_conservative_simple"].append(candidate(t,"conservative_simple"))
        rows["ablate_scar_guard"].append(candidate(t,"scar_guard"))
        rows["ablate_adaptive_compiler"].append(candidate(t,"adaptive_compiler"))
        rows["ablate_verification_reservation"].append(candidate(t,"verification_reservation"))
        rows["ablate_router"].append(candidate(t,"router"))
    m={c:metric(rows[c]) for c in CONDS}
    seed_results.append({"seed":seed,"metrics":m,
        "beats_baseline_both":m["candidate"]["mean_residual"]<m["baseline"]["mean_residual"] and m["candidate"]["vcgc_proxy"]>m["baseline"]["vcgc_proxy"],
        "beats_sham_residual":m["candidate"]["mean_residual"]<m["cost_matched_sham"]["mean_residual"],
        "beats_sham_verified":m["candidate"]["mean_verified"]>m["cost_matched_sham"]["mean_verified"]})
    for f in FAMILIES:
        idx=[j for j,t in enumerate(tasks) if t.family==f]
        for c in CONDS: fam_acc[c][f].extend(rows[c][j] for j in idx)

aggregate={c:{k:statistics.mean(sr["metrics"][c][k] for sr in seed_results) for k in seed_results[0]["metrics"][c]} for c in CONDS}
family_metrics={c:{f:metric(fam_acc[c][f]) for f in FAMILIES} for c in CONDS}
family_change={f:(family_metrics["candidate"][f]["vcgc_proxy"]-family_metrics["baseline"][f]["vcgc_proxy"])/family_metrics["baseline"][f]["vcgc_proxy"] for f in FAMILIES}
ablation_effects={}
for c in CONDS:
    if c.startswith("ablate_"):
        ablation_effects[c]={"residual_delta_vs_candidate":aggregate[c]["mean_residual"]-aggregate["candidate"]["mean_residual"],
                             "vcgc_delta_vs_candidate":aggregate[c]["vcgc_proxy"]-aggregate["candidate"]["vcgc_proxy"]}

wins_base=sum(x["beats_baseline_both"] for x in seed_results)
wins_sham_res=sum(x["beats_sham_residual"] for x in seed_results)
wins_sham_ver=sum(x["beats_sham_verified"] for x in seed_results)
pos_ab=sum(v["residual_delta_vs_candidate"]>0.01 or v["vcgc_delta_vs_candidate"]<-0.001 for v in ablation_effects.values())
family_gate=all(v>=-.05 for v in family_change.values())
passed=(wins_base>=7 and wins_sham_res>=6 and wins_sham_ver>=6 and family_gate and pos_ab>=3 and max_cost_mismatch<=1e-12)

result={"campaign":"C45","stage":"0050-R1","planned_units":50,"completed_units":50,
        "baseline":"frozen C43/C44 pre-campaign baseline","evidence_ceiling":"E3 synthetic verified simulation",
        "aggregate":aggregate,"family_metrics":family_metrics,"family_vcgc_relative_change_candidate_vs_baseline":family_change,
        "ablation_effects":ablation_effects,"seed_results":seed_results,"seed_wins_vs_baseline_both":wins_base,
        "seed_wins_vs_cost_matched_sham_residual":wins_sham_res,"seed_wins_vs_cost_matched_sham_verified":wins_sham_ver,
        "positive_ablation_signal_count":pos_ab,"family_robustness_gate":family_gate,"max_candidate_sham_cost_mismatch":max_cost_mismatch,
        "r50_r1_gate":passed,"next":"rung_100" if passed else "repair_again",
        "claim_limit":"Synthetic repaired stress test only. Passing authorizes progression to rung 100; it is not evidence of AGI or superintelligence."}
blob=json.dumps(result,sort_keys=True,separators=(",",":")); result["sha256"]=hashlib.sha256(blob.encode()).hexdigest()
with open("c45_stage_0050_r1_results.json","w") as f: json.dump(result,f,indent=2)
print(json.dumps(result,indent=2))
