"""Button-driven engine jobs: in-process thread pool + dashboard.db-backed state.

Single-user local tool: a ThreadPoolExecutor is deliberate — no queue service.
Dedupe key is (engine, obs_id, param_hash); reruns must be explicit so users
know when they are replacing cached evidence (spec requirement).
"""
from __future__ import annotations

import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from functools import partial
from typing import Callable

from . import db as ddb
from .models import DONE, FAILED, QUEUED, RUNNING, param_hash

log = logging.getLogger(__name__)


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
            fut = self._pool.submit(self._run, engine, obs_id, params, fn)
            fut.add_done_callback(partial(self._surface_crash, key))
            self._futures[key] = fut
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
            # this FAILED write may itself raise (DB gone): eviction below
            # still unblocks resubmission and _surface_crash logs the escape
            ddb.put_job(self._conn, engine, obs_id, params,
                        status=FAILED, error=str(exc))
        finally:
            with self._lock:
                self._futures.pop(key, None)

    @staticmethod
    def _surface_crash(key: tuple[str, int, str], fut: Future) -> None:
        """Nothing calls .result() on these futures: an exception escaping
        _run (e.g. the FAILED write itself dying) would otherwise vanish
        with the job stuck in a non-terminal status."""
        if fut.cancelled():
            return
        exc = fut.exception()
        if exc is not None:
            log.error("job crashed without recording a status: %s", key, exc_info=exc)

    def shutdown(self) -> None:
        self._pool.shutdown(wait=True, cancel_futures=True)
