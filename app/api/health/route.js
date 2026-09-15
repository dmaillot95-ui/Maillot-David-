export async function GET() {
  return Response.json({
    ok: true,
    service: 'CEREBRON OMEGA',
    provider_configured: Boolean(process.env.CEREBRON_API_BASE),
    model: process.env.CEREBRON_MODEL || null
  })
}
