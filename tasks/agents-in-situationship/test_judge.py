"""Pytest tests for the agents-in-situationship judge."""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent
EXPECTED_PATH = HERE / "expected" / "baseline_20q" / "answer.json"


def load_expected() -> dict:
    return json.loads(EXPECTED_PATH.read_text())


def test_expected_file_loads():
    """Sanity: the expected/answer.json file we wrote is valid."""
    data = load_expected()
    assert data["n_questions"] == 20
    assert len(data["scoring_key"]) == 20
    assert data["primary_tiebreak_order"] == ["anxious", "avoidant", "secure"]


# Import the judge module after it exists
import importlib.util


def _load_judge():
    spec = importlib.util.spec_from_file_location("judge", HERE / "judge.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ----- Parsing -----

def test_parse_plain_json():
    j = _load_judge()
    out, err = j._parse_output('{"answers": ["A","B","C","D"]}')
    assert out == {"answers": ["A","B","C","D"]}
    assert err == ""

def test_parse_with_code_fence():
    j = _load_judge()
    out, err = j._parse_output('```json\n{"answers": ["A"]}\n```')
    assert out == {"answers": ["A"]}

def test_parse_empty_string():
    j = _load_judge()
    out, err = j._parse_output("   ")
    assert out is None
    assert "empty" in err

def test_parse_invalid_json():
    j = _load_judge()
    out, err = j._parse_output("not json at all")
    assert out is None


# ----- Format gate -----

def test_format_gate_valid_20_letters():
    j = _load_judge()
    answers = ["A"] * 20
    ok, err = j._validate_answers(answers, n_expected=20)
    assert ok is True
    assert err == ""

def test_format_gate_wrong_count():
    j = _load_judge()
    ok, err = j._validate_answers(["A"] * 19, n_expected=20)
    assert ok is False
    assert "19" in err and "20" in err

def test_format_gate_lowercase_rejected():
    j = _load_judge()
    answers = ["A"] * 19 + ["a"]
    ok, err = j._validate_answers(answers, n_expected=20)
    assert ok is False

def test_format_gate_invalid_letter_rejected():
    j = _load_judge()
    answers = ["A"] * 19 + ["E"]
    ok, err = j._validate_answers(answers, n_expected=20)
    assert ok is False
