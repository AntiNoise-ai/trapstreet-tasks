# tests/test_build.py
import copy
import sys, pathlib
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_cases  # noqa: E402


TOOL_A = {
    "name": "calculate_percentage",
    "description": "Calculates a percentage of a given amount.",
    "parameters": {"type": "object", "properties": {"amount": {"type": "number"}}, "required": ["amount"]},
}
TOOL_B = {
    "name": "get_weather",
    "description": "Gets the weather.",
    "parameters": {"type": "object", "properties": {"location": {"type": "string"}}, "required": ["location"]},
}
TOOL_C = {
    "name": "set_timer",
    "description": "Sets a timer.",
    "parameters": {"type": "object", "properties": {"duration_seconds": {"type": "number"}}, "required": ["duration_seconds"]},
}

VALID_CASE = {
    "id": "case_01",
    "intent": "percentage",
    "query": "What's 15% of $84.50?",
    "tool_catalog": [TOOL_A, TOOL_B, TOOL_C],
    "correct_tool_name": "calculate_percentage",
    "expected_args": {"amount": [84.5, "84.5"], "percent": [15, "15"]},
    "n_tools": 3,
    "position": "early",
    "position_index": 0,
    "category": "tier1_n3_early",
}


def test_valid_case_passes():
    build_cases.validate_case(copy.deepcopy(VALID_CASE))  # must not raise


def test_missing_field_rejected():
    bad = copy.deepcopy(VALID_CASE)
    del bad["expected_args"]
    with pytest.raises(ValueError, match="missing fields"):
        build_cases.validate_case(bad)


def test_n_tools_mismatch_rejected():
    bad = copy.deepcopy(VALID_CASE)
    bad["n_tools"] = 5
    with pytest.raises(ValueError, match="n_tools"):
        build_cases.validate_case(bad)


def test_duplicate_tool_name_rejected():
    bad = copy.deepcopy(VALID_CASE)
    bad["tool_catalog"] = [TOOL_A, TOOL_A, TOOL_C]
    bad["n_tools"] = 3
    with pytest.raises(ValueError, match="duplicate tool name"):
        build_cases.validate_case(bad)


def test_correct_tool_missing_from_catalog_rejected():
    bad = copy.deepcopy(VALID_CASE)
    bad["correct_tool_name"] = "does_not_exist"
    with pytest.raises(ValueError, match="exactly once"):
        build_cases.validate_case(bad)


def test_position_index_mismatch_rejected():
    bad = copy.deepcopy(VALID_CASE)
    bad["position_index"] = 1  # correct tool is actually at index 0
    with pytest.raises(ValueError, match="position control is broken"):
        build_cases.validate_case(bad)


def test_position_index_out_of_range_rejected():
    bad = copy.deepcopy(VALID_CASE)
    bad["position_index"] = 99
    with pytest.raises(ValueError, match="out of range"):
        build_cases.validate_case(bad)


def test_invalid_position_label_rejected():
    bad = copy.deepcopy(VALID_CASE)
    bad["position"] = "somewhere"
    with pytest.raises(ValueError, match="early/mid/late"):
        build_cases.validate_case(bad)


def test_empty_expected_args_rejected():
    bad = copy.deepcopy(VALID_CASE)
    bad["expected_args"] = {}
    with pytest.raises(ValueError, match="expected_args"):
        build_cases.validate_case(bad)


def test_expected_args_value_not_a_list_rejected():
    bad = copy.deepcopy(VALID_CASE)
    bad["expected_args"] = {"amount": 84.5}  # should be a list of accepted values
    with pytest.raises(ValueError, match="expected_args"):
        build_cases.validate_case(bad)


def test_malformed_tool_schema_rejected():
    bad = copy.deepcopy(VALID_CASE)
    bad["tool_catalog"] = [{"name": "calculate_percentage"}, TOOL_B, TOOL_C]  # missing description/parameters
    bad["n_tools"] = 3
    with pytest.raises(ValueError, match="malformed tool schema"):
        build_cases.validate_case(bad)


def test_render_prompt_contains_query_and_all_tool_names():
    prompt = build_cases.render_prompt(VALID_CASE)
    assert "What's 15% of $84.50?" in prompt
    assert "calculate_percentage" in prompt
    assert "get_weather" in prompt
    assert "set_timer" in prompt
