#!/usr/bin/env python3
import json, os, socket, urllib.request

RELAYS = {
    "openai_agents": {
        "env": ["OPENAI_API_KEY"],
        "host": "api.openai.com",
        "mode": "managed_agents",
    },
    "gemini_managed_agents": {
        "env": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "host": "generativelanguage.googleapis.com",
        "mode": "managed_agents",
    },
}

def dns_ok(host):
    try:
        socket.getaddrinfo(host, 443)
        return True
    except Exception:
        return False

rows=[]
for rid, cfg in RELAYS.items():
    creds = any(bool(os.getenv(k)) for k in cfg["env"])
    network = dns_ok(cfg["host"])
    # Strict zero-euro gate: no billable/resource-creating call unless explicitly approved.
    can_create_real_agent = False
    reason = "credentials_missing" if not creds else "credentials_present_but_creation_blocked_by_zero_euro_gate"
    rows.append({
        "relay": rid,
        "mode": cfg["mode"],
        "credentials_present": creds,
        "network_reachable": network,
        "real_agent_created": False,
        "can_create_real_agent_now": can_create_real_agent,
        "reason": reason,
        "spend_limit_eur": 0,
        "paid_fallback": False,
    })

out={
    "engine":"CEREBRON_AGENT_RELAY_PROBE_V1",
    "claim_rule":"REAL_AGENT_CREATED only if provider returns a real agent id",
    "rows":rows,
    "real_remote_agents_created":0,
}
print(json.dumps(out, ensure_ascii=False))
open("relay-probe.json","w",encoding="utf-8").write(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
