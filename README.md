# satnogs-dashboard

Observation Review Workbench for SatNOGS community review.

A thin web app that composes three sibling engines:

- `satnogs-signal` for signal/noise triage (feeds the review queue).
- `satnogs-id` for Doppler-based object identification.
- `satnogs-decoder` for decoder validation and maintainer review evidence.

## Quick start

Needs `git` and Docker (with the compose plugin). Linux or macOS; on
Windows use WSL2.

    git clone https://github.com/RYASTRA/satnogs-dashboard.git
    cd satnogs-dashboard
    ./run.sh

Open http://localhost:8000. The first run takes a few minutes: the script
clones the three engine repos next to this one and builds their images.
Run in the background with `./run.sh -d`; stop with `docker compose down`.

`run.sh` does, in order:

1. Clone (or update) `../satnogs-signal`, `../satnogs-id`, `../satnogs-decoder`.
2. Build their Docker images.
3. Create `.env` from `.env.example` on first run.
4. `docker compose up`: the dashboard on :8000 plus a poller that scores new
   observations into the review queue every 15 minutes.

## API tokens (optional)

Everything starts without tokens; add them to `.env` for full functionality:

- `satnogs_network_api_key` — queue polling (from your
  [network.satnogs.org](https://network.satnogs.org) profile).
- `satnogs_db_api_key` — decoder evidence frames (from your
  [db.satnogs.org](https://db.satnogs.org) profile).
- `HUGGING_FACE_HUB_TOKEN` — model downloads
  ([huggingface.co](https://huggingface.co/settings/tokens)).

## How it runs

The compose file mounts the repo's parent directory (repo + siblings) at its
host path plus the docker socket, so the identity/decoder buttons can drive
the sibling containers from inside the dashboard container — the engines spin
up on demand per click, and results are cached in `dashboard.db`. The queue
reads satnogs-signal's `triage.db` read-only. The app never writes to SatNOGS.

## Development

Host-run alternative (the uv project env lives outside the tree):

    make dev
    open http://localhost:8000

No sibling data yet? Seed a fake queue:

    make seed
    SATNOGS_SIGNAL_DB=dev_triage.db make dev

Tests (offline by default): `make test`
Live engine smokes: `make test ARGS="-m slow"`
