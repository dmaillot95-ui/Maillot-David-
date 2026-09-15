export function createOpenAICompatibleInfer({
  baseUrl = process.env.CEREBRON_BASE_URL,
  apiKey = process.env.CEREBRON_API_KEY,
  model = process.env.CEREBRON_MODEL,
  timeoutMs = 120000,
  maxTokens = 700,
  temperature = 0.25
} = {}) {
  if (!baseUrl) throw new Error('CEREBRON_BASE_URL manquant.');
  if (!model) throw new Error('CEREBRON_MODEL manquant.');

  const root = String(baseUrl).replace(/\/$/, '');

  return async function infer(system, user, meta = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const res = await fetch(`${root}/chat/completions`, {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          ...(apiKey ? { authorization: `Bearer ${apiKey}` } : {})
        },
        body: JSON.stringify({
          model,
          messages: [
            { role: 'system', content: system },
            { role: 'user', content: user }
          ],
          temperature,
          max_tokens: maxTokens,
          metadata: {
            cerebron_phase: meta?.phase || 'unknown',
            cerebron_agent: meta?.agent?.id || null
          }
        }),
        signal: controller.signal
      });

      const text = await res.text();
      if (!res.ok) throw new Error(`Provider ${res.status}: ${text.slice(0, 500)}`);
      const data = JSON.parse(text);
      return data?.choices?.[0]?.message?.content?.trim()
        || data?.output_text
        || '[AUCUN TEXTE RETOURNE]';
    } finally {
      clearTimeout(timer);
    }
  };
}
