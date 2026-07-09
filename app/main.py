from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import db as ddb
from .config import Settings
from .routes_queue import router as queue_router

APP_DIR = Path(__file__).resolve().parent


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="SatNOGS Observation Review Workbench")
    app.state.settings = settings
    templates = Jinja2Templates(directory=str(APP_DIR / "templates"))
    templates.env.globals["settings"] = settings
    app.state.templates = templates
    app.state.db = ddb.connect(settings.dashboard_db)
    ddb.seed_registry(app.state.db, APP_DIR / "data" / "decoder_registry.toml")
    app.include_router(queue_router)
    app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")

    @app.get("/healthz")
    def healthz() -> dict:
        return {"ok": True}

    return app


app = create_app(Settings.from_env())
