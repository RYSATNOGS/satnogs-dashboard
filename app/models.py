"""Shared constants and small helpers for job/result records."""
from __future__ import annotations

import hashlib
import json

QUEUED = "queued"
RUNNING = "running"
DONE = "done"
FAILED = "failed"


def param_hash(params: dict) -> str:
    canon = json.dumps(params, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canon.encode()).hexdigest()[:16]
