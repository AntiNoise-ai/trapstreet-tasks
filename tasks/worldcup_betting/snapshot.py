"""Freeze 2026 World Cup fixtures into committed task cases, and back-fill odds.

Two ways in:
  1. seed.py calls freeze_event(...) with odds=None to create cases from a known
     fixture list BEFORE an API key is available (the model never sees odds, so a
     case is fully answerable with just teams + kickoff).
  2. `ODDS_API_KEY=... python3 snapshot.py` fetches upcoming fixtures + odds and
     either back-fills odds onto an existing seeded case (matched order-independently
     by date + team-pair) or creates a brand-new case.

Writes per fixture:
  inputs/<id>/question.txt    — matchup + kickoff only (NO odds — blind prediction)
  expected/<id>/answer.json   — teams + (optional) odds, graded:false, result:null
and rebuilds gold.cases.json + traptask.yaml deterministically from the manifest.
Idempotent: re-running never overwrites an existing question, and only fills odds
that are still null.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from oddsapi import (fetch_odds, parse_odds_event, slugify_case_id, team_code,
                     match_key, is_mapped)

HERE = Path(__file__).parent


def _warn(msg: str) -> None:
    print(f"WARNING: {msg}", file=sys.stderr)


def _check_team_names(parsed: dict) -> None:
    """Warn if either team name isn't explicitly mapped — the silent-join risk."""
    for side in ("home_team", "away_team"):
        if not is_mapped(parsed[side]):
            _warn(f"unmapped team name {parsed[side]!r} -> fallback code "
                  f"{team_code(parsed[side])!r}; add it to _TEAM_CODES or the "
                  f"odds/results join may silently miss this fixture")

QUESTION_TEMPLATE = """\
2026 FIFA World Cup — match prediction

{home} (home) vs {away} (away)
Kickoff: {commence}

Task: using your own knowledge of these teams, estimate the probability of each
outcome. Output ONLY a JSON object on a single line with keys "home", "draw",
"away" whose values are probabilities that sum to 1.
Example: {{"home": 0.45, "draw": 0.28, "away": 0.27}}
Do not explain your reasoning. Output only the JSON.
"""

TRAPTASK_HEADER = """\
dirs:
  inputs: inputs/
  expected: expected/

"""

TRAPTASK_FOOTER = """
judge:
  cmd: python3 judge.py

grader:
  cmd: python3 grader.py
"""


def freeze_event(base_dir: Path, event: dict) -> str:
    """Write inputs/ + expected/ for one fixture. Returns the case id.

    `event` needs home_team, away_team, commence_time; odds (dict) and id
    (the-odds-api event id) are optional. No-op if the case already exists, so a
    re-run never overwrites a previously frozen question / odds.
    """
    home, away = event["home_team"], event["away_team"]
    commence = event["commence_time"]
    cid = slugify_case_id(commence, home, away)
    in_dir = base_dir / "inputs" / cid
    exp_dir = base_dir / "expected" / cid
    if (exp_dir / "answer.json").exists():
        return cid

    in_dir.mkdir(parents=True, exist_ok=True)
    exp_dir.mkdir(parents=True, exist_ok=True)

    (in_dir / "question.txt").write_text(QUESTION_TEMPLATE.format(
        home=home, away=away, commence=commence,
    ))
    (exp_dir / "answer.json").write_text(json.dumps({
        "id": cid,
        "event_id": event.get("id"),
        "type": "match_prediction",
        "home_team": home,
        "away_team": away,
        "home_code": team_code(home),
        "away_code": team_code(away),
        "commence_time": commence,
        "date": commence[:10],
        "team_codes": sorted({team_code(home), team_code(away)}),
        "odds": event.get("odds"),
        "graded": False,
        "result": None,
        "matchers": [{"kind": "roi_logloss"}],
        "_source": "the-odds-api soccer_fifa_world_cup h2h (decimal)",
    }, indent=2) + "\n")
    return cid


def _iter_answer_paths(base_dir: Path):
    yield from (base_dir / "expected").glob("*/answer.json")


