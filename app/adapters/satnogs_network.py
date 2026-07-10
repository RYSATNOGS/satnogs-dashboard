"""Read-only SatNOGS Network metadata with dashboard.db-backed TTL cache.

Endpoint (verified against satnogs-id's client 2026-07-09):
GET {base}/observations/?id={obs_id}&format=json -> JSON list, element 0.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from .. import db as ddb

ENGINE = "network_meta"
PARAMS = {"v": 1}


class NetworkUnavailable(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _map(raw: dict, obs_id: int) -> dict:
    return {
        "obs_id": obs_id,
        "start": raw.get("start"),
        "end": raw.get("end"),
        "station_name": raw.get("station_name"),
        "transmitter_mode": raw.get("transmitter_mode"),
        "norad_cat_id": raw.get("norad_cat_id"),
        "waterfall": raw.get("waterfall"),
        "vetted_status": raw.get("vetted_status"),
        "observer_url": f"https://network.satnogs.org/observations/{obs_id}/",
    }


def _fresh(cached: dict | None, ttl_hours: float) -> bool:
    if not cached or cached.get("status") != "done" or cached.get("result") is None:
        return False
    updated = datetime.fromisoformat(cached["updated_at"])
    return datetime.now(timezone.utc) - updated < timedelta(hours=ttl_hours)


def get_observation(conn, settings, obs_id: int, *, http: httpx.Client | None = None,
                    force: bool = False) -> dict | None:
    cached = ddb.get_result(conn, ENGINE, obs_id, PARAMS)
    if not force and _fresh(cached, settings.network_ttl_hours):
        return cached["result"]

    client = http or httpx.Client(timeout=20)
    headers = {"User-Agent": "satnogs-dashboard/0.1 (review workbench; read-only)"}
    if settings.network_token:
        headers["Authorization"] = f"Token {settings.network_token}"
    url = f"{settings.network_base}/observations/?id={obs_id}&format=json"
    try:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
        payload = resp.json()
    except httpx.HTTPError as exc:
        if cached and cached.get("result") is not None:
            return cached["result"]  # stale beats broken
        raise NetworkUnavailable(f"SatNOGS Network fetch failed: {exc}") from exc
    finally:
        if http is None:
            client.close()

    if not payload:
        return None
    meta = _map(payload[0], obs_id)
    ddb.put_job(conn, ENGINE, obs_id, PARAMS, status="done", result=meta)
    return meta
