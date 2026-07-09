"""Create a small fake triage.db for local UI development (not for tests).

Usage: uv run python scripts/dev_seed_signal_db.py [dest.db]

Also the canonical committed home of the fixture schema constants —
tests/fixtures/factories.py imports them from here.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

TRIAGE_SCHEMA = """
CREATE TABLE predictions (
    obs_id          INTEGER PRIMARY KEY,
    norad           INTEGER,
    mode            TEXT,
    station         INTEGER,
    timestamp       TEXT,
    waterfall_url   TEXT,
    p_signal        REAL,
    predicted_label INTEGER,
    scored_at       TEXT
);
"""

DEFAULTS = {
    "norad": 63239, "mode": "FSK", "station": 1234,
    "timestamp": "2026-07-09T00:00:00Z",
    "waterfall_url": "https://example.invalid/waterfall.png",
    "p_signal": 0.9, "predicted_label": 1,
    "scored_at": "2026-07-09T01:00:00Z",
}


def main() -> None:
    dest = Path(sys.argv[1] if len(sys.argv) > 1 else "dev_triage.db")
    dest.unlink(missing_ok=True)
    conn = sqlite3.connect(dest)
    conn.executescript(TRIAGE_SCHEMA)
    for i in range(40):
        r = {**DEFAULTS, "obs_id": 14075700 + i, "norad": 63230 + (i % 5),
             "station": 1000 + (i % 7), "mode": ["FSK", "BPSK", "CW"][i % 3],
             "p_signal": round(1.0 - i * 0.023, 4),
             "predicted_label": 1 if i < 25 else 0}
        conn.execute(
            """INSERT INTO predictions VALUES (:obs_id,:norad,:mode,:station,
               :timestamp,:waterfall_url,:p_signal,:predicted_label,:scored_at)""", r)
    conn.commit()
    print(f"seeded {dest} with 40 rows")


if __name__ == "__main__":
    main()
