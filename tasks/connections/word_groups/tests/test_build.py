# tests/test_build.py
import json, sys, pathlib
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_cases  # noqa: E402


def _case(**over):
    base = {
        "id": "t1", "category": "easy",
        "groups": [
            {"theme": "a", "tier": "yellow", "words": ["A1", "A2", "A3", "A4"]},
            {"theme": "b", "tier": "green",  "words": ["B1", "B2", "B3", "B4"]},
            {"theme": "c", "tier": "blue",   "words": ["C1", "C2", "C3", "C4"]},
            {"theme": "d", "tier": "purple", "words": ["D1", "D2", "D3", "D4"]},
        ],
        "traps": ["A1"],
    }
    base.update(over)
    return base


def test_valid_case_passes():
    build_cases.validate_case(_case())  # no raise


def test_rejects_wrong_group_count():
    c = _case(); c["groups"] = c["groups"][:3]
    with pytest.raises(ValueError, match="4 groups"):
        build_cases.validate_case(c)


def test_rejects_wrong_words_per_group():
    c = _case(); c["groups"][0]["words"] = ["A1", "A2", "A3"]
    with pytest.raises(ValueError, match="4 words"):
        build_cases.validate_case(c)


def test_rejects_duplicate_word_across_groups():
    c = _case(); c["groups"][1]["words"] = ["A1", "B2", "B3", "B4"]
    with pytest.raises(ValueError, match="distinct"):
        build_cases.validate_case(c)


def test_rejects_trap_not_in_words():
    c = _case(); c["traps"] = ["ZZ"]
    with pytest.raises(ValueError, match="trap"):
        build_cases.validate_case(c)


def test_rejects_empty_traps():
    c = _case(); c["traps"] = []
    with pytest.raises(ValueError, match="trap"):
        build_cases.validate_case(c)


def test_shuffle_is_deterministic():
    words = ["A1", "A2", "B1", "B2", "C1", "C2", "D1", "D2"]
    assert build_cases.shuffled_words("x", list(words)) == build_cases.shuffled_words("x", list(words))


def test_shuffle_reorders():
    ordered = ["A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4",
               "C1", "C2", "C3", "C4", "D1", "D2", "D3", "D4"]
    assert build_cases.shuffled_words("e1", list(ordered)) != ordered
