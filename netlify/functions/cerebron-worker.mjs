import crypto from "node:crypto";

function execute(prompt) {
  let spec;
  try { spec = JSON.parse(prompt); } catch { spec = { op: "sha256", value: prompt }; }
  const op = spec.op || "sha256";
  if (op === "echo") return String(spec.value ?? "");
  if (op === "sha256") return crypto.createHash("sha256").update(String(spec.value ?? "")).digest("hex");
  if (op === "sum") {
    if (!Array.isArray(spec.values) || !spec.values.every(Number.isFinite)) throw new Error("sum requires numeric values[]");
    return String(spec.values.reduce((a, b) => a + b, 0));
  }
  throw new Error(`unsupported op: ${op}`);
}

export default async (request) => {
  const token = process.env.CEREBRON_WORKER_TOKEN || "";
  if (!token) return Response.json({ ok: false, error: "worker token not configured" }, { status: 503 });
  if (request.headers.get("authorization") !== `Bearer ${token}`) {
    return Response.json({ ok: false, error: "unauthorized" }, { status: 401 });
  }
  if (request.method !== "POST") return Response.json({ ok: false, error: "POST required" }, { status: 405 });
  const started = performance.now();
  try {
    const task = await request.json();
    const result = execute(String(task.prompt ?? ""));
    return Response.json({
      ok: true,
      worker_id: "netlify-free-worker",
      result,
      evidence: { provider: "netlify", deterministic: true, paid_fallback: false },
      runtime_s: (performance.now() - started) / 1000,
      cost_eur: 0.0,
      model: null
    });
  } catch (err) {
    return Response.json({ ok: false, error: String(err), result: "", runtime_s: (performance.now() - started) / 1000, cost_eur: 0.0 }, { status: 400 });
  }
};

export const config = { path: "/cerebron-worker" };
