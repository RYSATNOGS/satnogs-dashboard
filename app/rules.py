"""Deterministic next-action recommendations. First match wins; every branch
records the evidence it used so the UI can show an explainable trail.
Keep this table editable — it is product policy, not ML."""
from __future__ import annotations


def next_action(obs: dict, identity: dict | None, decode: dict | None,
                review: str | None, *, p_high: float = 0.9,
                p_low: float = 0.5) -> dict:
    p = obs.get("p_signal") or 0.0
    reasons: list[str] = [f"P(signal) = {p}"]

    if review in ("reviewed", "vetted_on_satnogs"):
        reasons.append(f"local review state: {review}")
        return {"action": "done — already reviewed locally", "reasons": reasons}

    if p < p_low:
        reasons.append(f"below low threshold {p_low}")
        return {"action": "deprioritize — likely noise", "reasons": reasons}

    tag = (identity or {}).get("name_tag") or {}
    if tag.get("tier") == "DISAGREES":
        reasons.append(f"name-tag disagrees: {tag.get('reason')}")
        return {"action": "inspect likely sibling object — decoded names disagree "
                          "with Doppler ID", "reasons": reasons}

    if identity and (identity.get("status") == "ambiguous" or identity.get("ambiguous")):
        reasons.append("identity ambiguous (runner-up margin below threshold)")
        return {"action": "wait for another pass — identity ambiguous "
                          "(or rerun identify with a launch designator)",
                "reasons": reasons}

    if identity is None and decode is None and p < p_high:
        # mid-band with no cached evidence: not worth an engine run yet
        reasons.append("mid-confidence signal with no blocking evidence")
        return {"action": "human eyeball — mid-confidence signal", "reasons": reasons}
    if identity is None:
        reasons.append("no identity evidence cached")
        return {"action": "run Doppler identify", "reasons": reasons}
    if identity.get("status") in ("rate_limited", "no_track", "missing_h5", "failed"):
        reasons.append(f"identity state: {identity.get('status')}")
        return {"action": f"retry identify later — last attempt: "
                          f"{identity.get('status')}", "reasons": reasons}

    if decode is None:
        reasons.append(f"identity ok (NORAD {identity.get('best_norad')}), "
                       "no decode evidence cached")
        return {"action": "run decoder checks", "reasons": reasons}

    status = decode.get("status")
    cc = decode.get("crosscheck") or {}
    if status == "known_decoder" and cc and "pass" not in str(cc.get("status", "")):
        reasons.append(f"cross-check {cc.get('status')} at agreement {cc.get('agreement')}")
        return {"action": "investigate decoder failure — cross-check failing",
                "reasons": reasons}
    if status == "known_decoder":
        reasons.append("known decoder decodes frames"
                       + (f", cross-check {cc.get('status')}" if cc else ""))
        return {"action": "vet on SatNOGS — signal, identity, and decode all support it",
                "reasons": reasons}
    if status == "inferred_hints":
        reasons.append("only inferred structure hints exist (assistive, not a decoder)")
        return {"action": "maintainer review — inferred structure hints available "
                          "(not a decoder)", "reasons": reasons}
    if status == "raw_frames":
        reasons.append(f"{decode.get('frame_count')} raw frames, no decoder support")
        return {"action": "candidate for new decoder work — frames exist without "
                          "decoder support", "reasons": reasons}
    if status == "no_frames":
        reasons.append("no telemetry frames stored for this window")
        return {"action": "vet on SatNOGS from waterfall evidence — no frames stored",
                "reasons": reasons}
    if status in ("no_token", "failed"):
        reasons.append(f"decoder tooling problem: {decode.get('error')}")
        return {"action": f"fix decoder tooling — {decode.get('error')}",
                "reasons": reasons}

    reasons.append("mid-confidence signal with no blocking evidence")
    return {"action": "human eyeball — mid-confidence signal", "reasons": reasons}
