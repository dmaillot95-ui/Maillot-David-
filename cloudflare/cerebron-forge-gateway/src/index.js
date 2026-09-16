export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/health") {
      return Response.json({ ok: true, service: "cerebron-forge-gateway", zero_cost_mode: env.CEREBRON_ZERO_COST === "1" });
    }
    if (!env.FORGE_ORIGIN) {
      return Response.json({ ok: false, error: "FORGE_ORIGIN_NOT_CONFIGURED" }, { status: 503 });
    }
    const allowed = new Set(["/status", "/register", "/submit", "/claim", "/finish"]);
    if (!allowed.has(url.pathname)) {
      return Response.json({ ok: false, error: "NOT_FOUND" }, { status: 404 });
    }
    const target = new URL(url.pathname, env.FORGE_ORIGIN);
    const headers = new Headers(request.headers);
    headers.set("X-Cerebron-Gateway", "cloudflare");
    if (env.FORGE_TOKEN) headers.set("Authorization", `Bearer ${env.FORGE_TOKEN}`);
    const init = { method: request.method, headers, redirect: "manual" };
    if (request.method !== "GET" && request.method !== "HEAD") init.body = await request.arrayBuffer();
    const response = await fetch(target, init);
    const outHeaders = new Headers(response.headers);
    outHeaders.set("X-Cerebron-Zero-Cost", "1");
    return new Response(response.body, { status: response.status, headers: outHeaders });
  },
};
