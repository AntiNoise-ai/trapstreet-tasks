"""Seed the worldcup_betting task with a known fixture list (no API key needed).

Because the model is graded blind (it never sees odds), a fixture is fully
answerable with just teams + kickoff. This seeds those cases now; odds and results
are back-filled later by snapshot.py / grade.py once ODDS_API_KEY is set.

Run:  python3 seed.py
Idempotent — re-running skips fixtures already frozen.

FIXTURES below is the 2026 World Cup slate we're tracking. Append future matchdays
here (or just run snapshot.py with a key, which also creates new cases).
"""
from __future__ import annotations

from pathlib import Path

from snapshot import seed_fixtures

HERE = Path(__file__).parent

# kickoff times are UTC (ISO-8601 Z). home_team is the fixture's listed-first side.
FIXTURES = [
    # --- 2026-06-24 (matchday 3) ---
    # Group B, 12:00 PT = 19:00 UTC
    {"home_team": "Switzerland", "away_team": "Canada",
     "commence_time": "2026-06-24T19:00:00Z"},
    {"home_team": "Bosnia and Herzegovina", "away_team": "Qatar",
     "commence_time": "2026-06-24T19:00:00Z"},
    # Group C, 18:00 ET = 22:00 UTC
    {"home_team": "Scotland", "away_team": "Brazil",
     "commence_time": "2026-06-24T22:00:00Z"},
    {"home_team": "Morocco", "away_team": "Haiti",
     "commence_time": "2026-06-24T22:00:00Z"},
    # Group A, 19:00 CT (UTC-6) = 01:00 UTC next day
    {"home_team": "Czechia", "away_team": "Mexico",
     "commence_time": "2026-06-25T01:00:00Z"},
    {"home_team": "South Africa", "away_team": "South Korea",
     "commence_time": "2026-06-25T01:00:00Z"},
]


def main() -> None:
    n = seed_fixtures(HERE, FIXTURES)
    print(f"seed: ensured {n} fixture(s) (existing ones left untouched)")


if __name__ == "__main__":
    main()
