# CEREBRON Ω — Supabase integration

Role: persistent state, task metadata, evidence index, queue coordination, and lightweight Edge Function execution.

Rules:
- zero-euro default;
- no paid fallback;
- no card-required upgrade path is enabled by code;
- secrets only through environment variables;
- Supabase is not counted as a large compute pool;
- Edge Functions may execute only allowlisted deterministic handlers unless a separately audited worker backend is connected.

Required environment variables when connected:
- `CEREBRON_SUPABASE_URL`
- `CEREBRON_SUPABASE_ANON_KEY` for least-privilege public operations when appropriate
- `CEREBRON_SUPABASE_SERVICE_ROLE_KEY` only on trusted server-side components when strictly required
- `CEREBRON_SUPABASE_WORKER_URL`
- `CEREBRON_SUPABASE_WORKER_TOKEN`

Never commit keys to the repository.

Target tables:
- `forge_workers`
- `forge_tasks`
- `forge_task_events`
- `forge_evidence`
- `forge_provider_health`

Status semantics:
- PREPARED = code exists
- CONNECTED = credentials/endpoints work
- VERIFIED = a real task executed and returned evidence

Only VERIFIED resources count toward real worker capacity.
