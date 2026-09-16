#!/usr/bin/env python3
"""Live probes for CEREBRON zero-euro routes already implemented in code."""
from __future__ import annotations
import json, os, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
CORE=ROOT/'cerebron'/'federation'/'core'
sys.path.insert(0,str(CORE))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from provider_bank import build_bank
from provider_adapters import invoke_groq, invoke_cloudflare
from provider_adapters_extra import invoke_gemini, invoke_openrouter, invoke_mistral

LIVE={
 'google_gemini': lambda: invoke_gemini('Reply only OK',max_tokens=8),
 'groq': lambda: invoke_groq('Reply only OK',max_tokens=8),
 'openrouter': lambda: invoke_openrouter('Reply only OK',max_tokens=8),
 'cloudflare_workers_ai': lambda: invoke_cloudflare('Reply only OK',max_tokens=8),
 'mistral': lambda: invoke_mistral('Reply only OK',max_tokens=8),
}

def main():
    bank=build_bank(); results=[]
    for p in bank['providers']:
        pid=p['id']
        if not p['routable']:
            results.append({'id':pid,'probe':'SKIPPED','status':p['status'],'runtime':p['runtime'],'reason':p['probe_reason']})
            continue
        if pid not in LIVE:
            results.append({'id':pid,'probe':'AVAILABLE_NOT_LIVE_TESTED','status':p['status'],'runtime':p['runtime'],'reason':p['probe_reason']})
            continue
        r=LIVE[pid]()
        state='LIVE_OK' if r.ok else ('QUOTA_LIMITED' if r.error_type=='QUOTA' else 'LIVE_FAILED')
        results.append({'id':pid,'probe':state,'provider':r.provider,'model':r.model,'status_code':r.status_code,'error_type':r.error_type,'retry_after':r.retry_after})
    summary={
      'engine':'CEREBRON_PROVIDER_PROBE_V1','provider_count':100,'spend_limit_eur':0,'paid_fallback':False,
      'live_ok':sum(x['probe']=='LIVE_OK' for x in results),
      'quota_limited':sum(x['probe']=='QUOTA_LIMITED' for x in results),
      'available_not_live_tested':sum(x['probe']=='AVAILABLE_NOT_LIVE_TESTED' for x in results),
      'results':results
    }
    out=Path(os.getenv('CEREBRON_PROVIDER_PROBE_OUT','cerebron/providers/provider-probe-runtime.json'))
    out.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='results'},ensure_ascii=False))

if __name__=='__main__': main()
