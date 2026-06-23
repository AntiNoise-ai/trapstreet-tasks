"""Back-fill THIS match's odds near kickoff (self-contained, per-task).

Run:  ODDS_API_KEY=... python3 snapshot.py

Fetches upcoming fixtures + decimal h2h odds from the-odds-api and writes the
(home/draw/away) odds into this task's own expected/<id>/answer.json — matched by
date + team-pair (order-independent), oriented to the seeded home/away. Odds are
never shown to the model; they live in expected/ only, for settlement. Idempotent:
only fills odds still null, only this task's own match.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from oddsapi import fetch_odds, parse_odds_event, team_code, match_key

HERE = Path(__file__).parent


def _answer_paths():
    return sorted(HERE.glob("expected/*/answer.json"))


def backfill_odds(parsed: dict) -> int:
    key = match_key(parsed["commence_time"], parsed["home_team"], parsed["away_team"])
    for p in _answer_paths():
        d = json.loads(p.read_text())
        if (d.get("date"), frozenset(d.get("team_codes", []))) != key or d.get("odds"):
            continue
        if team_code(parsed["home_team"]) == d.get("home_code"):
            odds = parsed["odds"]
        else:
            o = parsed["odds"]
            odds = {"home": o["away"], "draw": o["draw"], "away": o["home"]}
        d["odds"] = odds
        if not d.get("event_id"):
            d["event_id"] = parsed["id"]
        p.write_text(json.dumps(d, indent=2) + "\n")
        return 1
    return 0


def main() -> None:
    api_key = os.environ.get("ODDS_API_KEY")
    if not api_key:
        sys.exit("ODDS_API_KEY not set (get a free key at the-odds-api.com)")
    filled = 0
    for raw in fetch_odds(api_key):
        parsed = parse_odds_event(raw)
        if parsed is not None:
            filled += backfill_odds(parsed)
    print(f"snapshot: filled odds for {filled} match(es) in this task")


if __name__ == "__main__":
    main()
