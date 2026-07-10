# tests/test_build.py
import sys, pathlib
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_cases  # noqa: E402


def _case(**over):
    base = {
        "id": "case_01",
        "bug_category": "off_by_one",
        "source_repo": "example/repo",
        "source_commit_url": "https://github.com/example/repo/commit/abc123",
        "license": "MIT",
        "file_path": "src/example.py",
        "snippet_start_line": 10,
        "snippet_text": "def f():\n    return 1\n",
        "buggy_line": 11,
        "line_tolerance": 2,
        "keywords": ["off-by-one", "boundary"],
        "bug_description": "example bug",
    }
    base.update(over)
    return base


def test_valid_case_passes():
    build_cases.validate_case(_case())  # no raise


def test_rejects_missing_field():
    c = _case(); del c["keywords"]
    with pytest.raises(ValueError, match="missing required field"):
        build_cases.validate_case(c)


def test_rejects_bad_id_pattern():
    c = _case(id="bug1")
    with pytest.raises(ValueError, match="case_NN"):
        build_cases.validate_case(c)


def test_rejects_disallowed_license():
    c = _case(license="GPL-3.0")
    with pytest.raises(ValueError, match="license must be one of"):
        build_cases.validate_case(c)


def test_rejects_buggy_line_out_of_range():
    c = _case(buggy_line=999)
    with pytest.raises(ValueError, match="out of snippet range"):
        build_cases.validate_case(c)


def test_rejects_too_few_keywords():
    c = _case(keywords=["only-one"])
    with pytest.raises(ValueError, match="at least 2 keywords"):
        build_cases.validate_case(c)


def test_render_snippet_line_numbers():
    out = build_cases.render_snippet(10, "def f():\n    return 1\n")
    lines = out.split("\n")
    assert lines[0].startswith("   10| def f():")
    assert lines[1].startswith("   11|     return 1")
    assert len(lines) == 2  # trailing blank line from the source text is not rendered
