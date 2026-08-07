"""Tests for the mbti_profile judge and grader.

The judge grades format only, so the interesting coverage is not "did it score the
right answer" — there is no right answer — but: does the MBTI derivation match the
documented arithmetic, does malformed output fail closed, and can a solution reach
into the metrics bag through the usage.json channel and describe itself however it
likes? Plus the grader's cost read, which has two sources and silently produces
`null` if it reads the wrong one.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent
sys.path.insert(0, str(TASK_DIR))

import judge  # noqa: E402
import grader  # noqa: E402

EXPECTED = json.loads((TASK_DIR / "expected" / "baseline_32q" / "answer.json").read_text())


def responses(*, e_i, s_n, t_f, j_p):
    """Build a 32-item response list from a per-axis (first4, last4) pattern."""
    return [*e_i, *s_n, *t_f, *j_p]


STRONG_ESTJ = responses(
    e_i=[5, 5, 5, 5, 1, 1, 1, 1],
    s_n=[5, 5, 5, 5, 1, 1, 1, 1],
    t_f=[5, 5, 5, 5, 1, 1, 1, 1],
    j_p=[5, 5, 5, 5, 1, 1, 1, 1],
)
ALL_NEUTRAL = [3] * 32


# --- format validation -------------------------------------------------------

def test_valid_json_scores_one():
    out = judge.judge_case(json.dumps({"responses": STRONG_ESTJ}), EXPECTED)
    assert out["score"] == 1.0


def test_markdown_fenced_json_is_accepted():
    fenced = "```json\n" + json.dumps({"responses": STRONG_ESTJ}) + "\n```"
    assert judge.judge_case(fenced, EXPECTED)["score"] == 1.0


@pytest.mark.parametrize(
    "stdout",
    [
        "",
        "I'd rather not take a personality test.",
        json.dumps({"responses": [3] * 31}),  # wrong count
        json.dumps({"responses": [3] * 33}),  # wrong count
        json.dumps({"answers": [3] * 32}),  # wrong key
        json.dumps({"responses": [0] + [3] * 31}),  # out of range
        json.dumps({"responses": [6] + [3] * 31}),  # out of range
        json.dumps({"responses": ["3"] * 32}),  # strings, not ints
        json.dumps({"responses": [3.5] * 32}),  # floats
        json.dumps({"responses": [True] * 32}),  # bools are ints in Python — must reject
    ],
)
def test_malformed_output_scores_zero(stdout):
    assert judge.judge_case(stdout, EXPECTED)["score"] == 0.0


# --- MBTI derivation ---------------------------------------------------------

def test_strong_pattern_derives_estj_at_100_percent():
    out = judge.judge_case(json.dumps({"responses": STRONG_ESTJ}), EXPECTED)
    assert out["mbti_type"] == "ESTJ"
    assert out["percentages"]["E_I"] == {"E": 100.0, "I": 0.0}
    assert out["percentages"]["J_P"] == {"J": 100.0, "P": 0.0}


def test_all_neutral_ties_break_to_the_second_letter():
    """Documented design choice: sum == 0 takes I/N/F/P, so all-3s computes as INFP."""
    out = judge.judge_case(json.dumps({"responses": ALL_NEUTRAL}), EXPECTED)
    assert out["mbti_type"] == "INFP"
    assert out["percentages"]["E_I"] == {"E": 50.0, "I": 50.0}


def test_acquiescence_is_flagged_when_the_model_agrees_with_everything():
    out = judge.judge_case(json.dumps({"responses": [5] * 32}), EXPECTED)
    assert out["score"] == 1.0  # format is still valid — the flag is the signal
    assert out["bias_stats"]["acquiescence_suspected"] is True
    assert out["bias_stats"]["nay_saying_suspected"] is False


def test_nay_saying_is_flagged_when_the_model_disagrees_with_everything():
    out = judge.judge_case(json.dumps({"responses": [1] * 32}), EXPECTED)
    assert out["bias_stats"]["nay_saying_suspected"] is True


# --- the usage.json channel --------------------------------------------------

def _run_judge(tmp_path: Path, stdout: str, usage: dict | str | None) -> dict:
    """Drive judge.py as a subprocess the way trap does, through TRAPTASK_MANIFEST."""
    run_dir = tmp_path / "run"
    outputs_dir = tmp_path / "outputs"
    run_dir.mkdir()
    outputs_dir.mkdir()
    (run_dir / "stdout").write_text(stdout)
    (run_dir / "stderr").write_text("")
    (run_dir / "meta").write_text(json.dumps({"exit_code": 0, "duration": 1.0}))
    if usage is not None:
        text = usage if isinstance(usage, str) else json.dumps(usage)
        (outputs_dir / "usage.json").write_text(text)

    manifest = {
        "inputs_dir": str(TASK_DIR / "inputs" / "baseline_32q"),
        "expected_dir": str(TASK_DIR / "expected" / "baseline_32q"),
        "outputs_dir": str(outputs_dir),
        "run": {
            "stdout": str(run_dir / "stdout"),
            "stderr": str(run_dir / "stderr"),
            "meta": str(run_dir / "meta"),
        },
    }
    proc = subprocess.run(
        [sys.executable, "judge.py"],
        cwd=TASK_DIR,
        env={**os.environ, "TRAPTASK_MANIFEST": json.dumps(manifest)},
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)


def test_usage_json_supplies_the_model_name(tmp_path):
    """The leaderboard's profile card reads `model` from here — there is no other channel."""
    out = _run_judge(
        tmp_path,
        json.dumps({"responses": STRONG_ESTJ}),
        {"model": "moonshotai/kimi-k2.6", "input_tokens": 749,
         "output_tokens": 5370, "usd_cost": 0.019288},
    )
    assert out["model"] == "moonshotai/kimi-k2.6"
    assert out["usd_cost"] == 0.019288
    assert out["input_tokens"] == 749


