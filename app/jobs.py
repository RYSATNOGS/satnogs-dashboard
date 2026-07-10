"""Button-driven engine jobs: in-process thread pool + dashboard.db-backed state.

Single-user local tool: a ThreadPoolExecutor is deliberate — no queue service.
Dedupe key is (engine, obs_id, param_hash); reruns must be explicit so users
know when they are replacing cached evidence (spec requirement).
"""
from __future__ import annotations

import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Callable

from . import db as ddb
from .models import DONE, FAILED, QUEUED, RUNNING, param_hash


class JobRunner:
    def __init__(self, conn, workers: int = 2):
        self._conn = conn
        self._pool = ThreadPoolExecutor(max_workers=workers)
        self._lock = threading.Lock()
        self._futures: dict[tuple[str, int, str], Future] = {}

    def status(self, engine: str, obs_id: int, params: dict) -> dict | None:
        return ddb.get_result(self._conn, engine, obs_id, params)

    def submit(self, engine: str, obs_id: int, params: dict,
               fn: Callable[[], tuple[dict, str | None]], *, rerun: bool = False) -> dict:
        key = (engine, obs_id, param_hash(params))
        with self._lock:
            fut = self._futures.get(key)
            if fut is not None and not fut.done():
                return self.status(engine, obs_id, params)
            row = self.status(engine, obs_id, params)
            if row and row["status"] in (QUEUED, RUNNING) and fut is not None:
                return row
            if row and row["status"] == DONE and not rerun:
                return row
            ddb.put_job(self._conn, engine, obs_id, params, status=QUEUED)
            self._futures[key] = self._pool.submit(self._run, engine, obs_id, params, fn)
        return self.status(engine, obs_id, params)

    def _run(self, engine: str, obs_id: int, params: dict,
             fn: Callable[[], tuple[dict, str | None]]) -> None:
        key = (engine, obs_id, param_hash(params))
        try:
            ddb.put_job(self._conn, engine, obs_id, params, status=RUNNING)
            result, version = fn()
            ddb.put_job(self._conn, engine, obs_id, params, status=DONE,
                        result=result, engine_version=version)
        except Exception as exc:  # engine failures become normal UI states
            try:
                ddb.put_job(self._conn, engine, obs_id, params,
                            status=FAILED, error=str(exc))
            except Exception:
                pass  # DB unavailable: eviction below still unblocks resubmission
        finally:
            with self._lock:
                self._futures.pop(key, None)

    def shutdown(self) -> None:
        self._pool.shutdown(wait=True, cancel_futures=True)
