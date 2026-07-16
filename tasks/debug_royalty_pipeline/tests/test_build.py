# tests/test_build.py
import sys, pathlib
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_cases  # noqa: E402


def test_validate_case_is_implemented():
    """This fails until you replace build_cases.validate_case()'s
    NotImplementedError stub with real validation logic. Once you do,
    replace this test with real cases: valid-case-passes, and one
    test per invariant validate_case() is supposed to catch."""
    with pytest.raises(NotImplementedError):
        build_cases.validate_case({})
