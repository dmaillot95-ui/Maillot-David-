#!/usr/bin/env python3
"""CEREBRON Ω Physical Node.

Autonomous zero-euro node runtime for a real Linux PC/server.
Provides a persistent SQLite task DAG, local routing, deterministic CPU calculation,
local LLM execution, child-task spawning, capability inventory and evidence ledger.
No paid provider is ever selected by this runtime.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
import platform
import sqlite3
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(os.getenv("CEREBRON_NODE_ROOT", str(Path.home()/".cerebron-node")))
DB = ROOT / "node.db"
EVIDENCE = ROOT / "evidence.jsonl"
NODE_ID_FILE = ROOT / "node-id"
SPEND_LIMIT_EUR = 0

ALLOWED_FUNCS = {k: getattr(math, k) for k in ["sqrt","sin","cos","tan","log","log10","exp","floor","ceil","fabs"]}
ALLOWED_CONSTS = {"pi": math.pi, "e": math.e}


def init_fs() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    if not NODE_ID_FILE.exists():
        raw = f"{platform.node()}:{uuid.uuid4()}"
        NODE_ID_FILE.write_text("PN-" + hashlib.sha256(raw.encode()).hexdigest()[:16], encoding="utf-8")
    with sqlite3.connect(DB) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS tasks(
          id TEXT PRIMARY KEY, parent_id TEXT, kind TEXT NOT NULL, payload TEXT NOT NULL,
          priority INTEGER NOT NULL DEFAULT 100, state TEXT NOT NULL DEFAULT 'PENDING',
          result TEXT, created REAL NOT NULL, updated REAL NOT NULL, attempts INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_tasks_ready ON tasks(state,priority,created);
        """)


def node_id() -> str:
    init_fs(); return NODE_ID_FILE.read_text(encoding="utf-8").strip()


def capabilities() -> dict[str, Any]:
    return {
      "node_id": node_id(), "physical_host": platform.node(), "machine": platform.machine(),
      "os": platform.platform(), "cpu_count": os.cpu_count() or 1,
      "python": platform.python_version(), "spend_limit_eur": 0, "paid_fallback": False,
      "engines": {"cpu_calculator": True, "local_llm": _local_llm_available(), "task_dag": True, "sqlite_queue": True},
    }


def evidence(event: str, data: dict[str, Any]) -> None:
    rec = {"ts": time.time(), "node_id": node_id(), "event": event, **data}
    line = json.dumps(rec, ensure_ascii=False, sort_keys=True)
    rec["sha256"] = hashlib.sha256(line.encode()).hexdigest()
    with EVIDENCE.open("a", encoding="utf-8") as f: f.write(json.dumps(rec, ensure_ascii=False)+"\n")


def _local_llm_available() -> bool:
    try:
        import torch, transformers  # noqa
        return True
    except Exception:
        return False


def enqueue(kind: str, payload: Any, priority: int=100, parent_id: str|None=None) -> str:
    init_fs(); tid = "T-" + uuid.uuid4().hex[:16]; now=time.time()
    with sqlite3.connect(DB) as c:
        c.execute("INSERT INTO tasks(id,parent_id,kind,payload,priority,state,created,updated) VALUES(?,?,?,?,?,'PENDING',?,?)",
                  (tid,parent_id,kind,json.dumps(payload,ensure_ascii=False),priority,now,now))
    evidence("TASK_ENQUEUED", {"task_id":tid,"parent_id":parent_id,"kind":kind,"priority":priority})
    return tid


def _safe_calc(expr: str) -> Any:
    tree=ast.parse(expr, mode="eval")
    allowed=(ast.Expression,ast.Constant,ast.BinOp,ast.UnaryOp,ast.Add,ast.Sub,ast.Mult,ast.Div,ast.FloorDiv,ast.Mod,ast.Pow,ast.USub,ast.UAdd,ast.Call,ast.Name,ast.Load)
    for n in ast.walk(tree):
        if not isinstance(n, allowed): raise ValueError(f"blocked syntax: {type(n).__name__}")
        if isinstance(n, ast.Name) and n.id not in ALLOWED_FUNCS and n.id not in ALLOWED_CONSTS: raise ValueError(f"blocked name: {n.id}")
        if isinstance(n, ast.Call) and (not isinstance(n.func,ast.Name) or n.func.id not in ALLOWED_FUNCS): raise ValueError("blocked function")
    return eval(compile(tree,"<calc>","eval"), {"__builtins__":{}}, {**ALLOWED_FUNCS,**ALLOWED_CONSTS})


