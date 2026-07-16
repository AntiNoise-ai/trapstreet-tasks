# tests/test_judge.py
import sys, pathlib
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import judge  # noqa: E402


def test_score_case_is_implemented():
    """This fails until you replace judge.score_case()'s
    NotImplementedError stub with real scoring logic. Once you do, replace
    this test with real cases -- see references/scoring-design.md for the
    known-exploit cases you should specifically test for (substring vs.
    word-boundary matching, malformed JSON, Infinity/NaN, anti-shotgun)."""
    with pytest.raises(NotImplementedError):
        judge.score_case("", {})
