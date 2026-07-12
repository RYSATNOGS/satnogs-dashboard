# satnogs-dashboard

Observation Review Workbench for SatNOGS community review.

A thin web app that composes three sibling engines:

- `satnogs-signal` for signal/noise triage (feeds the review queue).
- `satnogs-id` for Doppler-based object identification.
- `satnogs-decoder` for decoder validation and maintainer review evidence.

## Quick start

Needs `git` and Docker. Linux, macOS, or WSL2:

    git clone https://github.com/RYASTRA/satnogs-dashboard.git
    cd satnogs-dashboard
    ./scripts/setup.sh

Native Windows without WSL2, in PowerShell:

    git clone https://github.com/RYASTRA/satnogs-dashboard.git
    cd satnogs-dashboard
    powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1

The setup script asks for three optional API tokens (press Enter to skip
any), writes them to `.env`, then starts the stack. Prefer to skip it? Plain
`docker compose up` still works and runs everything tokenless.

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
Update to the latest code with `docker compose up --build`.

## API tokens (optional)

Everything starts without tokens. The easiest way to add them is the setup
script above (re-run it with `--reconfigure` / `-Reconfigure` to change them).
To edit by hand, copy `.env.example` to `.env` and fill in any of:

- `satnogs_network_api_key` — queue polling (from your
  [network.satnogs.org](https://network.satnogs.org) profile).
- `satnogs_db_api_key` — decoder evidence frames (from your
  [db.satnogs.org](https://db.satnogs.org) profile).
- `HUGGING_FACE_HUB_TOKEN` — model downloads
  ([huggingface.co](https://huggingface.co/settings/tokens)).

After editing `.env`, restart: `docker compose up -d`.

## How it runs

The queue fills as satnogs-signal scores new observations. The
Identify/Decode buttons run the engines and cache their results, so
reviewing an observation is: open it, read the evidence panels, decide.
The app only ever reads from SatNOGS — it never writes back.
