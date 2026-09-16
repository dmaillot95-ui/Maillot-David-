#!/usr/bin/env python3
import json, os, re, time
from collections import Counter
from cerebron.providers.local_cpu_llm import invoke_local_cpu

TASKS = [
    ("Compute 37*41. Return only the integer.", "1517", "num"),
    ("Compute gcd(756,1134). Return only the integer.", "378", "num"),
    ("Sequence: 3, 8, 15, 24, 35, ?. Return only the next integer.", "48", "num"),
    ("If all K are L and no L are M, can any K be M? Return only yes or no.", "no", "word"),
    ("Convert hexadecimal 2F to decimal. Return only the integer.", "47", "num"),
    ("Compute 54321 mod 113. Return only the integer remainder.", "81", "num"),
    ("How many unordered pairs can be chosen from 9 objects? Return only the integer.", "36", "num"),
    ("A train travels 315 km in 4.5 hours at constant speed. Return km/h as an integer.", "70", "num"),
    ("Is 437 prime or composite? Return only prime or composite.", "composite", "word"),
    ("If P>Q, Q>R, and R>S, which is second greatest: P,Q,R,S? Return only the letter.", "q", "word"),
    ("Compute 2^10 + 3^4. Return only the integer.", "1105", "num"),
    ("A bag has 5 red, 3 blue, 2 green balls. Probability numerator for drawing red over denominator 10, reduced. Return only numerator/denominator.", "1/2", "frac"),
]

MINOR_A = os.getenv("MINOR_A", "HuggingFaceTB/SmolLM2-135M-Instruct")
MINOR_B = os.getenv("MINOR_B", "HuggingFaceTB/SmolLM2-360M-Instruct")
MAJOR = os.getenv("MAJOR", "Qwen/Qwen2.5-1.5B-Instruct")
OUT = os.getenv("OUT", "out/cascade-alchemy-report.json")


def extract(answer, kind):
    s=(answer or "").strip().lower()
    if kind=="num":
        m=re.search(r"-?\d+",s); return m.group(0) if m else ""
    if kind=="frac":
        m=re.search(r"\d+\s*/\s*\d+",s); return m.group(0).replace(" ","") if m else ""
    if "composite" in s: return "composite"
    if re.search(r"\bprime\b",s): return "prime"
    if re.search(r"\byes\b",s): return "yes"
    if re.search(r"\bno\b",s): return "no"
    m=re.search(r"\b([pqrs])\b",s)
    return m.group(1) if m else (s.split()[0].strip(".,:;!?") if s else "")


def call(model,prompt,kind):
    old=os.environ.get("CEREBRON_LOCAL_CPU_MODEL")
    os.environ["CEREBRON_LOCAL_CPU_MODEL"]=model
    r=invoke_local_cpu(prompt,max_new_tokens=48)
    if old is None: os.environ.pop("CEREBRON_LOCAL_CPU_MODEL",None)
    else: os.environ["CEREBRON_LOCAL_CPU_MODEL"]=old
    return {"pred":extract(r.get("answer",""),kind),"raw":r.get("answer",""),"elapsed_s":r.get("elapsed_s"),"ok":r.get("ok")}

rows=[]; started=time.time(); major_calls=0
for i,(prompt,expected,kind) in enumerate(TASKS,1):
    a=call(MINOR_A,prompt,kind)
    b=call(MINOR_B,prompt,kind)
    # Cascade rule: agreement between heterogeneous minors is accepted; disagreement escalates.
    if a["pred"] and a["pred"]==b["pred"]:
        cascade_pred=a["pred"]; escalated=False; major=None
    else:
        major=call(MAJOR,prompt,kind); major_calls+=1; cascade_pred=major["pred"]; escalated=True
    # Major-only baseline.
    base=call(MAJOR,prompt,kind)
    # Call-count control: three minor calls, majority if any; no major.
    c=call(MINOR_B,prompt,kind)
    votes=[x for x in [a["pred"],b["pred"],c["pred"]] if x]
    cc=Counter(votes)
    matched_pred=cc.most_common(1)[0][0] if cc else ""
    rows.append({"task":i,"expected":expected,"minor_a":a["pred"],"minor_b":b["pred"],"escalated":escalated,
                 "cascade_pred":cascade_pred,"cascade_correct":cascade_pred==expected,
                 "major_only_pred":base["pred"],"major_only_correct":base["pred"]==expected,
                 "three_minor_pred":matched_pred,"three_minor_correct":matched_pred==expected})

report={
 "schema":"cerebron-cascade-alchemy-v1",
 "tasks":len(rows),
 "models":{"minor_a":MINOR_A,"minor_b":MINOR_B,"major":MAJOR},
 "cascade_score":sum(r["cascade_correct"] for r in rows),
 "major_only_score":sum(r["major_only_correct"] for r in rows),
 "three_minor_score":sum(r["three_minor_correct"] for r in rows),
 "major_calls_in_cascade":major_calls,
 "major_call_savings_vs_major_every_task":len(rows)-major_calls,
 "escalation_rate":major_calls/len(rows),
 "elapsed_total_s":round(time.time()-started,3),
 "rows":rows,
 "controls_note":"three-minor is call-count matched only, not FLOP-matched; parameter counts differ",
 "spend_limit_eur":0,"paid_fallback":False,"api_key_used":False,
 "claim_superintelligence":False
}
os.makedirs(os.path.dirname(OUT),exist_ok=True)
json.dump(report,open(OUT,"w"),indent=2)
print(json.dumps(report,indent=2))
assert report["spend_limit_eur"]==0 and not report["paid_fallback"] and not report["api_key_used"]
