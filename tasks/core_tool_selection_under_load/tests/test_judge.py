# tests/test_judge.py
import json
import sys, pathlib
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import judge  # noqa: E402


EXPECTED = {
    "id": "case_01",
    "correct_tool_name": "calculate_percentage",
    "expected_args": {
        "amount": [84.5, "84.5", "$84.50", "84.50"],
        "percent": [15, "15", "15%"],
    },
    "n_tools": 4,
    "position": "early",
    "category": "tier1_n4_early",
}


def test_exact_hit():
    out = judge.score_case('{"name": "calculate_percentage", "arguments": {"amount": 84.5, "percent": 15}}', EXPECTED)
    assert out["score"] == 1.0


def test_exact_hit_string_numbers_and_fences():
    stdout = '```json\n{"name": "calculate_percentage", "arguments": {"amount": "$84.50", "percent": "15%"}}\n```'
    out = judge.score_case(stdout, EXPECTED)
    assert out["score"] == 1.0


def test_wrong_tool():
    out = judge.score_case('{"name": "calculate_tip", "arguments": {"amount": 84.5, "percent": 15}}', EXPECTED)
    assert out["score"] == 0.0
    assert "wrong tool" in out["reason"]


def test_right_tool_wrong_argument():
    out = judge.score_case('{"name": "calculate_percentage", "arguments": {"amount": 84.5, "percent": 20}}', EXPECTED)
    assert out["score"] == 0.0
    assert out["arg_results"]["percent"]["ok"] is False
    assert out["arg_results"]["amount"]["ok"] is True


def test_missing_argument():
    out = judge.score_case('{"name": "calculate_percentage", "arguments": {"amount": 84.5}}', EXPECTED)
    assert out["score"] == 0.0
    assert out["arg_results"]["percent"]["ok"] is False


def test_anti_shotgun_array_first_element_wrong():
    stdout = json.dumps([
        {"name": "calculate_tip", "arguments": {"bill_amount": 84.5, "tip_percent": 15}},
        {"name": "calculate_percentage", "arguments": {"amount": 84.5, "percent": 15}},
    ])
    out = judge.score_case(stdout, EXPECTED)
    # Correct answer is the SECOND element -- shotgunning must not get credit.
    assert out["score"] == 0.0


def test_anti_shotgun_array_first_element_right():
    stdout = json.dumps([
        {"name": "calculate_percentage", "arguments": {"amount": 84.5, "percent": 15}},
        {"name": "calculate_tip", "arguments": {"bill_amount": 84.5, "tip_percent": 15}},
    ])
    out = judge.score_case(stdout, EXPECTED)
    assert out["score"] == 1.0


def test_non_json_output():
    out = judge.score_case("Sure! I'll calculate that for you.", EXPECTED)
    assert out["score"] == 0.0
    assert "not parseable" in out["reason"]


def test_prose_wrapped_json_still_parses():
    stdout = 'Here is the call:\n{"name": "calculate_percentage", "arguments": {"amount": 84.5, "percent": 15}}\nDone.'
    out = judge.score_case(stdout, EXPECTED)
    assert out["score"] == 1.0


def test_missing_name_field():
    out = judge.score_case('{"arguments": {"amount": 84.5, "percent": 15}}', EXPECTED)
    assert out["score"] == 0.0


def test_arguments_not_an_object():
    out = judge.score_case('{"name": "calculate_percentage", "arguments": "amount=84.5"}', EXPECTED)
    assert out["score"] == 0.0
    assert "not an object" in out["reason"]


def test_infinity_argument_does_not_crash():
    out = judge.score_case('{"name": "calculate_percentage", "arguments": {"amount": Infinity, "percent": 15}}', EXPECTED)
    assert out["score"] == 0.0


def test_nan_argument_does_not_crash():
    out = judge.score_case('{"name": "calculate_percentage", "arguments": {"amount": NaN, "percent": 15}}', EXPECTED)
    assert out["score"] == 0.0


def test_deeply_nested_json_does_not_crash():
    nested = "[" * 2000 + "]" * 2000
    out = judge.score_case(nested, EXPECTED)
    assert out["score"] == 0.0


def test_non_dict_list_entries_do_not_crash():
    stdout = json.dumps(["just a string", 42, {"name": "calculate_percentage", "arguments": {"amount": 84.5, "percent": 15}}])
    out = judge.score_case(stdout, EXPECTED)
    # first element is a bare string, not a usable call -- must score 0, not crash
    assert out["score"] == 0.0


def test_tool_name_alias_accepted():
    out = judge.score_case('{"tool_name": "calculate_percentage", "arguments": {"amount": 84.5, "percent": 15}}', EXPECTED)
    assert out["score"] == 1.0


def test_empty_array_does_not_crash():
    out = judge.score_case("[]", EXPECTED)
    assert out["score"] == 0.0
