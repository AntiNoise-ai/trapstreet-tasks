# tests/test_judge.py
import json
import sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import judge  # noqa: E402

EXPECTED = {
    "id": "case_01",
    "bug_category": "off_by_one",
    "file_path": "src/croniter/croniter.py",
    "buggy_line": 1276,
    "line_tolerance": 2,
    "keywords": ["off-by-one", "1-based", "modulo", "boundary condition", "wrong range"],
}


def _out(findings):
    return json.dumps({"findings": findings})


def test_exact_hit_scores_one():
    out = _out([{"file": "croniter.py", "line": 1276,
                 "description": "classic off-by-one: 1-based month uses raw modulo"}])
    r = judge.score_case(out, EXPECTED)
    assert r["score"] == 1.0 and r["hit_index"] == 0


def test_near_miss_within_tolerance_hits():
    out = _out([{"file": "croniter.py", "line": 1277,
                 "description": "off-by-one in the month bound"}])
    r = judge.score_case(out, EXPECTED)
    assert r["score"] == 1.0


def test_line_outside_tolerance_misses():
    out = _out([{"file": "croniter.py", "line": 1300,
                 "description": "off-by-one modulo issue"}])
    r = judge.score_case(out, EXPECTED)
    assert r["score"] == 0.0


def test_wrong_file_misses():
    out = _out([{"file": "other_file.py", "line": 1276,
                 "description": "off-by-one modulo issue"}])
    r = judge.score_case(out, EXPECTED)
    assert r["score"] == 0.0


def test_missing_keyword_misses():
    out = _out([{"file": "croniter.py", "line": 1276,
                 "description": "this returns the wrong value sometimes"}])
    r = judge.score_case(out, EXPECTED)
    assert r["score"] == 0.0
    assert r["best_match_signals"]["file_match"] is True
    assert r["best_match_signals"]["line_match"] is True
    assert r["best_match_signals"]["keyword_match"] is False


def test_hit_beyond_first_five_ignored_anti_shotgun():
    padding = [{"file": "x.py", "line": i, "description": "unrelated"} for i in range(5)]
    real_hit = {"file": "croniter.py", "line": 1276, "description": "off-by-one modulo issue"}
    out = _out(padding + [real_hit])
    r = judge.score_case(out, EXPECTED)
    assert r["score"] == 0.0
    assert r["n_findings_considered"] == 5


def test_hit_within_first_five_counts():
    padding = [{"file": "x.py", "line": i, "description": "unrelated"} for i in range(4)]
    real_hit = {"file": "croniter.py", "line": 1276, "description": "off-by-one modulo issue"}
    out = _out(padding + [real_hit])
    r = judge.score_case(out, EXPECTED)
    assert r["score"] == 1.0 and r["hit_index"] == 4


def test_malformed_json():
    r = judge.score_case("I think the bug is on line 1276", EXPECTED)
    assert r["score"] == 0.0 and r["format_ok"] is False


def test_fenced_json_parses():
    inner = _out([{"file": "croniter.py", "line": 1276, "description": "off-by-one modulo issue"}])
    out = "```json\n" + inner + "\n```"
    r = judge.score_case(out, EXPECTED)
    assert r["score"] == 1.0


def test_missing_findings_key():
    r = judge.score_case('{"review": "looks fine"}', EXPECTED)
    assert r["score"] == 0.0 and r["format_ok"] is False


def test_non_dict_finding_entries_ignored_not_crashed():
    out = _out(["just a string finding"])
    r = judge.score_case(out, EXPECTED)
    assert r["score"] == 0.0


def test_empty_findings_list():
    out = _out([])
    r = judge.score_case(out, EXPECTED)
    assert r["score"] == 0.0 and r["hit_index"] is None
