"""JSON wrapper around satnogs_id.service.forward.identify_observation().

MUST run inside the satnogs-id environment (its Docker container bundles
strf/rffit). The dashboard invokes it via IDENTITY_CMD and parses stdout.
Exit code 0 whenever a JSON object was printed — engine failures are states.
"""
from __future__ import annotations

import argparse
import json
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("obs_id", type=int)
    ap.add_argument("--intdes", default=None)
    ap.add_argument("--catalog", default=None)
    args = ap.parse_args()

    from satnogs_id.shared.api import RateLimited

    try:
        from satnogs_id.service.forward import identify_observation
        fid = identify_observation(args.obs_id, intdes=args.intdes, catalog=args.catalog)
        out = {
            "obs_id": args.obs_id,
            "status": "ambiguous" if fid.ambiguous else "ok",
            "best_norad": fid.best,
            "ambiguous": fid.ambiguous,
            "margin_khz": fid.margin_khz,
            "epoch_gap_days": fid.epoch_gap_days,
            "n_points": fid.n_points,
            "ranking": [{"norad": n, "rms_khz": round(r, 3)} for r, n in fid.result.ranking],
            "name_tag": None if fid.name_tag is None else {
                "tier": fid.name_tag.tier,
                "norad": fid.name_tag.norad,
                "agrees": fid.name_tag.agrees,
                "reason": fid.name_tag.reason,
            },
            "engine_version": "satnogs-id@container",
        }
    except RateLimited as exc:
        out = {"obs_id": args.obs_id, "status": "rate_limited", "error": str(exc)}
    except Exception as exc:  # no-track / missing-h5 / anything: report, don't crash
        out = {"obs_id": args.obs_id, "status": "failed",
               "error": f"{type(exc).__name__}: {exc}"}

    json.dump(out, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