def execute(kind: str, payload: Any) -> dict[str, Any]:
    if kind == "CALC":
        expr = payload["expr"] if isinstance(payload,dict) else str(payload)
        return {"ok":True,"engine":"cpu_calculator","value":_safe_calc(expr),"expr":expr,"cost_eur":0}
    if kind == "LLM":
        if not _local_llm_available(): return {"ok":False,"engine":"local_llm","error":"LOCAL_LLM_RUNTIME_UNAVAILABLE","cost_eur":0}
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
        from providers.local_cpu_llm import invoke_local_cpu
        prompt = payload.get("prompt","") if isinstance(payload,dict) else str(payload)
        r=invoke_local_cpu(prompt); r["cost_eur"]=0; return r
    if kind == "FANOUT":
        children=payload.get("children",[]) if isinstance(payload,dict) else []
        return {"ok":True,"engine":"task_factory","children":children,"cost_eur":0}
    return {"ok":False,"error":"UNKNOWN_TASK_KIND","kind":kind,"cost_eur":0}


def run_one() -> dict[str,Any]|None:
    init_fs()
    with sqlite3.connect(DB) as c:
        row=c.execute("SELECT id,parent_id,kind,payload FROM tasks WHERE state='PENDING' ORDER BY priority ASC,created ASC LIMIT 1").fetchone()
        if not row: return None
        tid,parent,kind,payload_s=row; now=time.time()
        c.execute("UPDATE tasks SET state='RUNNING',attempts=attempts+1,updated=? WHERE id=?",(now,tid))
    payload=json.loads(payload_s); started=time.time()
    try:
        result=execute(kind,payload)
        state="COMPLETED" if result.get("ok") else "FAILED"
        if kind=="FANOUT" and result.get("ok"):
            for child in result["children"]:
                enqueue(child["kind"],child.get("payload",{}),int(child.get("priority",100)),tid)
    except Exception as e:
        result={"ok":False,"error_type":type(e).__name__,"error":repr(e),"cost_eur":0}; state="FAILED"
    result["elapsed_s"]=round(time.time()-started,4)
    with sqlite3.connect(DB) as c:
        c.execute("UPDATE tasks SET state=?,result=?,updated=? WHERE id=?",(state,json.dumps(result,ensure_ascii=False),time.time(),tid))
    evidence("TASK_FINISHED", {"task_id":tid,"parent_id":parent,"kind":kind,"state":state,"result":result})
    return {"task_id":tid,"kind":kind,"state":state,"result":result}


def status() -> dict[str,Any]:
    init_fs()
    with sqlite3.connect(DB) as c:
        counts=dict(c.execute("SELECT state,COUNT(*) FROM tasks GROUP BY state").fetchall())
    return {"node":capabilities(),"tasks":counts,"evidence":str(EVIDENCE)}


def main() -> int:
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("init"); sub.add_parser("status"); sub.add_parser("run-once")
    d=sub.add_parser("daemon"); d.add_argument("--sleep",type=float,default=1.0)
    e=sub.add_parser("enqueue"); e.add_argument("kind",choices=["CALC","LLM","FANOUT"]); e.add_argument("payload"); e.add_argument("--priority",type=int,default=100)
    a=p.parse_args(); init_fs()
    if a.cmd=="init": out=capabilities()
    elif a.cmd=="status": out=status()
    elif a.cmd=="enqueue": out={"task_id":enqueue(a.kind,json.loads(a.payload),a.priority)}
    elif a.cmd=="run-once": out=run_one() or {"idle":True}
    else:
        evidence("DAEMON_STARTED", capabilities())
        try:
            while True:
                if run_one() is None: time.sleep(a.sleep)
        except KeyboardInterrupt: return 0
    print(json.dumps(out,indent=2,ensure_ascii=False)); return 0

if __name__=="__main__": raise SystemExit(main())
