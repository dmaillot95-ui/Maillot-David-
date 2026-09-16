#!/usr/bin/env python3
import argparse, json, os, time, uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parent
CFG=json.loads((ROOT/'federation-12.json').read_text(encoding='utf-8'))

def get_farm(fid):
    for f in CFG['farms']:
        if f['id']==fid:
            return f
    raise SystemExit(f'unknown farm {fid}')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--farm',required=True)
    ap.add_argument('--workers',type=int,default=4)
    ap.add_argument('--mission',default='health-check')
    a=ap.parse_args()
    farm=get_farm(a.farm)
    count=max(1,min(a.workers,20))
    workers=[]
    for i in range(count):
        workers.append({
          'worker_id':f"{a.farm}-W-{uuid.uuid4().hex[:10]}",
          'slot':i,
          'specialization':farm['specialization'],
          'mission':a.mission,
          'status':'READY',
          'logical_worker':True,
          'physical_runner_id':os.getenv('RUNNER_NAME') or None
        })
    out={
      'engine':'CEREBRON_FARM_CONTROLLER_V1',
      'farm':farm,
      'mission':a.mission,
      'workers_created':len(workers),
      'workers':workers,
      'github_run_id':os.getenv('GITHUB_RUN_ID'),
      'spend_limit_eur':0,
      'paid_fallback':False,
      'timestamp':time.time(),
      'claim':'workers are logical children of this farm; a GitHub Actions matrix job is required for distinct physical runners'
    }
    print(json.dumps(out,ensure_ascii=False))

if __name__=='__main__': main()
