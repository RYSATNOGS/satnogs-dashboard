# Owner rule: NO venv inside the repo. The uv project environment lives
# outside the tree; every uv invocation goes through these targets (or
# exports UV_PROJECT_ENVIRONMENT itself).
UV_PROJECT_ENVIRONMENT ?= $(HOME)/.local/share/uv-project-envs/satnogs-dashboard
export UV_PROJECT_ENVIRONMENT
# Owner standard: python 3.14 everywhere (matches the python:3.14-slim siblings)
export UV_PYTHON = 3.14

.PHONY: up test dev seed lock

# The deployment path: build all four images, start all four containers.
up:
	docker compose up --build

test:
	uv run --extra dev pytest $(ARGS)

dev:
	uv run uvicorn app.main:app_factory --factory --reload

seed:
	uv run python scripts/dev_seed_signal_db.py dev_triage.db

lock:
	uv lock
