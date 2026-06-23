import json
from pathlib import Path
from oddsapi import (parse_odds_event, parse_scores_event, slugify_case_id,
                     team_code, match_key)

HERE = Path(__file__).parent
ODDS = json.loads((HERE / "fixtures" / "odds_sample.json").read_text())
SCORES = json.loads((HERE / "fixtures" / "scores_sample.json").read_text())


def test_parse_odds_event_extracts_decimal_hda():
    ev = parse_odds_event(ODDS[0])
    assert ev["home_team"] == "Scotland"
    assert ev["away_team"] == "Brazil"
    assert ev["odds"] == {"home": 8.50, "draw": 4.80, "away": 1.40}
    assert ev["commence_time"] == "2026-06-24T22:00:00Z"


def test_parse_odds_event_no_bookmakers_returns_none():
    assert parse_odds_event(ODDS[1]) is None


def test_parse_scores_event_decides_outcome():
    res = parse_scores_event(SCORES[0])
    assert res["id"] == "abc123" and res["result"] == "away"   # Scotland 0-3 Brazil
    draw = parse_scores_event(SCORES[1])
    assert draw["result"] == "draw"                            # Morocco 1-1 Haiti


def test_parse_scores_event_skips_incomplete():
    assert parse_scores_event(SCORES[2]) is None


def test_team_code_aliases():
    assert team_code("South Korea") == "KOR"
    assert team_code("South Africa") == "RSA"      # NOT a collision with KOR
    assert team_code("Czech Republic") == team_code("Czechia") == "CZE"
    assert team_code("Bosnia and Herzegovina") == "BIH"


def test_slugify_case_id_uses_codes():
    assert slugify_case_id("2026-06-24T22:00:00Z", "Scotland", "Brazil") == "wc26_20260624_SCO_BRA"


def test_match_key_is_order_independent():
    a = match_key("2026-06-24T22:00:00Z", "Scotland", "Brazil")
    b = match_key("2026-06-24T22:00:00Z", "Brazil", "Scotland")
    assert a == b
    assert a == ("2026-06-24", frozenset({"SCO", "BRA"}))
