"""Read-only adapter over satnogs-signal's triage.db (the queue source of truth)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

NETWORK_OBS_URL = "https://network.satnogs.org/observations/{obs_id}/"


class SignalStoreMissing(Exception):
    """triage.db is absent — a setup state, not a crash."""


def _connect_ro(db_path: Path) -> sqlite3.Connection:
    if not Path(db_path).exists():
        raise SignalStoreMissing(f"signal store not found at {db_path}")
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _map_row(r: sqlite3.Row) -> dict:
    return {
        "obs_id": r["obs_id"],
        "satnogs_url": NETWORK_OBS_URL.format(obs_id=r["obs_id"]),
        "norad": r["norad"],
        "mode": r["mode"],
        "station": r["station"],
        "timestamp": r["timestamp"],
        "waterfall_url": r["waterfall_url"],
        "p_signal": r["p_signal"],
        "signal_label": "likely_signal" if r["predicted_label"] == 1 else "likely_noise",
        "scored_at": r["scored_at"],
    }


def queue(db_path: Path, *, limit: int = 200, min_p: float | None = None,
          norad: int | None = None, station: int | None = None,
          mode: str | None = None, label: int | None = None) -> list[dict]:
    conn = _connect_ro(db_path)
    try:
        clauses = ["obs_id IS NOT NULL", "p_signal IS NOT NULL"]
        args: list = []
        if min_p is not None:
            clauses.append("p_signal >= ?"); args.append(min_p)
        if norad is not None:
            clauses.append("norad = ?"); args.append(norad)
        if station is not None:
            clauses.append("station = ?"); args.append(station)
        if mode is not None:
            clauses.append("mode = ?"); args.append(mode)
        if label is not None:
            clauses.append("predicted_label = ?"); args.append(label)
        rows = conn.execute(
            f"""SELECT * FROM predictions WHERE {' AND '.join(clauses)}
                ORDER BY p_signal DESC, obs_id DESC LIMIT ?""",
            (*args, limit),
        ).fetchall()
        return [_map_row(r) for r in rows]
    finally:
        conn.close()


def get_row(db_path: Path, obs_id: int) -> dict | None:
    conn = _connect_ro(db_path)
    try:
        r = conn.execute("SELECT * FROM predictions WHERE obs_id=?", (obs_id,)).fetchone()
        return _map_row(r) if r else None
    finally:
        conn.close()


def by_norad(db_path: Path, norad: int, *, exclude_obs: int | None = None,
             limit: int = 10) -> list[dict]:
    rows = queue(db_path, norad=norad, limit=limit + 1)
    return [r for r in rows if r["obs_id"] != exclude_obs][:limit]


def stats(db_path: Path) -> dict:
    conn = _connect_ro(db_path)
    try:
        r = conn.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(predicted_label),0) AS n_signal FROM predictions"
        ).fetchone()
        return {"n": r["n"], "n_signal": r["n_signal"]}
    finally:
        conn.close()
