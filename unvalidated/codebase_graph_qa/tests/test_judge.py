# tests/test_judge.py
import json
import sys, pathlib
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import judge  # noqa: E402


EXPECTED = {"id": "case_01", "category": "call_chain", "answer": ["a.py:f", "b.py:g"]}


def test_exact_match_scores_one():
    stdout = json.dumps({"answer": ["a.py:f", "b.py:g"]})
    result = judge.score_case(stdout, EXPECTED)
    assert result["score"] == pytest.approx(1.0)
    assert result["precision"] == pytest.approx(1.0)
    assert result["recall"] == pytest.approx(1.0)


def test_near_miss_partial_credit():
    # one correct, one missing, one wrong extra -> precision=0.5, recall=0.5, f1=0.5
    stdout = json.dumps({"answer": ["a.py:f", "c.py:h"]})
    result = judge.score_case(stdout, EXPECTED)
    assert result["precision"] == pytest.approx(0.5)
    assert result["recall"] == pytest.approx(0.5)
    assert result["score"] == pytest.approx(0.5)
    assert result["missing"] == ["b.py:g".casefold()]
    assert result["extra"] == ["c.py:h".casefold()]


def test_completely_wrong_scores_zero():
    stdout = json.dumps({"answer": ["z.py:nope"]})
    result = judge.score_case(stdout, EXPECTED)
    assert result["score"] == pytest.approx(0.0)


def test_shotgun_answer_is_self_punishing():
    """Anti-shotgun: listing many plausible-looking extras should score
    much worse than a precise correct answer, without needing an explicit
    MAX_FINDINGS cap (F1's precision term does the work)."""
    shotgun = json.dumps({"answer": ["a.py:f", "b.py:g"] + [f"x{i}.py:n" for i in range(20)]})
    precise = json.dumps({"answer": ["a.py:f", "b.py:g"]})
    shotgun_score = judge.score_case(shotgun, EXPECTED)["score"]
    precise_score = judge.score_case(precise, EXPECTED)["score"]
    assert shotgun_score < precise_score
    assert precise_score == pytest.approx(1.0)


def test_malformed_json_scores_zero_not_crash():
    result = judge.score_case("this is not json at all {{{", EXPECTED)
    assert result["score"] == 0.0
    assert "reason" in result


def test_missing_answer_key_scores_zero():
    result = judge.score_case(json.dumps({"findings": []}), EXPECTED)
    assert result["score"] == 0.0


def test_answer_not_a_list_scores_zero():
    result = judge.score_case(json.dumps({"answer": "a.py:f"}), EXPECTED)
    assert result["score"] == 0.0


def test_empty_answer_list_scores_zero():
    result = judge.score_case(json.dumps({"answer": []}), EXPECTED)
    assert result["score"] == 0.0


def test_non_string_entries_are_skipped_not_crash():
    stdout = json.dumps({"answer": ["a.py:f", 42, None, {"nested": True}, "b.py:g"]})
    result = judge.score_case(stdout, EXPECTED)
    assert result["score"] == pytest.approx(1.0)


def test_case_insensitive_matching():
    stdout = json.dumps({"answer": ["A.PY:F", "B.py:G"]})
    result = judge.score_case(stdout, EXPECTED)
    assert result["score"] == pytest.approx(1.0)


def test_repo_prefix_is_stripped():
    stdout = json.dumps({"answer": ["repo/a.py:f", "./repo/b.py:g"]})
    result = judge.score_case(stdout, EXPECTED)
    assert result["score"] == pytest.approx(1.0)


def test_whitespace_is_trimmed():
    stdout = json.dumps({"answer": [" a.py:f ", "b.py:g\n"]})
    result = judge.score_case(stdout, EXPECTED)
    assert result["score"] == pytest.approx(1.0)


def test_not_found_sentinel_exact_match():
    expected = {"id": "case_15", "category": "doc_code_xref", "answer": ["NOT_FOUND"]}
    result = judge.score_case(json.dumps({"answer": ["NOT_FOUND"]}), expected)
    assert result["score"] == pytest.approx(1.0)


def test_not_found_sentinel_mismatch_scores_zero():
    expected = {"id": "case_15", "category": "doc_code_xref", "answer": ["NOT_FOUND"]}
    result = judge.score_case(json.dumps({"answer": ["src/x.py:renamed_fn"]}), expected)
    assert result["score"] == pytest.approx(0.0)


def test_json_wrapped_in_prose_is_still_parsed():
    stdout = 'Here is my answer:\n' + json.dumps({"answer": ["a.py:f", "b.py:g"]}) + '\nHope that helps!'
    result = judge.score_case(stdout, EXPECTED)
    assert result["score"] == pytest.approx(1.0)


def test_json_after_prose_containing_braces_is_still_parsed():
    """Regression test: a naive 'first { to last }' substring scan breaks
    the moment any brace appears in prose before the real JSON -- e.g. a
    model narrating "Looking at handle_order() { it calls ... }" before
    its actual answer. The real answer must still be found and scored."""
    stdout = (
        'Let me trace this. The entry point looks like {roughly} a dispatcher, '
        'calling into {payment, inventory} subsystems.\n\n'
        'Final answer:\n' + json.dumps({"answer": ["a.py:f", "b.py:g"]})
    )
    result = judge.score_case(stdout, EXPECTED)
    assert result["score"] == pytest.approx(1.0)


def test_json_in_markdown_code_fence_is_parsed():
    stdout = '```json\n' + json.dumps({"answer": ["a.py:f", "b.py:g"]}) + '\n```'
    result = judge.score_case(stdout, EXPECTED)
    assert result["score"] == pytest.approx(1.0)


def test_deeply_nested_json_does_not_crash():
    nested = "[" * 10000 + "]" * 10000
    stdout = json.dumps({"answer": [nested]})
    result = judge.score_case(stdout, EXPECTED)
    assert result["score"] == 0.0  # nested list isn't a usable string identifier, no match


def test_main_handles_nonzero_exit_code(tmp_path, monkeypatch, capsys):
    stdout_file = tmp_path / "stdout.txt"
    stdout_file.write_text("")
    meta_file = tmp_path / "meta.json"
    meta_file.write_text(json.dumps({"exit_code": 1, "duration": 0.1}))
    exp_dir = tmp_path / "expected"
    exp_dir.mkdir()
    (exp_dir / "answer.json").write_text(json.dumps(EXPECTED))

    manifest = {
        "inputs_dir": str(tmp_path),
        "expected_dir": str(exp_dir),
        "outputs_dir": str(tmp_path),
        "run": {"stdout": str(stdout_file), "stderr": str(stdout_file), "meta": str(meta_file)},
    }
    monkeypatch.setenv("TRAPTASK_MANIFEST", json.dumps(manifest))
    judge.main()
    out = json.loads(capsys.readouterr().out)
    assert out["score"] == 0.0
    assert "exited 1" in out["reason"]
