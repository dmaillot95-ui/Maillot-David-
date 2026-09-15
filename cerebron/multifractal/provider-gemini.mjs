function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function createGeminiInfer({
  apiKey = process.env.GEMINI_API_KEY,
  model = process.env.GEMINI_MODEL || 'gemini-3.1-flash-lite',
  maxOutputTokens = Number(process.env.GEMINI_MAX_OUTPUT_TOKENS || 1400),
  temperature = Number(process.env.GEMINI_TEMPERATURE || 0.2),
  retries = 4
} = {}) {
  if (!apiKey) {
    throw new Error('PROVIDER_NOT_CONFIGURED: GEMINI_API_KEY absent.');
  }

  return async function infer(system, user, meta = {}) {
    const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent?key=${encodeURIComponent(apiKey)}`;
    const body = {
      system_instruction: {
        parts: [{ text: String(system || '') }]
      },
      contents: [{
        role: 'user',
        parts: [{ text: String(user || '') }]
      }],
      generationConfig: {
        temperature,
        maxOutputTokens
      }
    };

    let lastError;
    for (let attempt = 0; attempt <= retries; attempt += 1) {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(body)
      });

      if (response.ok) {
        const data = await response.json();
        const text = data?.candidates?.[0]?.content?.parts
          ?.map((part) => part?.text || '')
          .join('')
          .trim();
        if (!text) throw new Error(`EMPTY_MODEL_OUTPUT phase=${meta?.phase || 'unknown'}`);
        return text;
      }

      const raw = await response.text();
      lastError = new Error(`GEMINI_HTTP_${response.status}: ${raw.slice(0, 800)}`);
      if (![429, 500, 502, 503, 504].includes(response.status) || attempt === retries) break;
      await sleep(Math.min(12000, 1200 * (2 ** attempt)));
    }

    throw lastError || new Error('GEMINI_REQUEST_FAILED');
  };
}
