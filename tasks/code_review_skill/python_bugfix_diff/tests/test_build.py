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
        "source_commit_url": "https://github.com/example/repo/commit/" + ("a" * 40),
        "license": "MIT",
        "file_path": "src/example.py",
        "snippet_start_line": 10,
        "snippet_text": "def f():\n    return 1\n",
        "buggy_line": 11,
        "line_tolerance": 2,
        "keywords": ["off-by-one", "boundary"],
        "bug_description": "example bug",
        "parent_commit_sha": "b" * 40,
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


def test_rejects_malformed_parent_commit_sha():
    c = _case(parent_commit_sha="not-a-real-sha")
    with pytest.raises(ValueError, match="40-char lowercase hex SHA"):
        build_cases.validate_case(c)


def test_rejects_uppercase_parent_commit_sha():
    c = _case(parent_commit_sha="B" * 40)
    with pytest.raises(ValueError, match="40-char lowercase hex SHA"):
        build_cases.validate_case(c)


def test_rejects_parent_commit_sha_equal_to_fix_commit():
    # parent_commit_sha matching the fix commit would hand solutions the
    # answer via a clonable ref -- must be refused outright.
    fix_sha = "a" * 40
    c = _case(
        source_commit_url=f"https://github.com/example/repo/commit/{fix_sha}",
        parent_commit_sha=fix_sha,
    )
    with pytest.raises(ValueError, match="would leak the answer"):
        build_cases.validate_case(c)


def test_rejects_parent_commit_sha_equal_to_fix_commit_with_query_string():
    # A naive rsplit("/")[-1] extraction would treat "<sha>?diff=split" as
    # the fix sha and never match a clean parent_commit_sha -- silently
    # bypassing the leak check. Must still be caught via regex extraction.
    fix_sha = "a" * 40
    c = _case(
        source_commit_url=f"https://github.com/example/repo/commit/{fix_sha}?diff=split",
        parent_commit_sha=fix_sha,
    )
    with pytest.raises(ValueError, match="would leak the answer"):
        build_cases.validate_case(c)


def test_rejects_parent_commit_sha_equal_to_fix_commit_case_insensitive():
    # The same commit written in different case (GitHub SHAs are
    # case-insensitive) must still be caught, not bypassed by a naive
    # case-sensitive string comparison.
    fix_sha_upper = "A" * 40
    fix_sha_lower = "a" * 40
    c = _case(
        source_commit_url=f"https://github.com/example/repo/commit/{fix_sha_upper}",
        parent_commit_sha=fix_sha_lower,
    )
    with pytest.raises(ValueError, match="would leak the answer"):
        build_cases.validate_case(c)
