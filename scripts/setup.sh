#!/bin/sh
# First-run setup for the community deploy: collect the three optional API
# tokens into a root .env, then start the stack. Every token may be skipped
# (press Enter) — the stack runs tokenless without them. Plain
# `docker compose up` still works and is unaffected by this script.
#
#   ./scripts/setup.sh                # prompt if .env is missing, then up
#   ./scripts/setup.sh -d --build     # extra args are passed through to compose
#   ./scripts/setup.sh --reconfigure  # re-enter tokens even if .env exists
set -eu

# Repo root is the parent of this script's directory, so the script works
# regardless of the caller's working directory.
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(dirname -- "$SCRIPT_DIR")
ENV_FILE="$ROOT/.env"
EXAMPLE="$ROOT/.env.example"

# Peel our own --reconfigure flag out of the arguments; forward the rest to
# compose. Process exactly $# items: drop the flag, re-append everything else
# (this preserves arguments that contain spaces).
RECONFIGURE=0
n=$#
while [ "$n" -gt 0 ]; do
    arg=$1
    shift
    if [ "$arg" = "--reconfigure" ]; then
        RECONFIGURE=1
    else
        set -- "$@" "$arg"
    fi
    n=$((n - 1))
done

if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is required but was not found on PATH." >&2
    echo "Install Docker, then re-run this script." >&2
    exit 1
fi

# ask KEY DESCRIPTION URL  ->  sets REPLY_VALUE to the entered (or empty) token.
ask() {
    printf '\n%s — %s\n  Get it: %s\n  %s (press Enter to skip): ' "$1" "$2" "$3" "$1"
    IFS= read -r REPLY_VALUE || REPLY_VALUE=""
}

# write_env NETWORK DB HF  ->  writes .env from .env.example, substituting the
# three token lines and copying every other line (comments, tuning block)
# verbatim so .env stays self-documenting.
write_env() {
    _net=$1; _db=$2; _hf=$3
    if [ -f "$EXAMPLE" ]; then
        while IFS= read -r line || [ -n "$line" ]; do
            case "$line" in
                satnogs_network_api_key=*) printf '%s\n' "satnogs_network_api_key=$_net" ;;
                satnogs_db_api_key=*)      printf '%s\n' "satnogs_db_api_key=$_db" ;;
                HUGGING_FACE_HUB_TOKEN=*)  printf '%s\n' "HUGGING_FACE_HUB_TOKEN=$_hf" ;;
                *)                         printf '%s\n' "$line" ;;
            esac
        done < "$EXAMPLE" > "$ENV_FILE"
    else
        # Fallback if the template is missing for any reason.
        {
            printf '%s\n' "satnogs_db_api_key=$_db"
            printf '%s\n' "satnogs_network_api_key=$_net"
            printf '%s\n' "HUGGING_FACE_HUB_TOKEN=$_hf"
        } > "$ENV_FILE"
    fi
    chmod 600 "$ENV_FILE"
}

if [ -f "$ENV_FILE" ] && [ "$RECONFIGURE" -eq 0 ]; then
    echo "Using existing .env (pass --reconfigure to re-enter tokens)."
else
    echo "Setting up API tokens. All three are optional — press Enter to skip any."
    ask satnogs_network_api_key "queue polling" \
        "https://network.satnogs.org (Profile -> API key)"
    NETWORK=$REPLY_VALUE
    ask satnogs_db_api_key "decoder evidence frames" \
        "https://db.satnogs.org (Profile -> API key)"
    DB=$REPLY_VALUE
    ask HUGGING_FACE_HUB_TOKEN "model downloads" \
        "https://huggingface.co/settings/tokens"
    HF=$REPLY_VALUE

    write_env "$NETWORK" "$DB" "$HF"
    echo
    echo "Wrote $ENV_FILE"
fi

echo
echo "Starting the stack: docker compose up $*"
exec docker compose up "$@"
