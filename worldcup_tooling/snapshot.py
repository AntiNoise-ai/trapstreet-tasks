"""Back-fill odds into the per-match World Cup tasks (near kickoff).

Run:  ODDS_API_KEY=... python3 snapshot.py

Fetches upcoming fixtures + decimal h2h odds from the-odds-api and writes the
(home/draw/away) odds into the matching task's expected/<id>/answer.json — matched
order-independently by date + team-pair, oriented to the seeded home/away. Odds are
never shown to the model; they live in expected/ only, for settlement. Idempotent:
only fills odds that are still null. Prints loud WARNINGs on unmapped team names or
fixtures that match no task, so a mismatch never silently drops a match.

New fixtures (later matchdays) are created with seed.py, not here.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from oddsapi import fetch_odds, parse_odds_event, team_code, match_key, is_mapped

HERE = Path(__file__).parent
TASKS = HERE.parent / "tasks"


def _warn(msg: str) -> None:
    print(f"WARNING: {msg}", file=sys.stderr)


def answer_paths(tasks_root: Path = TASKS) -> list[Path]:
    return sorted(tasks_root.glob("worldcup_*/expected/*/answer.json"))


def backfill_odds(paths: list[Path], parsed: dict) -> int:
    """Fill odds into the task whose match matches `parsed` (by date+team-pair).

    Returns 1 if a null-odds case was filled, else 0. Re-orients odds to the
    seeded case's home/away and never overwrites odds already set.
    """
    key = match_key(parsed["commence_time"], parsed["home_team"], parsed["away_team"])
    for ans_path in paths:
        data = json.loads(ans_path.read_text())
        case_key = (data.get("date"), frozenset(data.get("team_codes", [])))
        if case_key != key or data.get("odds"):
            continue
        if team_code(parsed["home_team"]) == data.get("home_code"):
            odds = parsed["odds"]
        else:
            o = parsed["odds"]
            odds = {"home": o["away"], "draw": o["draw"], "away": o["home"]}
        data["odds"] = odds
        if not data.get("event_id"):
            data["event_id"] = parsed["id"]
        ans_path.write_text(json.dumps(data, indent=2) + "\n")
        return 1
    return 0


def main() -> None:
    api_key = os.environ.get("ODDS_API_KEY")
    if not api_key:
        sys.exit("ODDS_API_KEY not set (get a free key at the-odds-api.com)")
    paths = answer_paths()
    events = fetch_odds(api_key)
    filled = 0
    for raw in events:
        parsed = parse_odds_event(raw)
        if parsed is None:
            continue
        for side in ("home_team", "away_team"):
            if not is_mapped(parsed[side]):
                _warn(f"unmapped team {parsed[side]!r} -> code {team_code(parsed[side])!r}; "
                      f"add it to oddsapi._TEAM_CODES or its odds may not join")
        filled += backfill_odds(paths, parsed)
    print(f"snapshot: filled odds for {filled} match(es) "
          f"({len(events)} fixtures returned by API, {len(paths)} tasks scanned)")


if __name__ == "__main__":
    main()
