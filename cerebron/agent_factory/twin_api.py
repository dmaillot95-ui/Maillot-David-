#!/usr/bin/env python3
"""CEREBRON Ω Agent Digital Twin API.

A zero-paid-fallback, provider-neutral agent control plane. It reproduces the
useful orchestration surface of managed-agent relays without pretending to copy
proprietary models. Agents and tasks are persisted in SQLite.

Proof backend included here: deterministic CALC tasks. External/local AI engines
can be attached later behind the same API contract.
"""
from __future__ import annotations

import argparse
import ast
import json
import math
import os
import sqlite3
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

DB_PATH = Path(os.getenv("CEREBRON_TWIN_DB", "cerebron-agent-twin.db"))
SPEND_LIMIT_EUR = 0
PAID_FALLBACK = False
DB_LOCK = threading.Lock()

ALLOWED_FUNCS = {
    "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "log": math.log, "log10": math.log10, "exp": math.exp,
    "floor": math.floor, "ceil": math.ceil, "fabs": math.fabs,
}
ALLOWED_CONSTS = {"pi": math.pi, "e": math.e}


def now() -> float:
    return time.time()


def uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


def db() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DB_LOCK, db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS agents(
          id TEXT PRIMARY KEY,
          parent_id TEXT,
          name TEXT NOT NULL,
          specialization TEXT NOT NULL,
          engine TEXT NOT NULL,
          status TEXT NOT NULL,
          created_at REAL NOT NULL,
          heartbeat_at REAL NOT NULL,
          spend_limit_eur REAL NOT NULL,
          paid_fallback INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tasks(
          id TEXT PRIMARY KEY,
          agent_id TEXT NOT NULL,
          kind TEXT NOT NULL,
          payload TEXT NOT NULL,
          status TEXT NOT NULL,
          result TEXT,
          error TEXT,
          created_at REAL NOT NULL,
          completed_at REAL
        );
        """)


def rowdict(row):
    return dict(row) if row is not None else None


def safe_eval(expr: str):
    tree = ast.parse(expr, mode="eval")

    def ev(node):
        if isinstance(node, ast.Expression): return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)): return node.value
        if isinstance(node, ast.Name) and node.id in ALLOWED_CONSTS: return ALLOWED_CONSTS[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            v = ev(node.operand); return v if isinstance(node.op, ast.UAdd) else -v
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)):
            a, b = ev(node.left), ev(node.right)
            if isinstance(node.op, ast.Add): return a + b
            if isinstance(node.op, ast.Sub): return a - b
            if isinstance(node.op, ast.Mult): return a * b
            if isinstance(node.op, ast.Div): return a / b
            if isinstance(node.op, ast.FloorDiv): return a // b
            if isinstance(node.op, ast.Mod): return a % b
            if isinstance(node.op, ast.Pow):
                if abs(b) > 1000: raise ValueError("exponent too large")
                return a ** b
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ALLOWED_FUNCS:
            return ALLOWED_FUNCS[node.func.id](*[ev(a) for a in node.args])
        raise ValueError(f"unsupported expression: {ast.dump(node, include_attributes=False)}")

    return ev(tree)


def create_agent(data: dict, parent_id: str | None = None) -> dict:
    aid = uid("AG")
    t = now()
    name = str(data.get("name") or aid)
    specialization = str(data.get("specialization") or "general")
    engine = str(data.get("engine") or "deterministic_calc")
    with DB_LOCK, db() as con:
        con.execute(
            "INSERT INTO agents VALUES(?,?,?,?,?,?,?,?,?,?)",
            (aid, parent_id, name, specialization, engine, "READY", t, t, SPEND_LIMIT_EUR, int(PAID_FALLBACK)),
        )
    return get_agent(aid)


def get_agent(aid: str):
    with db() as con:
        row = con.execute("SELECT * FROM agents WHERE id=?", (aid,)).fetchone()
    d = rowdict(row)
    if d:
        d["paid_fallback"] = bool(d["paid_fallback"])
    return d


def stop_agent(aid: str):
    with DB_LOCK, db() as con:
        cur = con.execute("UPDATE agents SET status='STOPPED', heartbeat_at=? WHERE id=?", (now(), aid))
    return cur.rowcount > 0


def spawn_agents(parent_id: str, data: dict):
    if not get_agent(parent_id): return None
    count = max(1, min(int(data.get("count", 1)), 100))
    spec = str(data.get("specialization") or "general")
    engine = str(data.get("engine") or "deterministic_calc")
    return [create_agent({"name": f"child-{i}", "specialization": spec, "engine": engine}, parent_id) for i in range(count)]


def submit_task(aid: str, data: dict):
    agent = get_agent(aid)
    if not agent or agent["status"] != "READY": return None
    tid = uid("TK")
    kind = str(data.get("kind") or "CALC").upper()
    payload = data.get("payload", {})
    t = now()
    with DB_LOCK, db() as con:
        con.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?)", (tid, aid, kind, json.dumps(payload), "RUNNING", None, None, t, None))
        con.execute("UPDATE agents SET heartbeat_at=? WHERE id=?", (t, aid))
    try:
        if kind == "CALC":
            expr = str(payload.get("expression", ""))
            result = {"expression": expr, "value": safe_eval(expr), "engine": "deterministic_calc"}
        elif kind == "ECHO":
            result = {"echo": payload, "engine": "echo"}
        else:
            raise ValueError(f"unsupported task kind {kind}")
        status, error = "COMPLETED", None
    except Exception as exc:
        result, status, error = None, "FAILED", f"{type(exc).__name__}: {exc}"
    with DB_LOCK, db() as con:
        con.execute("UPDATE tasks SET status=?,result=?,error=?,completed_at=? WHERE id=?",
                    (status, json.dumps(result) if result is not None else None, error, now(), tid))
    return get_task(tid)


def get_task(tid: str):
    with db() as con:
        row = con.execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone()
    d = rowdict(row)
    if d:
        d["payload"] = json.loads(d["payload"])
        d["result"] = json.loads(d["result"]) if d["result"] else None
    return d


def agent_results(aid: str):
    with db() as con:
        rows = con.execute("SELECT * FROM tasks WHERE agent_id=? ORDER BY created_at", (aid,)).fetchall()
    out=[]
    for r in rows:
        d=rowdict(r); d["payload"]=json.loads(d["payload"]); d["result"]=json.loads(d["result"]) if d["result"] else None; out.append(d)
    return out


class Handler(BaseHTTPRequestHandler):
    server_version = "CEREBRON-AgentTwin/1.0"

    def log_message(self, fmt, *args):
        print("HTTP", self.address_string(), fmt % args)

    def send_json(self, code: int, obj):
        raw = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers(); self.wfile.write(raw)

    def body(self):
        n = int(self.headers.get("Content-Length", "0") or 0)
        if n > 1_000_000: raise ValueError("body too large")
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        p=urlparse(self.path).path.rstrip("/") or "/"
        if p == "/health":
            return self.send_json(200,{"ok":True,"engine":"CEREBRON_AGENT_TWIN_API_V1","spend_limit_eur":0,"paid_fallback":False})
        parts=p.strip("/").split("/")
        if len(parts)==2 and parts[0]=="agents":
            a=get_agent(parts[1]); return self.send_json(200,a) if a else self.send_json(404,{"error":"agent_not_found"})
        if len(parts)==3 and parts[0]=="agents" and parts[2]=="results":
            return self.send_json(200,{"agent_id":parts[1],"tasks":agent_results(parts[1])})
        if len(parts)==2 and parts[0]=="tasks":
            t=get_task(parts[1]); return self.send_json(200,t) if t else self.send_json(404,{"error":"task_not_found"})
        return self.send_json(404,{"error":"not_found"})

    def do_POST(self):
        p=urlparse(self.path).path.rstrip("/") or "/"
        try: data=self.body()
        except Exception as exc: return self.send_json(400,{"error":str(exc)})
        if p=="/agents": return self.send_json(201,create_agent(data))
        parts=p.strip("/").split("/")
        if len(parts)==3 and parts[0]=="agents" and parts[2]=="tasks":
            t=submit_task(parts[1],data); return self.send_json(201,t) if t else self.send_json(409,{"error":"agent_unavailable"})
        if len(parts)==3 and parts[0]=="agents" and parts[2]=="spawn":
            children=spawn_agents(parts[1],data); return self.send_json(201,{"children":children}) if children is not None else self.send_json(404,{"error":"agent_not_found"})
        return self.send_json(404,{"error":"not_found"})

    def do_DELETE(self):
        p=urlparse(self.path).path.rstrip("/")
        parts=p.strip("/").split("/")
        if len(parts)==2 and parts[0]=="agents":
            return self.send_json(200,{"agent_id":parts[1],"stopped":True}) if stop_agent(parts[1]) else self.send_json(404,{"error":"agent_not_found"})
        return self.send_json(404,{"error":"not_found"})


def serve(host: str, port: int):
    init_db()
    srv=ThreadingHTTPServer((host,port),Handler)
    print(json.dumps({"engine":"CEREBRON_AGENT_TWIN_API_V1","listen":f"http://{host}:{port}","spend_limit_eur":0,"paid_fallback":False}))
    srv.serve_forever()


if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--host",default="127.0.0.1"); ap.add_argument("--port",type=int,default=8787); args=ap.parse_args()
    serve(args.host,args.port)
