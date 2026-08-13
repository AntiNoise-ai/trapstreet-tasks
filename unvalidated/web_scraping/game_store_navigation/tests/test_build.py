import json
import sys
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_cases  # noqa: E402


VALID_CASE = {
    "id": "case_01",
    "mechanism": "static",
    "question": "What is the price of X?",
    "gold": "14.99",
}


def test_valid_case_passes():
    build_cases.validate_case(VALID_CASE)  # should not raise


@pytest.mark.parametrize("missing_field", ["id", "mechanism", "question", "gold"])
def test_missing_field_rejected(missing_field):
    case = {k: v for k, v in VALID_CASE.items() if k != missing_field}
    with pytest.raises(ValueError):
        build_cases.validate_case(case)


@pytest.mark.parametrize("bad_id", ["leopard_case", "CASE_01", "case_1a", "case"])
def test_non_opaque_id_rejected(bad_id):
    case = {**VALID_CASE, "id": bad_id}
    with pytest.raises(ValueError):
        build_cases.validate_case(case)


def test_unknown_mechanism_rejected():
    case = {**VALID_CASE, "mechanism": "not_a_real_mechanism"}
    with pytest.raises(ValueError):
        build_cases.validate_case(case)


def test_non_numeric_gold_rejected():
    case = {**VALID_CASE, "gold": "not a number"}
    with pytest.raises(ValueError):
        build_cases.validate_case(case)


def test_gold_answers_match_recomputation_from_site_src():
    """The real regression this guards: gold.cases.json values must equal
    what's mechanically derivable from site_src's own data files, not a
    hand-typed number that could silently drift (this caught a real 9-vs-10
    counting mistake during authoring)."""
    data = json.loads(build_cases.GOLD.read_text())
    build_cases.verify_gold_answers(data["cases"])  # should not raise


def test_gold_answers_mismatch_is_caught():
    data = json.loads(build_cases.GOLD.read_text())
    cases = json.loads(json.dumps(data["cases"]))  # deep copy
    for c in cases:
        if c["id"] == "case_09":
            c["gold"] = "999"
    with pytest.raises(ValueError):
        build_cases.verify_gold_answers(cases)


def test_build_generates_all_cases_with_no_answer_leak(tmp_path, monkeypatch):
    """Runs the real build() against the real gold.cases.json + site_src,
    into a throwaway inputs/expected under this task dir (build_cases.py
    resolves paths relative to itself, not cwd) -- then checks every case
    directory got created and that inputs/ never contains the gold answer.
    """
    build_cases.build()
    data = json.loads(build_cases.GOLD.read_text())
    for case in data["cases"]:
        cid = case["id"]
        in_dir = build_cases.HERE / "inputs" / cid
        exp_dir = build_cases.HERE / "expected" / cid
        assert in_dir.is_dir()
        assert exp_dir.is_dir()
        assert (in_dir / "question.txt").exists()
        assert (exp_dir / "answer.json").exists()

        answer = json.loads((exp_dir / "answer.json").read_text())
        assert answer["gold"] == case["gold"]

        # question.txt (what the solution reads before it ever loads the
        # site) must not itself state the answer -- the site's own pages
        # legitimately display prices (that's the whole point, e.g. case_01
        # asks for a price that's plainly shown on the catalog page), so the
        # gold value showing up inside site_src/*.html or *.json is correct,
        # not a leak. Only question.txt is checked here.
        question_text = (in_dir / "question.txt").read_text()
        assert case["gold"] not in question_text.split(), (
            f"{cid}: gold value {case['gold']!r} leaked into question.txt"
        )
