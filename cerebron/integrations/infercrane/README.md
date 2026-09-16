# CEREBRON Ω — InferCrane optional integration

InferCrane is treated as an orchestration/observability layer for self-hosted model endpoints, not as free compute by itself.

Potential role inside CEREBRON:
- register compatible inference backends;
- route requests to already-authorized model servers;
- observe latency/errors;
- support release guards/candidate deployments;
- provide an additional control plane beside CEREBRON FORGE.

Hard rules:
- zero-euro default;
- no cloud resource creation from CEREBRON unless the target provider is explicitly allowlisted and verified free;
- no automatic AWS/GCP/RunPod provisioning;
- no arbitrary shell task execution from remote requests;
- secrets remain environment-only;
- an InferCrane endpoint does not increase real worker count unless an actual backend worker is verified behind it.

Suggested environment variables:
- `CEREBRON_INFERCRANE_ENABLE=0`
- `CEREBRON_INFERCRANE_URL`
- `CEREBRON_INFERCRANE_TOKEN`

Activation gate:
1. endpoint reachable;
2. auth verified;
3. backend provenance known;
4. cost policy verified at 0 EUR;
5. one deterministic test task succeeds;
6. evidence recorded.

Until all six pass, state remains PREPARED, not VERIFIED.
