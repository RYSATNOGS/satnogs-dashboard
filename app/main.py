from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import db as ddb
from .config import Settings
from .jobs import JobRunner
from .routes_actions import router as actions_router
from .routes_analysis import router as analysis_router
from .routes_queue import router as queue_router

APP_DIR = Path(__file__).resolve().parent


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="SatNOGS Observation Review Workbench")
    app.state.settings = settings
    templates = Jinja2Templates(directory=str(APP_DIR / "templates"))
    templates.env.globals["settings"] = settings
    app.state.templates = templates
    app.state.db = ddb.connect(settings.dashboard_db)
    app.state.jobs = JobRunner(app.state.db, settings.job_workers)
    ddb.seed_registry(app.state.db, APP_DIR / "data" / "decoder_registry.toml")
    app.include_router(queue_router)
    app.include_router(analysis_router)
    app.include_router(actions_router)
    app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")

    @app.get("/healthz")
    def healthz() -> dict:
        return {"ok": True}

    return app


def app_factory() -> FastAPI:
    """Composition root for `uvicorn app.main:app_factory --factory` (make dev).

    Env reading and dashboard.db creation happen here, never at import time.
    """
    return create_app(Settings.from_env())
