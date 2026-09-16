from http.server import BaseHTTPRequestHandler
import hashlib
import json
import os
import time


def execute(prompt: str) -> str:
    try:
        spec = json.loads(prompt)
    except Exception:
        spec = {"op": "sha256", "value": prompt}
    op = spec.get("op", "sha256")
    if op == "echo":
        return str(spec.get("value", ""))
    if op == "sha256":
        return hashlib.sha256(str(spec.get("value", "")).encode()).hexdigest()
    if op == "sum":
        values = spec.get("values", [])
        if not isinstance(values, list) or not all(isinstance(v, (int, float)) for v in values):
            raise ValueError("sum requires numeric values[]")
        return str(sum(values))
    raise ValueError(f"unsupported op: {op}")


class handler(BaseHTTPRequestHandler):
    def _send(self, code: int, payload: dict):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        token = os.getenv("CEREBRON_WORKER_TOKEN", "")
        if not token:
            return self._send(503, {"ok": False, "error": "worker token not configured"})
        if self.headers.get("Authorization", "") != f"Bearer {token}":
            return self._send(401, {"ok": False, "error": "unauthorized"})
        started = time.perf_counter()
        try:
            n = int(self.headers.get("Content-Length", "0") or "0")
            if n > 262144:
                return self._send(413, {"ok": False, "error": "payload too large"})
            task = json.loads(self.rfile.read(n) or b"{}")
            result = execute(str(task.get("prompt", "")))
            return self._send(200, {
                "ok": True,
                "worker_id": "vercel-hobby-worker",
                "result": result,
                "evidence": {"provider": "vercel", "deterministic": True, "paid_fallback": False},
                "runtime_s": time.perf_counter() - started,
                "cost_eur": 0.0,
                "model": None,
            })
        except Exception as exc:
            return self._send(400, {
                "ok": False,
                "result": "",
                "error": f"{type(exc).__name__}: {exc}",
                "runtime_s": time.perf_counter() - started,
                "cost_eur": 0.0,
            })
