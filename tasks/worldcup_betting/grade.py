"""Stamp actual results into frozen worldcup_betting cases.

Run after matches finish:  ODDS_API_KEY=... python3 grade.py

Pulls completed fixtures from the-odds-api scores endpoint and writes the decided
outcome (home/draw/away) into the matching expected/<id>/answer.json, flipping
graded:false -> true. Matches cases by date + team-pair (order-independent), so a
home/away swap between seed and API doesn't break the join. Idempotent:
already-graded cases are left untouched.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from oddsapi import (fetch_scores, parse_scores_event, team_code, match_key,
                     is_mapped)

HERE = Path(__file__).parent


def _warn(msg: str) -> None:
    print(f"WARNING: {msg}", file=sys.stderr)


def apply_result(base_dir: Path, decided: dict) -> int:
    """Write result into the case matching this scores event. Returns 1 if updated.

    `decided` is the dict from parse_scores_event (teams + result, oriented to the
    API's home/away). The result is re-oriented to the seeded case's home/away.
    """
    key = match_key(decided["commence_time"], decided["home_team"], decided["away_team"])
    for ans_path in (base_dir / "expected").glob("*/answer.json"):
        data = json.loads(ans_path.read_text())
        case_key = (data.get("date"), frozenset(data.get("team_codes", [])))
        if case_key != key or data.get("graded"):
            continue
        result = decided["result"]
        # Re-orient if the API listed home/away opposite to the seeded case.
        if result in ("home", "away") and team_code(decided["home_team"]) != data.get("home_code"):
            result = "away" if result == "home" else "home"
        data["graded"] = True
        data["result"] = result
        ans_path.write_text(json.dumps(data, indent=2) + "\n")
        return 1
    return 0


def main() -> None:
    api_key = os.environ.get("ODDS_API_KEY")
    if not api_key:
        sys.exit("ODDS_API_KEY not set (get a free key at the-odds-api.com)")
    events = fetch_scores(api_key)
    updated = 0
    for raw in events:
        decided = parse_scores_event(raw)
        if decided is None:
            continue  # not completed, or scores missing
        for side in ("home_team", "away_team"):
            if not is_mapped(decided[side]):
                _warn(f"unmapped team name {decided[side]!r} in a completed match; "
                      f"its result may not join to any case")
        n = apply_result(HERE, decided)
        if n == 0:
            # already graded, OR — the dangerous case — completed match matched
            # no seeded case (name/date mismatch → silent hole in the board).
            _warn(f"completed match {decided['home_team']} vs {decided['away_team']} "
                  f"({decided['commence_time'][:10]}) matched no ungraded case "
                  f"(codes {sorted({team_code(decided['home_team']), team_code(decided['away_team'])})}) "
                  f"— already graded, or a name/date mismatch left it ungraded")
        updated += n
    print(f"grade: {updated} fixture(s) newly graded")


if __name__ == "__main__":
    main()
