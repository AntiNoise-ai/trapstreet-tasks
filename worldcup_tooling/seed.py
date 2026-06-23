"""Scaffold one TrapStreet task PER MATCH from a fixture list (no API key needed).

Each match becomes its own self-contained task under tasks/worldcup_<home>_<away>/
with its own traptask.yaml + 1 case + judge.py + grader.py. Because the model is
graded blind (never sees odds), a match is fully answerable from teams + kickoff;
odds and results are back-filled later by snapshot.py / grade.py.

Run:  python3 seed.py        (idempotent — existing tasks are left untouched)
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from oddsapi import team_code, slugify_case_id

HERE = Path(__file__).parent
TASKS = HERE.parent / "tasks"

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

README_TEMPLATE = """\
# World Cup betting — {home} vs {away}

One match from the 2026 FIFA World Cup, as a standalone TrapStreet task. A model
predicts the outcome **blind** (it never sees the odds) and is graded after the
match is played.

- Input: `inputs/{cid}/question.txt` — teams + kickoff, no odds.
- Output: stdout JSON `{{"home":p,"draw":p,"away":p}}`.
- Graded by `judge.py`: log-loss + Brier (calibration) and, once odds are
  back-filled, a flat-stake +EV ROI. `grader.py` aggregates the single match.

This task is **pending** until kickoff (`result: null`). Odds/results are filled
by the shared tooling in `worldcup_tooling/` (`snapshot.py` near kickoff,
`grade.py` after full time) once `ODDS_API_KEY` is set. See that directory's
README for the live loop. Blind prediction + post-cutoff fixtures keep it
leakage-free.
"""

TRAPTASK_TEMPLATE = """\
name: World Cup — {home} vs {away}

dirs:
  inputs: inputs/
  expected: expected/

cases:
- id: {cid}
  description: "{home} vs {away} ({date})"
  tags:
  - worldcup
  - worldcup_2026

judge:
  cmd: python3 judge.py

grader:
  cmd: python3 grader.py
"""

# kickoff times are UTC (ISO-8601 Z). home_team is the fixture's listed-first side.
FIXTURES = [
    {"home_team": "Switzerland", "away_team": "Canada",
     "commence_time": "2026-06-24T19:00:00Z"},
    {"home_team": "Bosnia and Herzegovina", "away_team": "Qatar",
     "commence_time": "2026-06-24T19:00:00Z"},
    {"home_team": "Scotland", "away_team": "Brazil",
     "commence_time": "2026-06-24T22:00:00Z"},
    {"home_team": "Morocco", "away_team": "Haiti",
     "commence_time": "2026-06-24T22:00:00Z"},
    {"home_team": "Czechia", "away_team": "Mexico",
     "commence_time": "2026-06-25T01:00:00Z"},
    {"home_team": "South Africa", "away_team": "South Korea",
     "commence_time": "2026-06-25T01:00:00Z"},
]


def task_name(fx: dict) -> str:
    return f"worldcup_{team_code(fx['home_team']).lower()}_{team_code(fx['away_team']).lower()}"


def _answer(cid: str, fx: dict) -> dict:
    home, away, commence = fx["home_team"], fx["away_team"], fx["commence_time"]
    return {
        "id": cid,
        "event_id": fx.get("id"),
        "type": "match_prediction",
        "home_team": home,
        "away_team": away,
        "home_code": team_code(home),
        "away_code": team_code(away),
        "commence_time": commence,
        "date": commence[:10],
        "team_codes": sorted({team_code(home), team_code(away)}),
        "odds": fx.get("odds"),
        "graded": False,
        "result": None,
        "matchers": [{"kind": "roi_logloss"}],
        "_source": "the-odds-api soccer_fifa_world_cup h2h (decimal)",
    }


def scaffold(fx: dict, tasks_root: Path = TASKS) -> tuple[str, bool]:
    """Create a per-match task dir. Returns (task_name, created). Idempotent."""
    home, away, commence = fx["home_team"], fx["away_team"], fx["commence_time"]
    name = task_name(fx)
    td = tasks_root / name
    cid = slugify_case_id(commence, home, away)
    if (td / "traptask.yaml").exists():
        return name, False

    (td / "inputs" / cid).mkdir(parents=True, exist_ok=True)
    (td / "expected" / cid).mkdir(parents=True, exist_ok=True)
    (td / "inputs" / cid / "question.txt").write_text(
        QUESTION_TEMPLATE.format(home=home, away=away, commence=commence))
    (td / "expected" / cid / "answer.json").write_text(
        json.dumps(_answer(cid, fx), indent=2) + "\n")
    (td / "gold.cases.json").write_text(json.dumps(
        [{"id": cid, "description": f"{home} vs {away} ({commence[:10]})",
          "commence_time": commence}], indent=2) + "\n")
    (td / "traptask.yaml").write_text(
        TRAPTASK_TEMPLATE.format(home=home, away=away, cid=cid, date=commence[:10]))
    (td / "README.md").write_text(
        README_TEMPLATE.format(home=home, away=away, cid=cid))
    shutil.copy(HERE / "judge.py", td / "judge.py")
    shutil.copy(HERE / "grader.py", td / "grader.py")
    return name, True


def main() -> None:
    created = 0
    for fx in FIXTURES:
        name, was_created = scaffold(fx)
        created += int(was_created)
        print(f"  {'created' if was_created else 'exists '}  tasks/{name}")
    print(f"seed: {created} task(s) created, {len(FIXTURES) - created} already present")


if __name__ == "__main__":
    main()
