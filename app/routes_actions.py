from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from .adapters import identity
from .routes_analysis import _panel_response

router = APIRouter()


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
