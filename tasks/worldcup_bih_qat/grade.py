"""Stamp THIS match's result after full time (self-contained, per-task).

Run:  ODDS_API_KEY=... python3 grade.py

Pulls completed fixtures from the-odds-api scores endpoint and writes the decided
outcome (home/draw/away) into this task's own expected/<id>/answer.json, flipping
graded:false -> true. Matched by date + team-pair, re-oriented to the seeded
home/away. Idempotent: an already-graded match is left untouched.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from oddsapi import fetch_scores, parse_scores_event, team_code, match_key

HERE = Path(__file__).parent


def _answer_paths():
    return sorted(HERE.glob("expected/*/answer.json"))


def apply_result(decided: dict) -> int:
    key = match_key(decided["commence_time"], decided["home_team"], decided["away_team"])
    for p in _answer_paths():
        d = json.loads(p.read_text())
        if (d.get("date"), frozenset(d.get("team_codes", []))) != key or d.get("graded"):
            continue
        result = decided["result"]
        if result in ("home", "away") and team_code(decided["home_team"]) != d.get("home_code"):
            result = "away" if result == "home" else "home"
        d["graded"] = True
        d["result"] = result
        p.write_text(json.dumps(d, indent=2) + "\n")
        return 1
    return 0


def main() -> None:
    api_key = os.environ.get("ODDS_API_KEY")
    if not api_key:
        sys.exit("ODDS_API_KEY not set (get a free key at the-odds-api.com)")
    updated = 0
    for raw in fetch_scores(api_key):
        decided = parse_scores_event(raw)
        if decided is not None:
            updated += apply_result(decided)
    print(f"grade: {updated} match(es) newly graded in this task")


if __name__ == "__main__":
    main()
