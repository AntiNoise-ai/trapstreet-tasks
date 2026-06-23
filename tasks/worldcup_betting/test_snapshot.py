import json
from pathlib import Path
from snapshot import (freeze_event, backfill_odds, rebuild_traptask_yaml,
                      _update_manifest, seed_fixtures)

FIXTURE = {
    "home_team": "Scotland",
    "away_team": "Brazil",
    "commence_time": "2026-06-24T22:00:00Z",
}


def test_freeze_event_blind_input_no_odds(tmp_path):
    cid = freeze_event(tmp_path, FIXTURE)
    assert cid == "wc26_20260624_SCO_BRA"

    q = (tmp_path / "inputs" / cid / "question.txt").read_text()
    assert "Scotland" in q and "Brazil" in q
    assert "home" in q and "draw" in q and "away" in q
    # no odds anywhere in the model's input
    for token in ("8.5", "1.4", "4.8", "odds", "Odds"):
        assert token not in q

    ans = json.loads((tmp_path / "expected" / cid / "answer.json").read_text())
    assert ans["graded"] is False and ans["result"] is None
    assert ans["odds"] is None                       # seeded without odds
    assert ans["team_codes"] == ["BRA", "SCO"]       # sorted
    assert ans["home_code"] == "SCO"


def test_freeze_event_with_odds(tmp_path):
    ev = {**FIXTURE, "id": "abc123", "odds": {"home": 8.5, "draw": 4.8, "away": 1.4}}
    cid = freeze_event(tmp_path, ev)
    ans = json.loads((tmp_path / "expected" / cid / "answer.json").read_text())
    assert ans["odds"] == {"home": 8.5, "draw": 4.8, "away": 1.4}
    assert ans["event_id"] == "abc123"


def test_freeze_event_is_idempotent(tmp_path):
    assert freeze_event(tmp_path, FIXTURE) == freeze_event(tmp_path, FIXTURE)
    assert len(list((tmp_path / "inputs").iterdir())) == 1


def test_backfill_odds_orients_to_seeded_home_away(tmp_path):
    # seed Scotland(home) vs Brazil(away), no odds
    freeze_event(tmp_path, FIXTURE)
    # API returns the SAME match with Brazil listed as home (swapped) + odds
    parsed = {
        "id": "evt1", "home_team": "Brazil", "away_team": "Scotland",
        "commence_time": "2026-06-24T22:00:00Z",
        "odds": {"home": 1.4, "draw": 4.8, "away": 8.5},   # Brazil-home perspective
    }
    assert backfill_odds(tmp_path, parsed) == 1
    ans = json.loads((tmp_path / "expected" / "wc26_20260624_SCO_BRA" / "answer.json").read_text())
    # re-oriented to Scotland-home perspective
    assert ans["odds"] == {"home": 8.5, "draw": 4.8, "away": 1.4}
    assert ans["event_id"] == "evt1"
    # second call is a no-op (odds already set)
    assert backfill_odds(tmp_path, parsed) == 0


def test_rebuild_traptask_yaml_is_deterministic_and_safe(tmp_path):
    (tmp_path / "gold.cases.json").write_text("[]")
    rebuild_traptask_yaml(tmp_path)
    text1 = (tmp_path / "traptask.yaml").read_text()
    assert "cases: []" in text1
    assert "cmd: python3 judge.py" in text1 and "cmd: python3 grader.py" in text1

    _update_manifest(tmp_path, "wc26_20260624_SCO_BRA", FIXTURE)
    rebuild_traptask_yaml(tmp_path)
    text2 = (tmp_path / "traptask.yaml").read_text()
    assert "id: wc26_20260624_SCO_BRA" in text2 and "- worldcup_2026" in text2
    # rebuilding again is byte-identical (no corruption on re-run)
    rebuild_traptask_yaml(tmp_path)
    assert (tmp_path / "traptask.yaml").read_text() == text2


def test_seed_fixtures_builds_manifest_and_yaml(tmp_path):
    (tmp_path / "gold.cases.json").write_text("[]")
    n = seed_fixtures(tmp_path, [FIXTURE])
    assert n == 1
    manifest = json.loads((tmp_path / "gold.cases.json").read_text())
    assert manifest[0]["id"] == "wc26_20260624_SCO_BRA"
    assert "wc26_20260624_SCO_BRA" in (tmp_path / "traptask.yaml").read_text()
