from __future__ import annotations

from fastapi import APIRouter, Request

from . import db as ddb
from .adapters import signal

router = APIRouter()


def _int_or_none(v: str | None) -> int | None:
    try:
        return int(v) if v not in (None, "") else None
    except ValueError:
        return None


def _float_or_none(v: str | None) -> float | None:
    try:
        return float(v) if v not in (None, "") else None
    except ValueError:
        return None


@router.get("/")
def queue_page(request: Request, min_p: str | None = None, norad: str | None = None,
               station: str | None = None, mode: str | None = None,
               label: str | None = None, reviewed: str = "any"):
    s = request.app.state.settings
    templates = request.app.state.templates
    conn = request.app.state.db
    obs_in = obs_not_in = None
    if reviewed == "yes":
        obs_in = ddb.reviewed_obs_ids(conn)
    elif reviewed == "no":
        obs_not_in = ddb.reviewed_obs_ids(conn)
    try:
        rows = signal.queue(
            s.signal_db, limit=s.queue_limit,
            min_p=_float_or_none(min_p),
            norad=_int_or_none(norad), station=_int_or_none(station),
            mode=mode or None, label=_int_or_none(label),
            obs_in=obs_in, obs_not_in=obs_not_in,
        )
        store_stats = signal.stats(s.signal_db)
        setup_error = None
    except signal.SignalStoreMissing as exc:
        rows, store_stats, setup_error = [], {"n": 0, "n_signal": 0}, str(exc)

    ids = [r["obs_id"] for r in rows]
    identity_map = ddb.cached_status_map(conn, "identity", ids)
    decoder_map = ddb.cached_status_map(conn, "decoder", ids)
    review_map = ddb.review_states(conn, ids)
    for r in rows:
        p = r["p_signal"]
        r["band"] = "hi" if p >= s.p_high else ("mid" if p >= s.p_low else "lo")
        r["identity_status"] = identity_map.get(r["obs_id"])
        r["decoder_status"] = decoder_map.get(r["obs_id"])
        r["review"] = review_map.get(r["obs_id"])

    return templates.TemplateResponse(request, "queue.html", {
        "rows": rows, "stats": store_stats, "setup_error": setup_error,
        "filters": {"min_p": min_p or "", "norad": norad or "", "station": station or "",
                    "mode": mode or "", "label": label or "", "reviewed": reviewed},
    })
