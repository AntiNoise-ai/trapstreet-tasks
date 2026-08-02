"""Tests for build_cases.py's validation — chiefly the answer-leak check,
which is the reason this task exists as a fork of tasks/pdf_reader.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))

from build_cases import assert_no_answer_leak, validate_case  # noqa: E402

GOLD = json.loads((HERE.parent / "gold.cases.json").read_text())
V1 = HERE.parent.parent / "pdf_reader"


def _case(question: str, matchers: list[dict]) -> dict:
    return {"question": question, "matchers": matchers}


# ---------------------------------------------------------------- leak check

def test_clean_case_has_no_leak():
    fatal, partial = assert_no_answer_leak(
        _case("What is the deposit amount in GBP?",
              [{"kind": "leading_numeric", "value": 2250.0, "tolerance": 0.01}])
    )
    assert fatal == [] and partial == []


def test_answer_verbatim_in_question_is_fatal():
    """The v1 governing_act shape: the format example WAS the answer."""
    fatal, _ = assert_no_answer_leak(
        _case("Which Act governs this tenancy? (e.g. 'Housing Act 1988')",
              [{"kind": "keywords_all", "values": ["housing act", "1988"]},
               {"kind": "no_hedge"}])
    )
    assert fatal, "answer sitting in the question must be fatal"


def test_numeric_answer_in_question_is_fatal():
    fatal, _ = assert_no_answer_leak(
        _case("Rent is £2,100 pcm. What is the monthly rent?",
              [{"kind": "leading_numeric", "value": 2100.0, "tolerance": 0.01}])
    )
    assert fatal


def test_numeric_leak_detected_through_thousands_separator():
    fatal, _ = assert_no_answer_leak(
        _case("The total is 77,400 over the term. What is the total?",
              [{"kind": "numeric", "value": 77400.0, "tolerance": 0.01}])
    )
    assert fatal


def test_numeric_substring_does_not_false_positive():
    """2100 must not 'match' inside 12100 or 21005."""
    fatal, partial = assert_no_answer_leak(
        _case("Reference 12100 and code 21005 apply.",
              [{"kind": "leading_numeric", "value": 2100.0, "tolerance": 0.01}])
    )
    assert fatal == [] and partial == []


def test_partial_overlap_is_not_fatal():
    """One matcher echoable, another not — still forces real work."""
    fatal, partial = assert_no_answer_leak(
        _case("Does it apply to the fixed term, the extension period, or both?",
              [{"kind": "keywords_all", "values": ["extension"]},
               {"kind": "keywords_any", "values": ["only", "solely"]},
               {"kind": "no_hedge"}])
    )
    assert fatal == []
    assert partial, "the echoable matcher should still be reported"


def test_shape_only_matchers_are_never_a_leak():
    """leading_word/no_hedge/min_words constrain form, not content."""
    fatal, partial = assert_no_answer_leak(
        _case("Answer yes or no.",
              [{"kind": "leading_word", "value": "no"}, {"kind": "no_hedge"}])
    )
    assert fatal == [] and partial == []


def test_regex_matching_question_is_fatal():
    fatal, _ = assert_no_answer_leak(
        _case("The tenancy began 05/09/2022. What is the start date?",
              [{"kind": "regex_required", "pattern": r"\b0?5[/\-]0?9[/\-]2022\b"}])
    )
    assert fatal


# ---------------------------------------------------------------- validators

def test_descriptive_case_id_is_rejected():
    case = dict(GOLD["cases"][0], id="pets_allowed")
    with pytest.raises(ValueError, match="opaque"):
        validate_case(case, set())


def test_duplicate_case_id_is_rejected():
    seen: set[str] = set()
    validate_case(dict(GOLD["cases"][0]), seen)
    with pytest.raises(ValueError, match="duplicate"):
        validate_case(dict(GOLD["cases"][0]), seen)


def test_unknown_matcher_kind_is_rejected():
    case = dict(GOLD["cases"][0], matchers=[{"kind": "vibes"}])
    with pytest.raises(ValueError, match="unknown matcher"):
        validate_case(case, set())


def test_missing_field_is_rejected():
    case = {k: v for k, v in GOLD["cases"][0].items() if k != "answer"}
    with pytest.raises(ValueError, match="answer"):
        validate_case(case, set())


# ---------------------------------------------------------------- gold itself

def test_shipped_gold_builds_clean():
    seen: set[str] = set()
    for case in GOLD["cases"]:
        validate_case(case, seen)
    assert len(seen) == 20


def test_every_case_id_is_opaque_and_sequential():
    ids = [c["id"] for c in GOLD["cases"]]
    assert ids == [f"case_{i:02d}" for i in range(1, 21)]


def test_labels_are_unique():
    labels = [c["label"] for c in GOLD["cases"]]
    assert len(set(labels)) == len(labels)


@pytest.mark.skipif(not V1.exists(), reason="v1 task not present")
def test_regression_v1_leaks_would_be_caught():
    """The four cases this fork exists to fix must trip the checker when
    run against v1's own question text + matchers."""
    caught = set()
    for d in sorted((V1 / "expected").iterdir()):
        exp = json.loads((d / "answer.json").read_text())
        q = (V1 / "inputs" / d.name / "question.txt").read_text()
        fatal, _ = assert_no_answer_leak({"question": q, "matchers": exp["matchers"]})
        if fatal:
            caught.add(d.name)
    assert caught == {
        "governing_act",
        "late_rent_interest_rate",
        "pets_allowed",
        "rent_increase_scope",
    }
