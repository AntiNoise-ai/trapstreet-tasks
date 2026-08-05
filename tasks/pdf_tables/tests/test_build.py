"""Tests for build_cases.py's validation, especially the leak checker.

The leak checker is the reason pdf_reader_v2 exists, and it had to be taught
about scientific notation for this task: a question that quoted "2.25E+01"
would have sailed past the inherited `_numeric_forms`, which only knows how to
write 22.5 as "22.5" or "22". These tests plant leaks and assert they are
caught.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

TASK = Path(__file__).parent.parent
sys.path.insert(0, str(TASK))

import build_cases as bc  # noqa: E402

GOLD = json.loads((TASK / "gold.cases.json").read_text())
CASES = GOLD["cases"]


def case(question: str, matchers: list[dict], **kw) -> dict:
    base = {
        "id": "case_99", "label": "planted", "question": question,
        "answer": "x", "type": "extraction", "category": "test",
        "difficulty": "easy", "matchers": matchers,
    }
    base.update(kw)
    return base


# ------------------------------------------------- the real cases are clean

@pytest.mark.parametrize("c", CASES, ids=[c["id"] for c in CASES])
def test_no_shipped_case_leaks_its_answer(c):
    fatal, _ = bc.assert_no_answer_leak(c)
    assert not fatal, f"{c['id']} ({c['label']}): {fatal}"


def test_every_case_declares_the_page_its_gold_was_read_from():
    """The gold provenance claim is only auditable if each case says which
    rendered page to go back and check."""
    for c in CASES:
        assert isinstance(c.get("_page"), int), f"{c['id']} has no _page"


def test_all_matchers_are_registered_in_the_judge():
    sys.path.insert(0, str(TASK))
    import judge
    for c in CASES:
        for m in c["matchers"]:
            assert m["kind"] in bc.VALID_MATCHERS, f"{c['id']}: {m['kind']} not in VALID_MATCHERS"
            assert m["kind"] in judge.MATCHERS, f"{c['id']}: {m['kind']} has no judge implementation"


def test_case_ids_are_opaque():
    seen: set[str] = set()
    for c in CASES:
        bc.validate_case(c, seen)


def test_traptask_case_list_matches_gold():
    """A real copy-paste mistake: a case id in traptask.yaml drifting away
    from gold.cases.json. Parsed without pyyaml to keep tests dependency-free."""
    import re
    text = (TASK / "traptask.yaml").read_text()
    listed = re.findall(r"^- id:\s*(\S+)", text, re.M)
    assert listed == [c["id"] for c in CASES]


# ------------------------------------------------- planted leaks

def test_sci_value_leak_in_e_notation_is_caught():
    c = case("What is the value, which happens to be 2.25E+01, at stage C3?",
             [{"kind": "sci_value", "value": 22.5}])
    fatal, _ = bc.assert_no_answer_leak(c)
    assert fatal, "a question quoting the answer in E-notation must be a fatal leak"


def test_sci_value_leak_in_plain_decimal_is_caught():
    c = case("Confirm that the stage C3 figure is 22.5 kg CO2e.",
             [{"kind": "sci_value", "value": 22.5}])
    fatal, _ = bc.assert_no_answer_leak(c)
    assert fatal


def test_negative_sci_value_leak_is_caught():
    c = case("Is the A3 figure -2.70E+01?", [{"kind": "sci_value", "value": -27.0}])
    fatal, _ = bc.assert_no_answer_leak(c)
    assert fatal


def test_a_question_merely_naming_the_row_and_column_is_not_a_leak():
    """The shape every real case here has. Naming the row and the column is
    the question; it must not be mistaken for the answer."""
    c = case("What value does the table report for GWP - total at stage C3?",
             [{"kind": "sci_value", "value": 22.5}])
    fatal, partial = bc.assert_no_answer_leak(c)
    assert not fatal and not partial


def test_partial_overlap_is_reported_but_not_fatal():
    """One of two content matchers satisfiable is worth surfacing, but the
    other still forces the model to produce something the prompt didn't give."""
    c = case("Which column, B6 or another, carries values?",
             [{"kind": "regex_required", "pattern": "\\bB\\s*6\\b"},
              {"kind": "sci_value", "value": 2.32e-08}])
    fatal, partial = bc.assert_no_answer_leak(c)
    assert not fatal and partial


def test_regex_forbidden_alone_cannot_score_a_case():
    """It only ever asserts absence, so a case scored solely by it checks
    nothing about the content."""
    c = case("Anything.", [{"kind": "regex_forbidden", "pattern": "zzz"}])
    with pytest.raises(ValueError, match="nothing checks the content"):
        bc.validate_case(c, set())
