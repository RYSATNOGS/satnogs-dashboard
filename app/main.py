from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import Settings

APP_DIR = Path(__file__).resolve().parent


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="SatNOGS Observation Review Workbench")
    app.state.settings = settings
    templates = Jinja2Templates(directory=str(APP_DIR / "templates"))
    templates.env.globals["settings"] = settings
    app.state.templates = templates
    app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")

    @app.get("/healthz")
    def healthz() -> dict:
        return {"ok": True}

    return app


app = create_app(Settings.from_env())
