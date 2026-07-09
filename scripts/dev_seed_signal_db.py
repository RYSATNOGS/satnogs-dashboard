"""Create a small fake triage.db for local UI development (not for tests).

Usage: uv run python scripts/dev_seed_signal_db.py [dest.db]
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.fixtures.factories import TRIAGE_SCHEMA, DEFAULTS  # noqa: E402


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
