import json
from pathlib import Path
from snapshot import freeze_event
from grade import apply_result

FIXTURE = {
    "home_team": "Scotland",
    "away_team": "Brazil",
    "commence_time": "2026-06-24T22:00:00Z",
}


def test_apply_result_orients_to_seeded_home_away(tmp_path):
    freeze_event(tmp_path, FIXTURE)   # Scotland(home) vs Brazil(away)
    # API: Brazil listed home, Brazil won -> result "home" in API perspective
    decided = {
        "id": "evt1", "home_team": "Brazil", "away_team": "Scotland",
        "commence_time": "2026-06-24T22:00:00Z", "result": "home",
    }
    assert apply_result(tmp_path, decided) == 1
    ans = json.loads((tmp_path / "expected" / "wc26_20260624_SCO_BRA" / "answer.json").read_text())
    assert ans["graded"] is True
    assert ans["result"] == "away"    # Brazil is the AWAY side in the seeded case


def test_apply_result_draw_unchanged(tmp_path):
    freeze_event(tmp_path, {**FIXTURE, "home_team": "Morocco", "away_team": "Haiti"})
    decided = {"id": "e", "home_team": "Haiti", "away_team": "Morocco",
               "commence_time": "2026-06-24T22:00:00Z", "result": "draw"}
    assert apply_result(tmp_path, decided) == 1
    ans = json.loads((tmp_path / "expected" / "wc26_20260624_MAR_HAI" / "answer.json").read_text())
    assert ans["result"] == "draw"


def test_apply_result_no_match_returns_zero(tmp_path):
    freeze_event(tmp_path, FIXTURE)
    decided = {"id": "x", "home_team": "Spain", "away_team": "Japan",
               "commence_time": "2026-06-24T22:00:00Z", "result": "home"}
    assert apply_result(tmp_path, decided) == 0


def test_apply_result_idempotent(tmp_path):
    freeze_event(tmp_path, FIXTURE)
    decided = {"id": "evt1", "home_team": "Scotland", "away_team": "Brazil",
               "commence_time": "2026-06-24T22:00:00Z", "result": "away"}
    assert apply_result(tmp_path, decided) == 1
    # already graded -> no change
    decided2 = {**decided, "result": "home"}
    assert apply_result(tmp_path, decided2) == 0
    ans = json.loads((tmp_path / "expected" / "wc26_20260624_SCO_BRA" / "answer.json").read_text())
    assert ans["result"] == "away"
