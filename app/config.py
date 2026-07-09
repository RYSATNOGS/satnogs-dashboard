"""Env-driven settings. Exact env names come from docs/MVP_ARCHITECTURE.md."""
from __future__ import annotations

import os
import shlex
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _default_identity_cmd(id_dir: Path) -> list[str]:
    return shlex.split(
        f"docker compose -f {id_dir}/docker-compose.yml run --rm -T "
        f"-v {SCRIPTS_DIR}:/runner app python /runner/run_identity_json.py"
    )


def _default_decoder_cmd(decoder_dir: Path) -> list[str]:
    return shlex.split(
        f"docker compose -f {decoder_dir}/compose.yaml run --rm -T "
        f"-v {SCRIPTS_DIR}:/runner app python /runner/run_decoder_json.py"
    )


@dataclass
class Settings:
    signal_db: Path
    dashboard_db: Path
    id_dir: Path
    decoder_dir: Path
    identity_cmd: list[str] = field(default_factory=list)  # empty -> derive from id_dir
    decoder_cmd: list[str] = field(default_factory=list)
    network_base: str = "https://network.satnogs.org/api"
    network_token: str = ""
    network_ttl_hours: float = 24.0
    p_high: float = 0.9
    p_low: float = 0.5
    queue_limit: int = 200
    job_workers: int = 2
    job_timeout_s: int = 1800
    signal_model_note: str = (
        "Signal model is validated on a limited satellite set; "
        "scores for unsupported satellites are unreliable."
    )

    def __post_init__(self) -> None:
        if not self.identity_cmd:
            self.identity_cmd = _default_identity_cmd(self.id_dir)
        if not self.decoder_cmd:
            self.decoder_cmd = _default_decoder_cmd(self.decoder_dir)

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.environ
        siblings = REPO_ROOT.parent
        id_dir = Path(env.get("SATNOGS_ID_DIR", siblings / "satnogs-id"))
        decoder_dir = Path(env.get("SATNOGS_DECODER_DIR", siblings / "satnogs-decoder"))
        return cls(
            signal_db=Path(env.get("SATNOGS_SIGNAL_DB", siblings / "satnogs-signal" / "triage.db")),
            dashboard_db=Path(env.get("DASHBOARD_DB", REPO_ROOT / "dashboard.db")),
            id_dir=id_dir,
            decoder_dir=decoder_dir,
            identity_cmd=shlex.split(env.get("IDENTITY_CMD", "")),
            decoder_cmd=shlex.split(env.get("DECODER_CMD", "")),
            network_token=env.get("SATNOGS_NETWORK_TOKEN", ""),
            network_ttl_hours=float(env.get("NETWORK_TTL_HOURS", "24")),
            p_high=float(env.get("P_HIGH", "0.9")),
            p_low=float(env.get("P_LOW", "0.5")),
            queue_limit=int(env.get("QUEUE_LIMIT", "200")),
            job_workers=int(env.get("JOB_WORKERS", "2")),
            job_timeout_s=int(env.get("JOB_TIMEOUT_S", "1800")),
        )
