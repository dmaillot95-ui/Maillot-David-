const JSON_HEADERS = { "content-type": "application/json; charset=utf-8" };

function json(data, status = 200) {
  return new Response(JSON.stringify(data, null, 2), { status, headers: JSON_HEADERS });
}

function html(body, status = 200) {
  return new Response(body, { status, headers: { "content-type": "text/html; charset=utf-8" } });
}

const PAGE = `<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CEREBRON Inference Hub</title>
<style>body{font-family:system-ui,sans-serif;max-width:900px;margin:40px auto;padding:0 18px;background:#0b1020;color:#e8ecf4}button,input,textarea{font:inherit}textarea,input{width:100%;box-sizing:border-box;margin:6px 0 14px;padding:10px;border-radius:8px;border:1px solid #445;background:#131a2d;color:#fff}button{padding:10px 16px;border:0;border-radius:8px;cursor:pointer}pre{white-space:pre-wrap;background:#131a2d;padding:14px;border-radius:8px}.muted{opacity:.75}</style>
</head><body><h1>CEREBRON INFERENCE HUB Ω</h1><p class="muted">Control plane zéro-euro. Agents logiques ≠ workers physiques.</p>
<label>Mission</label><input id="mission" value="PHONE-MISSION">
<label>Question</label><textarea id="prompt" rows="6">Analyse cette question avec CLAIM <= EVIDENCE.</textarea>
<label>Agents logiques</label><input id="agents" type="number" min="1" max="10000" value="20">
<button onclick="prepare()">Préparer mission</button>
<pre id="out">Prêt.</pre>
<script>
async function prepare(){const payload={mission_id:mission.value,prompt:prompt.value,agents:Number(agents.value)};const r=await fetch('/api/mission/validate',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(payload)});out.textContent=JSON.stringify(await r.json(),null,2)}
</script></body></html>`;

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/") return html(PAGE);
    if (url.pathname === "/api/health") {
      return json({
        service: "CEREBRON_INFERENCE_HUB",
        version: "v1",
        status: "OK",
        spend_limit_eur: 0,
        max_logical_agents: 10000,
        note: "This HTTP layer validates and routes missions; compute remains bounded by enabled zero-euro providers."
      });
    }
    if (url.pathname === "/api/mission/validate" && request.method === "POST") {
      let body;
      try { body = await request.json(); } catch { return json({ok:false,error:"INVALID_JSON"},400); }
      const missionId = String(body.mission_id || "").trim();
      const prompt = String(body.prompt || "").trim();
      const agents = Number(body.agents || 20);
      if (!missionId || !prompt) return json({ok:false,error:"MISSION_ID_AND_PROMPT_REQUIRED"},400);
      if (!Number.isInteger(agents) || agents < 1 || agents > 10000) return json({ok:false,error:"AGENTS_OUT_OF_RANGE",min:1,max:10000},400);
      return json({
        ok: true,
        accepted: true,
        mission_id: missionId,
        logical_agents: agents,
        physical_workers: "BOUNDED_BY_SCHEDULER_AND_FREE_QUOTA",
        execution_status: "NOT_STARTED",
        next_step: "Submit to authenticated scheduler endpoint after provider binding"
      });
    }
    return json({ok:false,error:"NOT_FOUND"},404);
  }
};
