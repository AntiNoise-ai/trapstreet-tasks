# tests/test_build.py
import sys, pathlib
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_cases  # noqa: E402


def _valid_case(**overrides):
    case = {
        "id": "case_01",
        "category": "gifting_disclosure",
        "trap": "gifting_disclosure",
        "tags": ["marketing"],
        "description": "A valid case.",
        "scenario": "x" * 60,
        "expected_requires_disclosure": True,
    }
    case.update(overrides)
    return case


def test_valid_case_passes():
    build_cases.validate_case(_valid_case())  # no exception


def test_missing_field_raises():
    case = _valid_case()
    del case["scenario"]
    with pytest.raises(ValueError, match="missing fields"):
        build_cases.validate_case(case)


def test_non_opaque_id_rejected():
    with pytest.raises(ValueError, match="opaque"):
        build_cases.validate_case(_valid_case(id="gifting_coffee_case"))


def test_bad_id_shape_rejected():
    with pytest.raises(ValueError, match=r"case_\\d\\d"):
        build_cases.validate_case(_valid_case(id="case_1"))


def test_unknown_category_rejected():
    with pytest.raises(ValueError, match="category"):
        build_cases.validate_case(_valid_case(category="bogus"))


def test_unknown_trap_rejected():
    with pytest.raises(ValueError, match="trap"):
        build_cases.validate_case(_valid_case(trap="bogus"))


def test_category_trap_mismatch_rejected():
    with pytest.raises(ValueError, match="implies trap"):
        build_cases.validate_case(_valid_case(category="attribution", trap="none"))


def test_clean_control_requires_none_trap():
    build_cases.validate_case(_valid_case(category="clean_control", trap="none"))  # no exception


def test_non_bool_disclosure_rejected():
    with pytest.raises(ValueError, match="bool"):
        build_cases.validate_case(_valid_case(expected_requires_disclosure="yes"))


def test_short_scenario_rejected():
    with pytest.raises(ValueError, match="real paragraph"):
        build_cases.validate_case(_valid_case(scenario="too short"))


def test_empty_tags_rejected():
    with pytest.raises(ValueError, match="tags"):
        build_cases.validate_case(_valid_case(tags=[]))


def test_build_end_to_end():
    """Full build() run against the real gold.cases.json produces inputs/
    and expected/ for every case, with no answer leakage into inputs/."""
    build_cases.build()
    gold = __import__("json").loads(build_cases.GOLD.read_text())
    for case in gold["cases"]:
        cid = case["id"]
        q = (build_cases.HERE / "inputs" / cid / "question.txt").read_text()
        # the boolean answer itself is too generic a string to check for
        # leakage meaningfully, so check the trap/category label doesn't
        # leak instead (would hint at the intended issue)
        assert case["category"] not in q
        ans = __import__("json").loads((build_cases.HERE / "expected" / cid / "answer.json").read_text())
        assert ans["expected_requires_disclosure"] == case["expected_requires_disclosure"]
