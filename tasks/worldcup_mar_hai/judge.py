"""Per-case judge for the worldcup_betting task — calibration + realized P&L.

Reads the agent's stdout (a probability distribution over {home, draw, away}),
the actual result and (when available) the frozen odds from expected/<id>/answer.json,
and emits a metrics JSON on stdout (trap stores it as CaseResult.metrics).

Per graded case:
  - log_loss : -ln(p_actual), the calibration signal (lower is better).
  - brier    : Σ(p_o - y_o)^2, bounded [0,2] calibration signal, robust on small n.
  - score    : 1.0 if the model's argmax outcome was the actual result, else 0.0
               (a simple "did it call it" accuracy proxy; works even before odds
               are back-filled, since it doesn't need odds).
  - profit / staked / returned : realized P&L from a fixed flat-stake +EV rule —
               ONLY emitted once odds are present. Bet $1 on every outcome where
               p*odds > 1; a winning bet returns `odds`, else 0.

States:
  - match not yet played (graded != true)  -> score = null (pending; grader skips).
  - graded, odds still null                -> calibration + score, ROI fields omitted.
  - graded, odds present                   -> calibration + score + ROI.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

OUTCOMES = ("home", "draw", "away")
_EPS = 1e-15


def parse_probs(stdout: str) -> dict | None:
    """Parse stdout into {home,draw,away} probabilities, renormalized to sum 1.

    Accepts a bare JSON object or `{"answer": "<json string>"}`. Returns None if
    the answer can't be parsed, is missing an outcome, has a negative value, or
    sums to <= 0.
    """
    s = (stdout or "").strip()
    if not s:
        return None
    try:
        obj = json.loads(s)
    except json.JSONDecodeError:
        return None
    if isinstance(obj, dict) and "answer" in obj and not all(k in obj for k in OUTCOMES):
        inner = obj["answer"]
        if isinstance(inner, str):
            try:
                obj = json.loads(inner)
            except json.JSONDecodeError:
                return None
    if not isinstance(obj, dict):
        return None
    try:
        vals = {k: float(obj[k]) for k in OUTCOMES}
    except (KeyError, TypeError, ValueError):
        return None
    if any(v < 0 for v in vals.values()):
        return None
    total = sum(vals.values())
    if total <= 0:
        return None
    return {k: v / total for k, v in vals.items()}


def log_loss(probs: dict, result: str) -> float:
    """-ln(p_actual), with p clamped to [_EPS, 1] to avoid infinities."""
    p = max(_EPS, min(1.0, probs[result]))
    return -math.log(p)


def brier_score(probs: dict, result: str) -> float:
    """Multiclass Brier: Σ_o (p_o - y_o)^2, bounded [0, 2]."""
    return sum((probs[o] - (1.0 if o == result else 0.0)) ** 2 for o in OUTCOMES)


def settle_bets(probs: dict, odds: dict, result: str) -> tuple[float, float]:
    """Flat $1 stake on every +EV outcome; return (staked, returned).

    A bet on outcome o is placed when probs[o] * odds[o] > 1. A winning bet (o ==
    result) returns odds[o]; a losing bet returns 0.
    """
    staked = 0.0
    returned = 0.0
    for o in OUTCOMES:
        if probs[o] * odds[o] > 1.0:
            staked += 1.0
            if o == result:
                returned += odds[o]
    return staked, returned


def main() -> None:
    payload = json.loads(os.environ["TRAPTASK_PAYLOAD"])
    stdout = Path(payload["outputs"]["case_stdout"]).read_text()
    exit_code = json.loads(Path(payload["outputs"]["case_meta.json"]).read_text())["exit_code"]
    expected = json.loads(Path(payload["expected"]["answer.json"]).read_text())

    base = {
        "id": expected.get("id"),
        "type": expected.get("type"),
        "home_team": expected.get("home_team"),
        "away_team": expected.get("away_team"),
    }

    # Not yet played — nothing to grade.
    if not expected.get("graded") or expected.get("result") is None:
        print(json.dumps({"score": None, "reason": "match not yet graded", **base}))
        return

    if exit_code != 0:
        print(json.dumps({"score": 0.0, "reason": f"solution exited {exit_code}", **base}))
        return

    probs = parse_probs(stdout)
    if probs is None:
        print(json.dumps({"score": 0.0, "reason": "could not parse probabilities",
                          "agent_answer": (stdout or "")[:300], **base}))
        return

    result = expected["result"]
    ll = log_loss(probs, result)
    brier = brier_score(probs, result)
    top_pick = max(OUTCOMES, key=lambda o: probs[o])

    out = {
        "score": 1.0 if top_pick == result else 0.0,
        "log_loss": round(ll, 6),
        "brier": round(brier, 6),
        "probs": probs,
        "result": result,
        "top_pick": top_pick,
        **base,
    }

    odds = expected.get("odds")
    if odds:
        staked, returned = settle_bets(probs, odds, result)
        out.update({
            "staked": staked,
            "returned": round(returned, 4),
            "profit": round(returned - staked, 4),
            "odds": odds,
        })
    else:
        out["odds_pending"] = True

    print(json.dumps(out))


if __name__ == "__main__":
    main()