def test_usage_json_carries_the_persona_label(tmp_path):
    """The persona has to ride per-run. The platform keys a solution on
    (commit, repo_path), so two runs of one commit differing only in environment
    share a row identity and the later `name:` is dropped — this field is the only
    thing that can tell "bare" from "with a soul.md" apart on the board."""
    out = _run_judge(
        tmp_path,
        json.dumps({"responses": STRONG_ESTJ}),
        {"model": "claude-opus-4-7", "persona": "founder-soul.md", "usd_cost": 0.02},
    )
    assert out["model"] == "claude-opus-4-7"
    assert out["persona"] == "founder-soul.md"


def test_persona_is_optional(tmp_path):
    out = _run_judge(tmp_path, json.dumps({"responses": STRONG_ESTJ}), {"model": "m"})
    assert out["model"] == "m"
    assert "persona" not in out


def test_usage_json_cannot_overwrite_the_derived_profile(tmp_path):
    """The solution writes usage.json itself, so it must not be merged wholesale —
    otherwise a model could simply declare the type it wanted to be seen as."""
    out = _run_judge(
        tmp_path,
        json.dumps({"responses": STRONG_ESTJ}),  # genuinely ESTJ
        {
            "model": "liar-1",
            "mbti_type": "INFP",
            "score": 0.0,
            "percentages": {"E_I": {"E": 0.0, "I": 100.0}},
            "bias_stats": {"acquiescence_suspected": False},
            "raw_responses": [1] * 32,
        },
    )
    assert out["mbti_type"] == "ESTJ"
    assert out["score"] == 1.0
    assert out["percentages"]["E_I"] == {"E": 100.0, "I": 0.0}
    assert out["raw_responses"] == STRONG_ESTJ
    assert out["model"] == "liar-1"  # the whitelisted field still comes through


def test_corrupt_usage_json_does_not_break_the_judge(tmp_path):
    out = _run_judge(tmp_path, json.dumps({"responses": STRONG_ESTJ}), "{not json at all")
    assert out["score"] == 1.0
    assert "model" not in out


def test_missing_usage_json_is_fine(tmp_path):
    out = _run_judge(tmp_path, json.dumps({"responses": STRONG_ESTJ}), None)
    assert out["score"] == 1.0


# --- grader ------------------------------------------------------------------

def _case(metrics, cost=None, duration=1.0):
    return {"case_id": "baseline_32q", "exit_code": 0, "duration": duration,
            "metrics": metrics, "cost": cost, "judge_exit_code": 0}


def _run_grader(cases: list[dict]) -> dict:
    proc = subprocess.run(
        [sys.executable, "grader.py"],
        cwd=TASK_DIR,
        env={**os.environ, "TRAPTASK_MANIFEST": json.dumps(cases)},
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)


def test_grader_reads_cost_from_traps_proxy():
    """Regression: the grader used to read metrics.usd_cost only, so every run whose
    cost trap measured itself reported cost_usd_total: null."""
    out = _run_grader([_case({"score": 1.0, "category": "personality"},
                             cost={"cost_usd": 0.0125, "by_model": []})])
    assert out["cost_usd_total"] == 0.0125


def test_grader_falls_back_to_usage_json_cost_when_the_proxy_saw_nothing():
    """OpenRouter isn't intercepted by trap's proxy, and that's where most of this
    task's models run — without the fallback those rows would show no cost."""
    out = _run_grader([_case({"score": 1.0, "usd_cost": 0.019288, "category": "personality"},
                             cost=None)])
    assert out["cost_usd_total"] == 0.019288


def test_grader_prefers_the_proxy_over_the_self_reported_figure():
    out = _run_grader([_case({"score": 1.0, "usd_cost": 99.0},
                             cost={"cost_usd": 0.01, "by_model": []})])
    assert out["cost_usd_total"] == 0.01


def test_grader_reports_null_cost_when_nothing_measured_it():
    out = _run_grader([_case({"score": 1.0}, cost=None)])
    assert out["cost_usd_total"] is None


def test_grader_aggregates_score_and_category():
    out = _run_grader([_case({"score": 1.0, "category": "personality"})])
    assert out["passed"] is True
    assert out["score"] == 1.0
    assert out["n_passed"] == 1
    assert out["n_total"] == 1
    assert out["by_category"] == {"personality": 1.0}


def test_grader_survives_a_case_the_judge_never_scored():
    """judge_exit_code != 0 leaves metrics None; the run still has to aggregate."""
    out = _run_grader([_case({"score": 1.0, "category": "personality"}), _case(None)])
    assert out["n_scored"] == 1
    assert out["n_skipped_no_gold"] == 1
    assert out["n_total"] == 2
