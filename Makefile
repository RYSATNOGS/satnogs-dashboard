# Owner rule: NO venv inside the repo. The uv project environment lives
# outside the tree; every uv invocation goes through these targets (or
# exports UV_PROJECT_ENVIRONMENT itself).
UV_PROJECT_ENVIRONMENT ?= $(HOME)/.local/share/uv-project-envs/satnogs-dashboard
export UV_PROJECT_ENVIRONMENT
.PHONY: up test dev seed

# The deployment path: build all four images, start all four containers.
up:
	docker compose up --build

test:
	uv run --upgrade --extra dev pytest $(ARGS)

dev:
	uv run --upgrade uvicorn app.main:app_factory --factory --reload

seed:
	uv run --upgrade python scripts/dev_seed_signal_db.py dev_triage.db
