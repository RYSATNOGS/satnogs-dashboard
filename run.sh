#!/usr/bin/env bash
# One-command setup + run for the SatNOGS review workbench.
# Clones/updates the three engine repos NEXT TO this one (sibling convention),
# builds their images, prepares .env, then starts the dashboard + poller.
# Extra args go to `docker compose up` (e.g. `./run.sh -d` for background).
set -euo pipefail

cd "$(dirname "$0")"
PARENT="$(cd .. && pwd)"
ENGINES="satnogs-signal satnogs-id satnogs-decoder"
BASE_URL="${SATNOGS_GIT_BASE:-https://github.com/RYASTRA}"

command -v git >/dev/null 2>&1 || { echo "error: git is required"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "error: docker is required — https://docs.docker.com/get-docker/"; exit 1; }
docker info >/dev/null 2>&1 || { echo "error: the docker daemon is not running"; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "error: docker compose v2 is required"; exit 1; }

for repo in $ENGINES; do
    dir="$PARENT/$repo"
    if [ ! -d "$dir/.git" ]; then
        echo "==> cloning $repo"
        git clone "$BASE_URL/$repo.git" "$dir"
    else
        echo "==> updating $repo"
        git -C "$dir" pull --ff-only || \
            echo "    (skipped: local changes or diverged history — using checkout as-is)"
    fi
done

for repo in $ENGINES; do
    echo "==> building $repo image"
    (cd "$PARENT/$repo" && docker compose build)
done

if [ ! -f .env ]; then
    cp .env.example .env
    echo
    echo "==> created .env — API tokens are optional but recommended (edit .env):"
    echo "    satnogs_network_api_key : queue polling    (network.satnogs.org)"
    echo "    satnogs_db_api_key      : decoder evidence (db.satnogs.org)"
    echo "    HUGGING_FACE_HUB_TOKEN  : model downloads  (huggingface.co)"
    echo
fi

echo "==> starting dashboard (http://localhost:8000) + signal poller"
exec docker compose up --build "$@"
