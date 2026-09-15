import { runMultifractal } from '../../../../cerebron/multifractal/core.mjs';
import { createOpenAICompatibleInfer } from '../../../../cerebron/multifractal/provider-openai-compatible.mjs';

export const runtime = 'nodejs';
export const maxDuration = 300;

export async function POST(request) {
  try {
    const body = await request.json();
    const mission = String(body?.mission || '').trim();
    if (!mission) {
      return Response.json({ ok: false, error: 'mission requise' }, { status: 400 });
    }

    const infer = createOpenAICompatibleInfer({
      baseUrl: process.env.CEREBRON_BASE_URL,
      apiKey: process.env.CEREBRON_API_KEY,
      model: process.env.CEREBRON_MODEL,
      maxTokens: Number(process.env.CEREBRON_MAX_TOKENS || 700)
    });

    const result = await runMultifractal({
      mission,
      agentCount: body?.agentCount ?? 20,
      swarmSize: body?.swarmSize ?? 10,
      concurrency: body?.concurrency ?? 4,
      infer
    });

    return Response.json({ ok: true, result });
  } catch (error) {
    return Response.json({ ok: false, error: String(error?.message || error) }, { status: 500 });
  }
}

export async function GET() {
  return Response.json({
    ok: true,
    service: 'CEREBRON OMEGA MULTIFRACTAL',
    version: '1.0',
    status: 'READY_FOR_PROVIDER',
    limits: { leavesPerMission: 120, swarmSizeMax: 10 }
  });
}
