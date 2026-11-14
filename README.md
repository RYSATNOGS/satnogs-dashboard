# satnogs-dashboard

Observation Review Workbench for SatNOGS community review.

## The SatNOGS fleet

Four small, honest tools around a SatNOGS observation — three single-purpose engines, plus one app
that composes them for a human reviewer:

| repo | the question it answers |
|---|---|
| [satnogs-signal](https://github.com/RYSATNOGS/satnogs-signal) | *is there a signal in this waterfall?* — signal-vs-noise triage |
| [satnogs-decoder](https://github.com/RYSATNOGS/satnogs-decoder) | *what does the frame say?* — telemetry decoding |
| [satnogs-id](https://github.com/RYSATNOGS/satnogs-id) | *which catalog object is it?* — Doppler identification |
| **satnogs-dashboard** (this repo) | ***review it all on one observation*** — the workbench that runs the three engines |

The three engines are standalone and read-only against SatNOGS; the dashboard is the surface that
composes them. This repo is the **dashboard** — it runs the three engines and shows their evidence
side by side.

## Quick start

Needs `git` and Docker. Linux, macOS, or WSL2:

    git clone https://github.com/RYSATNOGS/satnogs-dashboard.git
    cd satnogs-dashboard
    ./scripts/setup.sh

Native Windows without WSL2, in PowerShell:

    git clone https://github.com/RYSATNOGS/satnogs-dashboard.git
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
After pulling the latest code, run `docker compose up --build` to rebuild the
dashboard and engines with fresh base images and Python dependencies.

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
