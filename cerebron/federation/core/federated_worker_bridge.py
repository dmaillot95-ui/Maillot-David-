#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,subprocess,sys
from pathlib import Path

CORE=Path(__file__).resolve().parent
WORKER=CORE/'adaptive_shard_worker.py'

def parse_address(address:str):
    # T001/H001/S00 -> physical lane is final shard number modulo 20.
    parts=address.split('/')
    if len(parts)!=3 or not parts[2].startswith('S'):
        raise ValueError(f'invalid federated address: {address}')
    logical_shard=int(parts[2][1:])
    return logical_shard % 20

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--address',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--role',default='PROOF_A')
    p.add_argument('--objective',default='Validate federated execution path. CLAIM<=EVIDENCE.')
    a=p.parse_args()
    lane=parse_address(a.address)
    raw=Path(a.output).with_suffix('.worker.jsonl')
    cmd=[sys.executable,str(WORKER),'--shard',str(lane),'--limit','1','--output',str(raw),'--smoke','--smoke-role',a.role,'--smoke-objective',a.objective]
    cp=subprocess.run(cmd,capture_output=True,text=True)
    rows=[]
    if raw.exists():
        for line in raw.read_text(encoding='utf-8').splitlines():
            if line.strip(): rows.append(json.loads(line))
    result={
      'federated_address':a.address,
      'physical_lane':lane,
      'returncode':cp.returncode,
      'worker_results':rows,
      'worker_stdout_tail':cp.stdout[-3000:],
      'worker_stderr_tail':cp.stderr[-3000:],
    }
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if cp.returncode!=0: raise SystemExit(cp.returncode)

if __name__=='__main__': main()
