from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Form, Request
from fastapi.responses import (HTMLResponse, JSONResponse, PlainTextResponse,
                               RedirectResponse)

from . import db as ddb, rules
from .adapters import decoder, identity, satnogs_network
from .routes_analysis import _panel_response, load_obs

router = APIRouter()

REVIEW_EVENTS = ("seen", "reviewed", "needs_decoder_review",
                 "identity_ambiguous", "vetted_on_satnogs")


def _respond(request: Request, obs_id: int, panel: str):
    if request.headers.get("HX-Request"):
        return _panel_response(request, obs_id, panel)
    return RedirectResponse(f"/observations/{obs_id}/analysis", status_code=303)


@router.post("/observations/{obs_id}/actions/identify")
def action_identify(request: Request, obs_id: int, intdes: str = Form(""),
                    catalog: str = Form(""), rerun: str = Form("")):
    s = request.app.state.settings
    params = identity.params_for(intdes or None, catalog or None)
    request.app.state.jobs.submit(
        "identity", obs_id, params,
        lambda: identity.run_identify(s, obs_id, intdes=intdes or None,
                                      catalog=catalog or None),
        rerun=rerun == "1")
    return _respond(request, obs_id, "identity")


@router.post("/observations/{obs_id}/actions/decode_check")
def action_decode(request: Request, obs_id: int, rerun: str = Form(""),
                  infer: str = Form("")):
    s = request.app.state.settings
    conn = request.app.state.db
    obs = load_obs(request, obs_id)
    if obs is None:
        return _respond(request, obs_id, "decode")
    cached_meta = ddb.get_result(conn, "network_meta", obs_id, {"v": 1})
    meta = cached_meta["result"] if cached_meta and cached_meta.get("result") else None
    start, end = decoder.window_for(obs, meta)
    entry = ddb.registry_lookup(conn, obs["norad"]) if obs.get("norad") is not None else None
    module = entry["module"] if entry else None
    ksy_path = entry.get("ksy_path") if entry else None
    params = decoder.params_for(obs["norad"], start, end, module, infer == "1")
    request.app.state.jobs.submit(
        "decoder", obs_id, params,
        lambda: decoder.run_decode(s, obs_id, norad=obs["norad"], start=start,
                                   end=end, module=module, ksy_path=ksy_path,
                                   infer=infer == "1"),
        rerun=rerun == "1")
    return _respond(request, obs_id, "decode")


@router.get("/observations/{obs_id}/artifacts/ksy")
def ksy_artifact(request: Request, obs_id: int):
    row = ddb.latest_results(request.app.state.db, "decoder", obs_id)
    hints = (row or {}).get("result") or {}
    hints = hints.get("structure_hints") or {}
    if not hints.get("ksy_text"):
        return PlainTextResponse("no inferred ksy cached for this observation",
                                 status_code=404)
    return PlainTextResponse(hints["ksy_text"], headers={
        "Content-Disposition":
            f"attachment; filename=obs{obs_id}_inferred_REVIEW_ONLY.ksy"})


@router.post("/observations/{obs_id}/actions/mark")
def action_mark(request: Request, obs_id: int, event: str = Form(...),
                note: str = Form("")):
    if event not in REVIEW_EVENTS:
        return HTMLResponse("unknown review event", status_code=400)
    ddb.add_review(request.app.state.db, obs_id, event, note)
    return _respond(request, obs_id, "review")


@router.post("/observations/{obs_id}/actions/refresh_meta")
def action_refresh_meta(request: Request, obs_id: int):
    s = request.app.state.settings
    try:
        satnogs_network.get_observation(request.app.state.db, s, obs_id, force=True)
    except satnogs_network.NetworkUnavailable as exc:
        return HTMLResponse(
            f'<div class="panel" id="panel-meta"><h3>observation metadata</h3>'
            f'<p><span class="chip mid">network unavailable</span> {exc.reason}</p>'
            f'<p class="muted">Cached data (if any) is still shown after reload.</p></div>')
    return _respond(request, obs_id, "meta")


@router.get("/observations/{obs_id}/export.json")
def export_bundle(request: Request, obs_id: int):
    obs = load_obs(request, obs_id)
    if obs is None:
        return JSONResponse({"error": "unknown observation"}, status_code=404)
    conn = request.app.state.db
    meta_row = ddb.get_result(conn, "network_meta", obs_id, {"v": 1})
    return JSONResponse({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "observation": obs,
        "network_meta": meta_row["result"] if meta_row else None,
        "engine_results": {
            "identity": ddb.latest_results(conn, "identity", obs_id),
            "decoder": ddb.latest_results(conn, "decoder", obs_id),
        },
        "review_events": ddb.list_reviews(conn, obs_id),
        "next_action": rules.next_action(
            obs,
            (ddb.latest_results(conn, "identity", obs_id) or {}).get("result"),
            (ddb.latest_results(conn, "decoder", obs_id) or {}).get("result"),
            ddb.review_state(conn, obs_id),
            p_high=request.app.state.settings.p_high,
            p_low=request.app.state.settings.p_low),
    })
