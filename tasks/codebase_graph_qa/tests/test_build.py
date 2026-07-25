# tests/test_build.py
import sys, pathlib
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_cases  # noqa: E402


def _base_case(**overrides):
    case = {
        "id": "case_01",
        "category": "call_chain",
        "files": {"a.py": "def f():\n    pass\n"},
        "question": "list stuff",
        "answer": ["a.py:f"],
    }
    case.update(overrides)
    return case


def test_valid_case_passes():
    build_cases.validate_case(_base_case())  # should not raise


def test_missing_field_raises():
    case = _base_case()
    del case["question"]
    with pytest.raises(ValueError, match="question"):
        build_cases.validate_case(case)


def test_bad_id_format_raises():
    with pytest.raises(ValueError, match="case_NN"):
        build_cases.validate_case(_base_case(id="my_bug_case"))


def test_unknown_category_raises():
    with pytest.raises(ValueError, match="category"):
        build_cases.validate_case(_base_case(category="vibes"))


def test_unsafe_path_raises():
    case = _base_case(files={"../etc/passwd": "x"})
    with pytest.raises(ValueError, match="unsafe file path"):
        build_cases.validate_case(case)


def test_duplicate_answer_entries_raise():
    case = _base_case(answer=["a.py:f", "a.py:f"])
    with pytest.raises(ValueError, match="duplicate"):
        build_cases.validate_case(case)


def test_answer_referencing_unknown_file_raises():
    case = _base_case(answer=["b.py:g"])
    with pytest.raises(ValueError, match="not in this case"):
        build_cases.validate_case(case)


def test_answer_bare_path_must_be_known_file():
    case = _base_case(category="import_chain", answer=["b.py"])
    with pytest.raises(ValueError, match="not in this case"):
        build_cases.validate_case(case)


def test_import_chain_bare_path_answer_ok():
    case = _base_case(category="import_chain", files={"a.py": "x", "b.py": "y"}, answer=["b.py"])
    build_cases.validate_case(case)  # should not raise


def test_doc_code_xref_requires_single_answer():
    case = _base_case(category="doc_code_xref", answer=["a.py:f", "a.py:g"])
    with pytest.raises(ValueError, match="exactly one entry"):
        build_cases.validate_case(case)


def test_doc_code_xref_not_found_sentinel_ok():
    case = _base_case(category="doc_code_xref", answer=["NOT_FOUND"])
    build_cases.validate_case(case)  # should not raise -- NOT_FOUND is exempt from file-ref check


def test_schema_fk_table_must_appear_in_schema_sql():
    case = _base_case(
        category="schema_fk",
        files={"schema.sql": "CREATE TABLE orders (id INTEGER);"},
        answer=["customers"],
    )
    with pytest.raises(ValueError, match="does not appear"):
        build_cases.validate_case(case)


def test_schema_fk_table_present_ok():
    case = _base_case(
        category="schema_fk",
        files={"schema.sql": "CREATE TABLE orders (id INTEGER);"},
        answer=["orders"],
    )
    build_cases.validate_case(case)  # should not raise


def test_gold_cases_all_validate():
    """Integration check: every case in the real gold.cases.json validates
    cleanly (no crashes, no invariant violations)."""
    data = __import__("json").loads(build_cases.GOLD.read_text())
    for case in data["cases"]:
        build_cases.validate_case(case)
