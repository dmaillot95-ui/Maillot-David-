#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

from federated_multiwave_orchestrator import load_json, save_json, mark_terminal


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--state',required=True)
    p.add_argument('--artifacts',required=True)
    p.add_argument('--report',required=True)
    a=p.parse_args()

    state_path=Path(a.state)
    state=load_json(state_path,{})
    completed=[]; failed=[]; rows=[]
    for f in sorted(Path(a.artifacts).rglob('*.json')):
        try:
            obj=json.loads(f.read_text(encoding='utf-8'))
        except Exception as e:
            rows.append({'file':str(f),'status':'PARSE_ERROR','error':str(e)})
            continue
        aid=obj.get('assignment_id')
        rc=int(obj.get('returncode',1))
        worker_results=obj.get('worker_results') or []
        terminal_statuses=[str(r.get('execution_status') or r.get('status') or 'UNKNOWN') for r in worker_results if isinstance(r,dict)]
        terminal_ok=rc==0 and any(s=='COMPLETED' for s in terminal_statuses)
        if aid:
            (completed if terminal_ok else failed).append(aid)
        rows.append({'file':str(f),'assignment_id':aid,'returncode':rc,'terminal_statuses':terminal_statuses,'terminal_ok':terminal_ok})

    mark_terminal(state, completed, 'COMPLETED')
    mark_terminal(state, failed, 'FAILED')
    save_json(state_path,state)
    report={
      'schema':'cerebron-orchestrated-wave-commit-v2',
      'completed':completed,
      'failed':failed,
      'completed_count':len(completed),
      'failed_count':len(failed),
      'state_inflight':len(state.get('inflight',{})),
      'state_completed':len(state.get('completed',{})),
      'state_failed':len(state.get('failed',{})),
      'rows':rows,
    }
    Path(a.report).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__': main()
