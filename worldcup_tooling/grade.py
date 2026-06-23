"""Stamp actual results into the per-match World Cup tasks (after full time).

Run:  ODDS_API_KEY=... python3 grade.py

Pulls completed fixtures from the-odds-api scores endpoint and writes the decided
outcome (home/draw/away) into the matching task's expected/<id>/answer.json,
flipping graded:false -> true. Matched by date + team-pair (order-independent) and
re-oriented to the seeded home/away. Idempotent: already-graded matches untouched.
Prints a WARNING for any completed match that matches no task (a name/date
mismatch would otherwise silently leave it ungraded).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from oddsapi import fetch_scores, parse_scores_event, team_code, match_key, is_mapped

HERE = Path(__file__).parent
TASKS = HERE.parent / "tasks"


def _warn(msg: str) -> None:
    print(f"WARNING: {msg}", file=sys.stderr)


def answer_paths(tasks_root: Path = TASKS) -> list[Path]:
    return sorted(tasks_root.glob("worldcup_*/expected/*/answer.json"))


def apply_result(paths: list[Path], decided: dict) -> int:
    """Write result into the task matching this scores event. Returns 1 if updated."""
    key = match_key(decided["commence_time"], decided["home_team"], decided["away_team"])
    for ans_path in paths:
        data = json.loads(ans_path.read_text())
        case_key = (data.get("date"), frozenset(data.get("team_codes", [])))
        if case_key != key or data.get("graded"):
            continue
        result = decided["result"]
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
    paths = answer_paths()
    events = fetch_scores(api_key)
    updated = 0
    for raw in events:
        decided = parse_scores_event(raw)
        if decided is None:
            continue
        for side in ("home_team", "away_team"):
            if not is_mapped(decided[side]):
                _warn(f"unmapped team {decided[side]!r} in a completed match; "
                      f"its result may not join to any task")
        n = apply_result(paths, decided)
        if n == 0:
            _warn(f"completed match {decided['home_team']} vs {decided['away_team']} "
                  f"({decided['commence_time'][:10]}) matched no ungraded task "
                  f"(codes {sorted({team_code(decided['home_team']), team_code(decided['away_team'])})}) "
                  f"— already graded, or a name/date mismatch")
        updated += n
    print(f"grade: {updated} match(es) newly graded ({len(paths)} tasks scanned)")


if __name__ == "__main__":
    main()
