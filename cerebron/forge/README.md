# CEREBRON FORGE Ω

CEREBRON FORGE Ω is the independent control plane for CEREBRON CLOUD Ω.

## Roles

- `core.py`: persistent worker registry, queue, atomic task claim, ownership and terminal state.
- `server.py`: HTTP control plane for remote workers and dashboards.
- `remote_worker.py`: remote worker client.
- `dashboard_export.py`: read-only JSON snapshot for dashboards such as Floot.

## Zero-euro policy

The canonical policy is `cerebron/config/cloud_zero_euro.json`.

Default rules:

- spend limit = 0 EUR;
- paid fallback forbidden;
- external providers disabled until explicitly configured;
- secrets never stored in the repository;
- volunteer-compute architecture disabled;
- card-required providers are not part of the default execution path;
- a dashboard is not a compute worker;
- a logical worker is not automatically an independent physical machine or model.

## Control plane

Local development:

```bash
CEREBRON_FORGE_TOKEN=development-token \
CEREBRON_FORGE_BIND=127.0.0.1 \
python -m cerebron.forge.server
```

Public deployments must provide `CEREBRON_FORGE_TOKEN` and should be placed behind an authenticated reverse proxy or gateway.

Endpoints:

- `GET /health` — liveness only, no sensitive queue details.
- `GET /status` — authenticated scheduler status.
- `POST /register` — register/update a worker.
- `POST /submit` — submit a task.
- `POST /claim` — atomically claim one compatible pending task.
- `POST /finish` — return a terminal result.

## Intended free-cloud topology

```text
Cloudflare gateway
       |
       v
CEREBRON FORGE control plane (Render or another allowed free host)
       |
       +--> GitHub Actions batch workers
       +--> explicitly configured free endpoints
       +--> optional dashboards (Floot is read-only/status-oriented)
```

The repository prepares adapters and deployment manifests. An adapter being present does not prove that the external account or endpoint is connected.

## Evidence doctrine

CLAIM <= EVIDENCE. A committed configuration is not a deployed service. A queued workflow is not a completed execution. A logical worker is not evidence of an independent machine. Simulation is not a test.