def backfill_odds(base_dir: Path, parsed: dict) -> int:
    """Fill odds into a seeded case matching this odds event (by date+team-pair).

    Returns 1 if a case's null odds were filled, else 0. Never overwrites odds
    that are already set.
    """
    key = match_key(parsed["commence_time"], parsed["home_team"], parsed["away_team"])
    for ans_path in _iter_answer_paths(base_dir):
        data = json.loads(ans_path.read_text())
        case_key = (data.get("date"), frozenset(data.get("team_codes", [])))
        if case_key != key or data.get("odds"):
            continue
        # Orient the odds to the seeded case's home/away (API may have swapped).
        if (team_code(parsed["home_team"]) == data.get("home_code")):
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


def _update_manifest(base_dir: Path, cid: str, event: dict) -> None:
    """Append the case to gold.cases.json (the source of truth) if not present."""
    manifest_path = base_dir / "gold.cases.json"
    manifest = json.loads(manifest_path.read_text())
    if any(c["id"] == cid for c in manifest):
        return
    desc = f"{event['home_team']} vs {event['away_team']} ({event['commence_time'][:10]})"
    manifest.append({"id": cid, "description": desc,
                     "commence_time": event["commence_time"]})
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")


def rebuild_traptask_yaml(base_dir: Path) -> None:
    """Regenerate traptask.yaml deterministically from gold.cases.json.

    Rebuilding from the manifest (instead of string-splicing) means a re-run can
    never corrupt the file — it's a pure function of the manifest.
    """
    manifest = json.loads((base_dir / "gold.cases.json").read_text())
    if not manifest:
        cases_block = "cases: []\n"
    else:
        lines = ["cases:"]
        for c in manifest:
            lines.append(f"- id: {c['id']}")
            lines.append(f"  description: \"{c['description']}\"")
            lines.append("  tags:")
            lines.append("  - worldcup")
            lines.append("  - worldcup_2026")
            if "example" in c["id"]:
                lines.append("  - example")
        cases_block = "\n".join(lines) + "\n"
    (base_dir / "traptask.yaml").write_text(TRAPTASK_HEADER + cases_block + TRAPTASK_FOOTER)


def seed_fixtures(base_dir: Path, fixtures: list[dict]) -> int:
    """Create cases (odds=None) from a manual fixture list. Returns count seeded."""
    n = 0
    for fx in fixtures:
        cid = freeze_event(base_dir, fx)
        _update_manifest(base_dir, cid, fx)
        n += 1
    rebuild_traptask_yaml(base_dir)
    return n


def main() -> None:
    api_key = os.environ.get("ODDS_API_KEY")
    if not api_key:
        sys.exit("ODDS_API_KEY not set (get a free key at the-odds-api.com). "
                 "To create cases without odds, use seed.py instead.")
    events = fetch_odds(api_key)
    # dates that already have seeded cases — a "new" case on such a date is more
    # likely a team-name mismatch than a genuinely new fixture, so flag it.
    seeded_dates = {json.loads(p.read_text()).get("date")
                    for p in _iter_answer_paths(HERE)}
    created = filled = 0
    for raw in events:
        parsed = parse_odds_event(raw)
        if parsed is None:
            continue
        _check_team_names(parsed)
        if backfill_odds(HERE, parsed):
            filled += 1
            continue
        cid = slugify_case_id(parsed["commence_time"], parsed["home_team"], parsed["away_team"])
        if parsed["commence_time"][:10] in seeded_dates:
            _warn(f"creating NEW case {cid} on a date that already has seeded "
                  f"cases — verify this isn't a name mismatch with an existing "
                  f"fixture (which would leave that one's odds null)")
        freeze_event(HERE, parsed)
        _update_manifest(HERE, cid, parsed)
        created += 1
    rebuild_traptask_yaml(HERE)
    print(f"snapshot: {created} new case(s), {filled} odds back-filled "
          f"({len(events)} returned by API)")


if __name__ == "__main__":
    main()
