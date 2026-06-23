import math
import pytest
from judge import parse_probs, log_loss, brier_score, settle_bets


def test_parse_probs_plain_json():
    assert parse_probs('{"home":0.5,"draw":0.3,"away":0.2}') == pytest.approx(
        {"home": 0.5, "draw": 0.3, "away": 0.2}, rel=1e-9
    )


def test_parse_probs_wrapped_answer():
    out = parse_probs('{"answer": "{\\"home\\":0.5,\\"draw\\":0.3,\\"away\\":0.2}"}')
    assert out == pytest.approx({"home": 0.5, "draw": 0.3, "away": 0.2}, rel=1e-9)


def test_parse_probs_renormalizes():
    out = parse_probs('{"home":2,"draw":1,"away":1}')
    assert out == pytest.approx({"home": 0.5, "draw": 0.25, "away": 0.25}, rel=1e-9)


def test_parse_probs_rejects_garbage():
    assert parse_probs("not json at all") is None
    assert parse_probs('{"home":0.5}') is None          # missing keys
    assert parse_probs('{"home":-1,"draw":1,"away":1}') is None  # negative
    assert parse_probs('{"home":0,"draw":0,"away":0}') is None   # zero sum


def test_log_loss_perfect_vs_wrong():
    p = {"home": 0.9, "draw": 0.05, "away": 0.05}
    assert log_loss(p, "home") == pytest.approx(-math.log(0.9), rel=1e-9)
    assert log_loss(p, "away") == pytest.approx(-math.log(0.05), rel=1e-9)


def test_log_loss_clamps_zero():
    p = {"home": 1.0, "draw": 0.0, "away": 0.0}
    assert log_loss(p, "away") == pytest.approx(-math.log(1e-15), rel=1e-6)


def test_brier_score_multiclass():
    assert brier_score({"home": 1.0, "draw": 0.0, "away": 0.0}, "home") == pytest.approx(0.0)
    assert brier_score({"home": 1.0, "draw": 0.0, "away": 0.0}, "away") == pytest.approx(2.0)
    assert brier_score({"home": 0.5, "draw": 0.3, "away": 0.2}, "home") == pytest.approx(0.38)


def test_settle_bets_places_only_positive_ev():
    odds = {"home": 2.1, "draw": 3.4, "away": 3.6}
    probs = {"home": 0.55, "draw": 0.25, "away": 0.20}
    staked, returned = settle_bets(probs, odds, result="home")
    assert staked == pytest.approx(1.0)
    assert returned == pytest.approx(2.1)


def test_settle_bets_loses_when_wrong():
    odds = {"home": 2.1, "draw": 3.4, "away": 3.6}
    probs = {"home": 0.55, "draw": 0.25, "away": 0.20}
    staked, returned = settle_bets(probs, odds, result="away")
    assert staked == pytest.approx(1.0)
    assert returned == pytest.approx(0.0)


def test_settle_bets_abstains_when_no_edge():
    odds = {"home": 2.0, "draw": 3.0, "away": 4.0}
    probs = {"home": 0.40, "draw": 0.30, "away": 0.20}
    staked, returned = settle_bets(probs, odds, result="home")
    assert staked == pytest.approx(0.0)
    assert returned == pytest.approx(0.0)
