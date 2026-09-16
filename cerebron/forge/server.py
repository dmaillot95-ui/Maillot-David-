#!/usr/bin/env python3
"""CEREBRON FORGE Ω — minimal distributed HTTP control plane.

Standard-library HTTP server exposing worker registration, task submission,
claim, completion, and status over JSON. Intended for trusted/private networks
or a reverse proxy with authentication. No paid provider calls.
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from cerebron.forge.core import Worker, connect, register_worker, submit_task, claim_task, finish_task, status

DB_PATH = os.getenv("CEREBRON_FORGE_DB", "out/cerebron-forge-distributed.db")
BIND = os.getenv("CEREBRON_FORGE_BIND", "127.0.0.1")
PORT = int(os.getenv("CEREBRON_FORGE_PORT", "8765"))
TOKEN = os.getenv("CEREBRON_FORGE_TOKEN", "")


def _json_row(row):
    if row is None:
        return None
    d = dict(row)
    for key in ("payload_json", "required_capabilities_json", "result_json"):
        if key in d and d[key]:
            try:
                d[key[:-5] if key.endswith('_json') else key] = json.loads(d[key])
            except Exception:
                pass
    return d


class Handler(BaseHTTPRequestHandler):
    server_version = "CerebronForge/1"

    def _auth_ok(self):
        if not TOKEN:
            return True
        return self.headers.get("Authorization", "") == f"Bearer {TOKEN}"

    def _send(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(n) if n else b"{}"
        return json.loads(raw.decode("utf-8"))

    def do_GET(self):
        if not self._auth_ok():
            return self._send(401, {"ok": False, "error": "unauthorized"})
        if urlparse(self.path).path == "/status":
            db = connect(DB_PATH)
            return self._send(200, {"ok": True, **status(db)})
        return self._send(404, {"ok": False, "error": "not_found"})

    def do_POST(self):
        if not self._auth_ok():
            return self._send(401, {"ok": False, "error": "unauthorized"})
        try:
            data = self._body()
            path = urlparse(self.path).path
            db = connect(DB_PATH)
            if path == "/register":
                w = Worker(
                    worker_id=str(data["worker_id"]),
                    machine_id=str(data["machine_id"]),
                    capabilities=list(data.get("capabilities", [])),
                    max_parallel=int(data.get("max_parallel", 1)),
                    provider=str(data.get("provider", "remote")),
                )
                register_worker(db, w)
                return self._send(200, {"ok": True, "worker_id": w.worker_id})
            if path == "/submit":
                tid = submit_task(
                    db,
                    str(data["kind"]),
                    dict(data.get("payload", {})),
                    list(data.get("required_capabilities", [])),
                    int(data.get("priority", 100)),
                )
                return self._send(200, {"ok": True, "task_id": tid})
            if path == "/claim":
                row = claim_task(db, str(data["worker_id"]))
                return self._send(200, {"ok": True, "task": _json_row(row)})
            if path == "/finish":
                finish_task(
                    db,
                    str(data["task_id"]),
                    str(data["worker_id"]),
                    dict(data.get("result", {})),
                    str(data.get("status", "COMPLETED")),
                    data.get("error"),
                )
                return self._send(200, {"ok": True})
            return self._send(404, {"ok": False, "error": "not_found"})
        except Exception as exc:
            return self._send(400, {"ok": False, "error": f"{type(exc).__name__}: {exc}"})

    def log_message(self, fmt, *args):
        if os.getenv("CEREBRON_FORGE_QUIET", "0") != "1":
            super().log_message(fmt, *args)


def main():
    server = ThreadingHTTPServer((BIND, PORT), Handler)
    print(json.dumps({"ok": True, "bind": BIND, "port": PORT, "db": DB_PATH, "token_required": bool(TOKEN)}), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
