# CEREBRON INFERENCE HUB V1

Zero-euro control plane for many logical agents with bounded physical concurrency.

## Principles
- Logical agent count is not physical parallelism.
- No paid provider is enabled automatically.
- Quota errors are retryable states, never successes.
- External model outputs remain unreviewed evidence until audited.
- Collatz federation is separate and untouched.

## Current V1
- Persistent JSON queue.
- Up to 10,000 logical agents per mission definition.
- Micro-batch scheduler, default 4 physical workers.
- Up to 3 model candidates per task through the existing free Hugging Face registry.
- Backoff and jitter.
- GitHub Actions validation.
- Optional Cloudflare provider is disabled until an account is explicitly connected.

## CLI
```bash
python cerebron/inference_hub/hub.py enqueue --mission-id DEMO --prompt "Question" --agents 20
python cerebron/inference_hub/hub.py run --limit 20
python cerebron/inference_hub/hub.py status
```

The V1 is an orchestration layer, not a claim of unlimited compute or superintelligence.
