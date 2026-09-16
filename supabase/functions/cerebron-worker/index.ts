const enc = new TextEncoder();

async function sha256(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", enc.encode(value));
  return Array.from(new Uint8Array(digest)).map(b => b.toString(16).padStart(2, "0")).join("");
}

async function execute(prompt: string): Promise<string> {
  let spec: any;
  try { spec = JSON.parse(prompt); } catch { spec = { op: "sha256", value: prompt }; }
  const op = spec.op || "sha256";
  if (op === "echo") return String(spec.value ?? "");
  if (op === "sha256") return await sha256(String(spec.value ?? ""));
  if (op === "sum") {
    if (!Array.isArray(spec.values) || !spec.values.every((v: unknown) => typeof v === "number" && Number.isFinite(v))) {
      throw new Error("sum requires numeric values[]");
    }
    return String(spec.values.reduce((a: number, b: number) => a + b, 0));
  }
  throw new Error(`unsupported op: ${op}`);
}

Deno.serve(async (req: Request) => {
  const token = Deno.env.get("CEREBRON_WORKER_TOKEN") || "";
  if (!token) return Response.json({ ok: false, error: "worker token not configured" }, { status: 503 });
  if (req.headers.get("authorization") !== `Bearer ${token}`) {
    return Response.json({ ok: false, error: "unauthorized" }, { status: 401 });
  }
  if (req.method !== "POST") return Response.json({ ok: false, error: "POST required" }, { status: 405 });

  const started = performance.now();
  try {
    const task = await req.json();
    const result = await execute(String(task.prompt ?? ""));
    return Response.json({
      ok: true,
      worker_id: "supabase-free-edge-worker",
      result,
      evidence: { provider: "supabase", deterministic: true, paid_fallback: false },
      runtime_s: (performance.now() - started) / 1000,
      cost_eur: 0.0,
      model: null
    });
  } catch (err) {
    return Response.json({ ok: false, error: String(err), result: "", runtime_s: (performance.now() - started) / 1000, cost_eur: 0.0 }, { status: 400 });
  }
});
