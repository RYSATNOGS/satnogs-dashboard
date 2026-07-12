# satnogs-dashboard

Observation Review Workbench for SatNOGS community review.

A thin web app that composes three sibling engines:

- `satnogs-signal` for signal/noise triage (feeds the review queue).
- `satnogs-id` for Doppler-based object identification.
- `satnogs-decoder` for decoder validation and maintainer review evidence.

## Quick start

Needs `git` and Docker. Linux or macOS; on Windows use WSL2.

    git clone https://github.com/RYASTRA/satnogs-dashboard.git
    cd satnogs-dashboard
    docker compose up

Open http://localhost:8000. The first run takes a few minutes: Docker
builds the three engine images straight from their GitHub repos (nothing
else to clone or install) and starts all four containers:

| container         | role                                              |
| ----------------- | ------------------------------------------------- |
| satnogs-dashboard | the web app on :8000                              |
| satnogs-signal    | scores new observations into the queue every 15 m |
| satnogs-id        | identification engine, runs on demand             |
| satnogs-decoder   | decoder-evidence engine, runs on demand           |

Run detached with `docker compose up -d`; stop with `docker compose down`.
Update to the engines' latest code with `make up` (rebuilds, then starts).

## API tokens (optional)

Everything starts without tokens; add them to `.env` (copy `.env.example`)
for full functionality:

- `satnogs_network_api_key` — queue polling (from your
  [network.satnogs.org](https://network.satnogs.org) profile).
- `satnogs_db_api_key` — decoder evidence frames (from your
  [db.satnogs.org](https://db.satnogs.org) profile).
- `HUGGING_FACE_HUB_TOKEN` — model downloads
  ([huggingface.co](https://huggingface.co/settings/tokens)).

After editing `.env`, restart: `docker compose up -d`.

## How it runs

The queue reads satnogs-signal's `triage.db` (shared `data` volume,
read-only use). The Identify/Decode buttons execute the JSON runner
scripts inside the always-on id/decoder containers via the docker socket
and cache results in `dashboard.db`. The app never writes to SatNOGS.

## Development

Host-run dev loop (the uv project env lives outside the tree):

    make dev
    open http://localhost:8000

No sibling data yet? Seed a fake queue:

    make seed
    SATNOGS_SIGNAL_DB=dev_triage.db make dev

Tests (offline by default): `make test`
Live engine smokes: `make test ARGS="-m slow"`
