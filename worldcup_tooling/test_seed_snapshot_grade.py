import json
from pathlib import Path
from seed import scaffold, task_name
from snapshot import backfill_odds
from grade import apply_result

FX = {"home_team": "Scotland", "away_team": "Brazil",
      "commence_time": "2026-06-24T22:00:00Z"}


def _paths(root: Path):
    return sorted(root.glob("worldcup_*/expected/*/answer.json"))


def test_scaffold_creates_self_contained_task(tmp_path):
    name, created = scaffold(FX, tasks_root=tmp_path)
    assert name == "worldcup_sco_bra" and created is True
    td = tmp_path / "worldcup_sco_bra"
    # runner-facing files present
    for f in ("traptask.yaml", "judge.py", "grader.py", "gold.cases.json", "README.md"):
        assert (td / f).exists(), f
    q = (td / "inputs" / "wc26_20260624_SCO_BRA" / "question.txt").read_text()
    assert "Scotland" in q and "Brazil" in q
    # odds never leak into the model's input
    assert "8.5" not in q and "odds" not in q.lower()
    ans = json.loads((td / "expected" / "wc26_20260624_SCO_BRA" / "answer.json").read_text())
    assert ans["odds"] is None and ans["graded"] is False and ans["result"] is None
    assert ans["team_codes"] == ["BRA", "SCO"] and ans["home_code"] == "SCO"


def test_scaffold_is_idempotent(tmp_path):
    scaffold(FX, tasks_root=tmp_path)
    _, created = scaffold(FX, tasks_root=tmp_path)
    assert created is False
    assert len(list(tmp_path.glob("worldcup_*"))) == 1


def test_task_name_no_collision(tmp_path):
    # South Africa vs South Korea must NOT collapse to the same slug
    rsa = task_name({"home_team": "South Africa", "away_team": "South Korea",
                     "commence_time": "2026-06-25T01:00:00Z"})
    assert rsa == "worldcup_rsa_kor"


def test_backfill_odds_orients_to_seeded_home_away(tmp_path):
    scaffold(FX, tasks_root=tmp_path)            # Scotland(home) vs Brazil(away)
    parsed = {"id": "evt1", "home_team": "Brazil", "away_team": "Scotland",
              "commence_time": "2026-06-24T22:00:00Z",
              "odds": {"home": 1.4, "draw": 4.8, "away": 8.5}}  # Brazil-home view
    assert backfill_odds(_paths(tmp_path), parsed) == 1
    ans = json.loads((tmp_path / "worldcup_sco_bra/expected/wc26_20260624_SCO_BRA/answer.json").read_text())
    assert ans["odds"] == {"home": 8.5, "draw": 4.8, "away": 1.4}   # re-oriented
    assert ans["event_id"] == "evt1"
    assert backfill_odds(_paths(tmp_path), parsed) == 0             # already set


def test_apply_result_orients_and_is_idempotent(tmp_path):
    scaffold(FX, tasks_root=tmp_path)
    decided = {"id": "evt1", "home_team": "Brazil", "away_team": "Scotland",
               "commence_time": "2026-06-24T22:00:00Z", "result": "home"}  # Brazil won
    assert apply_result(_paths(tmp_path), decided) == 1
    ans = json.loads((tmp_path / "worldcup_sco_bra/expected/wc26_20260624_SCO_BRA/answer.json").read_text())
    assert ans["graded"] is True and ans["result"] == "away"   # Brazil is AWAY here
    assert apply_result(_paths(tmp_path), {**decided, "result": "draw"}) == 0


def test_apply_result_no_match(tmp_path):
    scaffold(FX, tasks_root=tmp_path)
    decided = {"id": "x", "home_team": "Spain", "away_team": "Japan",
               "commence_time": "2026-06-24T22:00:00Z", "result": "home"}
    assert apply_result(_paths(tmp_path), decided) == 0
