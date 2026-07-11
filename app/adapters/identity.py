"""Runs the identity JSON runner (inside the satnogs-id container) and
normalizes its output into UI-ready states.

States: ok | ambiguous | rate_limited | no_track | missing_h5 | failed.
no_track / missing_h5 are recovered from error text because the engine
raises untyped exceptions for them (keyword mapping is a documented MVP
pragmatism — see docs/MVP_ARCHITECTURE.md 'Risks').
"""
from __future__ import annotations

import json
import re
import subprocess

NO_TRACK_RE = re.compile(r"no usable track|no points|track", re.I)
MISSING_H5_RE = re.compile(r"h5|artifact", re.I)


def params_for(intdes: str | None, catalog: str | None) -> dict:
    return {"intdes": intdes, "catalog": catalog}


def run_identify(settings, obs_id: int, *, intdes: str | None = None,
                 catalog: str | None = None) -> tuple[dict, str | None]:
    argv = [*settings.identity_cmd, str(obs_id)]
    if intdes:
        argv += ["--intdes", intdes]
    if catalog:
        argv += ["--catalog", catalog]
    proc = subprocess.run(argv, capture_output=True, text=True,
                          timeout=settings.job_timeout_s)
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip()[-500:]
        raise RuntimeError(f"identity runner exit {proc.returncode}: {tail}")
    lines = [ln for ln in proc.stdout.strip().splitlines() if ln.strip()]
    try:
        result = json.loads(lines[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"identity runner produced no JSON: {proc.stdout[-300:]}") from exc

    if result.get("status") == "failed":
        err = result.get("error", "")
        if MISSING_H5_RE.search(err):
            result["status"] = "missing_h5"
        elif NO_TRACK_RE.search(err):
            result["status"] = "no_track"
    return result, result.get("engine_version")
