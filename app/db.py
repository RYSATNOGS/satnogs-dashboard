"""dashboard.db: engine result cache, local review events, decoder registry."""
from __future__ import annotations

import json
import sqlite3
import tomllib
from datetime import datetime, timezone
from pathlib import Path

from .models import param_hash

SCHEMA = """
CREATE TABLE IF NOT EXISTS engine_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  engine TEXT NOT NULL,
  obs_id INTEGER NOT NULL,
  param_hash TEXT NOT NULL,
  params_json TEXT NOT NULL,
  engine_version TEXT,
  status TEXT NOT NULL,
  result_json TEXT,
  error TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(engine, obs_id, param_hash)
);
CREATE TABLE IF NOT EXISTS review_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  obs_id INTEGER NOT NULL,
  event TEXT NOT NULL,
  note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_review_obs ON review_events(obs_id, id);
CREATE TABLE IF NOT EXISTS decoder_registry (
  norad INTEGER PRIMARY KEY,
  module TEXT NOT NULL,
  ksy_path TEXT,
  notes TEXT NOT NULL DEFAULT ''
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    return conn


def put_job(conn, engine: str, obs_id: int, params: dict, *, status: str,
            result: dict | None = None, error: str | None = None,
            engine_version: str | None = None) -> None:
    now = _now()
    with conn:
        conn.execute(
            """INSERT INTO engine_results
               (engine, obs_id, param_hash, params_json, engine_version, status,
                result_json, error, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(engine, obs_id, param_hash) DO UPDATE SET
                 status=excluded.status, result_json=excluded.result_json,
                 error=excluded.error, engine_version=excluded.engine_version,
                 updated_at=excluded.updated_at""",
            (engine, obs_id, param_hash(params), json.dumps(params, default=str),
             engine_version, status,
             json.dumps(result) if result is not None else None, error, now, now),
        )


def _row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    d = dict(row)
    d["result"] = json.loads(d.pop("result_json")) if d.get("result_json") else None
    d["params"] = json.loads(d.pop("params_json")) if d.get("params_json") else {}
    return d


def get_result(conn, engine: str, obs_id: int, params: dict) -> dict | None:
    row = conn.execute(
        "SELECT * FROM engine_results WHERE engine=? AND obs_id=? AND param_hash=?",
        (engine, obs_id, param_hash(params)),
    ).fetchone()
    return _row_to_dict(row)


def latest_results(conn, engine: str, obs_id: int) -> dict | None:
    row = conn.execute(
        "SELECT * FROM engine_results WHERE engine=? AND obs_id=? ORDER BY updated_at DESC, id DESC LIMIT 1",
        (engine, obs_id),
    ).fetchone()
    return _row_to_dict(row)


def cached_status_map(conn, engine: str, obs_ids: list[int]) -> dict[int, str]:
    if not obs_ids:
        return {}
    marks = ",".join("?" * len(obs_ids))
    rows = conn.execute(
        f"""SELECT obs_id, status FROM engine_results
            WHERE engine=? AND obs_id IN ({marks}) ORDER BY updated_at, id""",
        (engine, *obs_ids),
    ).fetchall()
    return {r["obs_id"]: r["status"] for r in rows}  # last write wins


def add_review(conn, obs_id: int, event: str, note: str = "") -> None:
    with conn:
        conn.execute(
            "INSERT INTO review_events (obs_id, event, note, created_at) VALUES (?,?,?,?)",
            (obs_id, event, note, _now()),
        )


def review_state(conn, obs_id: int) -> str | None:
    row = conn.execute(
        "SELECT event FROM review_events WHERE obs_id=? ORDER BY id DESC LIMIT 1",
        (obs_id,),
    ).fetchone()
    return row["event"] if row else None


def review_states(conn, obs_ids: list[int]) -> dict[int, str]:
    if not obs_ids:
        return {}
    marks = ",".join("?" * len(obs_ids))
    rows = conn.execute(
        f"SELECT obs_id, event FROM review_events WHERE obs_id IN ({marks}) ORDER BY id",
        obs_ids,
    ).fetchall()
    return {r["obs_id"]: r["event"] for r in rows}


def list_reviews(conn, obs_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM review_events WHERE obs_id=? ORDER BY id DESC", (obs_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def reviewed_obs_ids(conn) -> list[int]:
    """Obs ids with ANY local review event (small, human-marked set)."""
    rows = conn.execute("SELECT DISTINCT obs_id FROM review_events").fetchall()
    return [r["obs_id"] for r in rows]


def seed_registry(conn, toml_path: Path) -> int:
    """Idempotently load registry entries; DB rows win over TOML on re-seed."""
    if not toml_path.exists():
        return 0
    entries = tomllib.loads(toml_path.read_text()).get("satellite", [])
    with conn:
        for e in entries:
            conn.execute(
                """INSERT INTO decoder_registry (norad, module, ksy_path, notes)
                   VALUES (?,?,?,?) ON CONFLICT(norad) DO NOTHING""",
                (int(e["norad"]), e["module"], e.get("ksy_path"), e.get("notes", "")),
            )
    return len(entries)


def registry_lookup(conn, norad: int) -> dict | None:
    row = conn.execute(
        "SELECT * FROM decoder_registry WHERE norad=?", (norad,)
    ).fetchone()
    return dict(row) if row else None
