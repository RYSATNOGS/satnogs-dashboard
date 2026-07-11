# satnogs-dashboard

Observation Review Workbench for SatNOGS community review.

This repo is starting as a thin web app that composes three sibling engines:

- `satnogs-signal` for signal/noise triage.
- `satnogs-id` for Doppler-based object identification.
- `satnogs-decoder` for decoder validation and maintainer review evidence.

## Run (MVP)

Container-first (sibling convention — the container is the environment):

    cp .env.example .env          # adjust paths/tokens
    docker compose up --build
    open http://localhost:8000

The compose file mounts the repo's parent directory (repo + siblings) at its
host path plus the docker socket, so the identity/decoder buttons can drive
the sibling containers from inside the dashboard container.

Host-run alternative (the uv project env lives outside the tree):

    make dev
    open http://localhost:8000

The queue reads satnogs-signal's `triage.db` read-only. Identity and decoder
buttons run the sibling engines inside their own containers (build them once:
`docker compose build` in each sibling repo) and cache results in
`dashboard.db`. The app never writes to SatNOGS.

No sibling data yet? Seed a fake queue:

    make seed
    SATNOGS_SIGNAL_DB=dev_triage.db make dev

Tests (offline by default): `make test`
Live engine smokes: `make test ARGS="-m slow"`
