from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from . import db as ddb, rules
from .adapters import signal

router = APIRouter()

PANELS = ("signal", "related", "meta", "identity", "decode", "review", "next_action")


def load_obs(request: Request, obs_id: int) -> dict | None:
    s = request.app.state.settings
    try:
        return signal.get_row(s.signal_db, obs_id)
    except signal.SignalStoreMissing:
        return None


def _panel_context(request: Request, obs_id: int, panel: str) -> dict:
    s = request.app.state.settings
    conn = request.app.state.db
    obs = load_obs(request, obs_id)
    ctx: dict = {"obs": obs, "obs_id": obs_id, "panel": panel}
    if obs is None:
        return ctx
    if panel == "signal":
        p = obs["p_signal"]
        ctx["band"] = "hi" if p >= s.p_high else ("mid" if p >= s.p_low else "lo")
    elif panel == "related":
        ctx["related"] = signal.by_norad(s.signal_db, obs["norad"], exclude_obs=obs_id)
    elif panel == "meta":
        cached = ddb.get_result(conn, "network_meta", obs_id, {"v": 1})
        ctx["meta"] = cached["result"] if cached and cached.get("result") else None
    elif panel == "identity":
        ctx["job"] = ddb.latest_results(conn, "identity", obs_id)
    elif panel == "decode":
        ctx["job"] = ddb.latest_results(conn, "decoder", obs_id)
        ctx["registry"] = (ddb.registry_lookup(conn, obs["norad"])
                          if obs and obs.get("norad") is not None else None)
    elif panel == "review":
        ctx["events"] = ddb.list_reviews(conn, obs_id)
    elif panel == "next_action":
        ident_row = ddb.latest_results(conn, "identity", obs_id)
        dec_row = ddb.latest_results(conn, "decoder", obs_id)
        ctx["recommendation"] = rules.next_action(
            obs,
            (ident_row or {}).get("result"),
            (dec_row or {}).get("result"),
            ddb.review_state(conn, obs_id),
            p_high=s.p_high, p_low=s.p_low)
    return ctx


def _panel_response(request: Request, obs_id: int, panel: str) -> HTMLResponse:
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request, f"partials/panel_{panel}.html", _panel_context(request, obs_id, panel))


@router.get("/observations/{obs_id}/analysis")
def analysis_page(request: Request, obs_id: int):
    templates = request.app.state.templates
    obs = load_obs(request, obs_id)
    if obs is None:
        return HTMLResponse(
            f"<h1>Observation {obs_id} is not in the signal store</h1>"
            "<p>Only observations scored by satnogs-signal appear here. "
            'Return to the <a href="/">queue</a>.</p>', status_code=404)
    conn = request.app.state.db
    cached_meta = ddb.get_result(conn, "network_meta", obs_id, {"v": 1})
    meta = cached_meta["result"] if cached_meta and cached_meta.get("result") else None
    waterfall = obs["waterfall_url"] or (meta or {}).get("waterfall")
    return templates.TemplateResponse(request, "analysis.html", {
        "obs": obs, "obs_id": obs_id, "waterfall": waterfall, "panels": PANELS})


@router.get("/observations/{obs_id}/panels/{panel}")
def panel(request: Request, obs_id: int, panel: str):
    if panel not in PANELS:
        return HTMLResponse("unknown panel", status_code=404)
    return _panel_response(request, obs_id, panel)
