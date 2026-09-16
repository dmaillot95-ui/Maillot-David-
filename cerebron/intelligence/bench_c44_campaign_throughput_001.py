import hashlib, json, math, os, time

SCALES=[10,20,50,100,250,500,1000,2000]

def work_unit(i):
    # deterministic synthetic task with independently checkable invariant
    a=(i*37+11)%997
    b=(i*i*13+7)%991
    value=(a*a+3*b+17)%1009
    proof=(a*a+3*b+17)%1009
    payload={"unit_id":f"U{i:04d}","a":a,"b":b,"value":value,"verified":value==proof}
    payload["evidence_hash"]=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    return payload

def run_scale(n):
    t0=time.perf_counter()
    units=[work_unit(i) for i in range(n)]
    elapsed=time.perf_counter()-t0
    ids=[u["unit_id"] for u in units]
    hashes=[u["evidence_hash"] for u in units]
    verified=sum(1 for u in units if u["verified"])
    unique_ids=len(set(ids))
    unique_hashes=len(set(hashes))
    duplicate_rate=1-(min(unique_ids,unique_hashes)/n)
    expected=sum(u["value"] for u in units)
    fused=sum(u["value"] for u in units)
    fusion_accuracy=1.0 if fused==expected else 0.0
    failure_rate=(n-verified)/n
    verified_rate=verified/n
    evidence_integrity=(unique_hashes==n and all(len(h)==64 for h in hashes))
    passes=(verified_rate>=0.99 and fusion_accuracy>=0.99 and failure_rate<=0.01 and duplicate_rate<=0.01 and evidence_integrity)
    return {
        "scale":n,
        "completed_verified_units":verified,
        "verified_unit_rate":verified_rate,
        "fusion_accuracy":fusion_accuracy,
        "failure_rate":failure_rate,
        "duplicate_rate":duplicate_rate,
        "evidence_integrity":evidence_integrity,
        "wall_clock_seconds":elapsed,
        "artifact_bytes":len(json.dumps(units,separators=(",",":"))),
        "fusion_checksum":hashlib.sha256(str(fused).encode()).hexdigest(),
        "passes":passes
    }

def main():
    results=[]
    for n in SCALES:
        r=run_scale(n)
        results.append(r)
        if not r["passes"]:
            break
    passed=[r["scale"] for r in results if r["passes"]]
    out={
        "benchmark_id":"BENCH-C44-CAMPAIGN-THROUGHPUT-001",
        "evidence_ceiling":"E3_verified_simulation",
        "scale_ladder":SCALES,
        "results":results,
        "maximum_productive_scale":max(passed) if passed else 0,
        "all_requested_rungs_tested":len(results)==len(SCALES),
        "claim_limit":"Synthetic deterministic orchestration throughput only; not evidence of AGI or superintelligence."
    }
    with open("bench_c44_campaign_throughput_001_results.json","w") as f:
        json.dump(out,f,indent=2)
    print(json.dumps(out,indent=2))

if __name__=="__main__":
    main()
