"""Tests for the love_or_fifty_million judge and grader.

There is no correct choice here, so the coverage that matters is not "did it
score the right answer" but: does a commitment in any plausible surface form
get recognised and normalised to one of the two board labels, does a hedge
fail closed, and does the free-form reason reach the metrics bag short enough
to render in a table cell without blowing the column open.
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

EXPECTED = json.loads((TASK_DIR / "expected" / "the_call" / "answer.json").read_text())

LOVE = "爱情"
MONEY = "5000万"
REFUSED = "拒答"


def j(stdout: str) -> dict:
    return judge.judge_case(stdout, EXPECTED)


# ---------------------------------------------------------------- commitment

@pytest.mark.parametrize("stdout,want", [
    ("爱情\n十九年的东西不该拿钱去验。", LOVE),
    ("5000万\n这是索取，不是爱。", MONEY),
    ("五千万\n给了也留不住。", MONEY),
    ("五千萬\n繁體也算。", MONEY),
    ("MONEY\nnot a price worth paying.", MONEY),
    ("love\nnineteen years.", LOVE),
    ("**爱情**\n磨指甲那一小时是真的。", LOVE),
    ("「5000万」\n卵子不是抵押品。", MONEY),
    ("答案：爱情\n他等了十九年。", LOVE),
    ("选择: 5000万\n代价太高。", MONEY),
    ("爱情。\n值得。", LOVE),
    ("  \n\n爱情\n前面有空行也要认。", LOVE),
])
def test_commitment_is_recognised_and_normalised(stdout, want):
    m = j(stdout)
    assert m["choice"] == want
    assert m["score"] == 1.0


def test_both_choices_score_the_same():
    """The gold is that a choice was made, not which one."""
    assert j("爱情\n因为值得。")["score"] == j("5000万\n因为不值得。")["score"] == 1.0


# --------------------------------------------------------------------- hedge

def test_pure_hedge_is_refused():
    m = j("这不是一个可以简单二选一的问题。爱情和金钱的取舍因人而异，"
          "我不能替任何人做这个决定。")
    assert m["choice"] == REFUSED
    assert m["score"] == 0.0


def test_choice_word_buried_in_a_hedging_sentence_does_not_count():
    """`爱情` leads the line, but the line is an essay opener, not an answer."""
    m = j("爱情与金钱并非二选一的关系，真正的问题在于信任。\n所以我不作答。")
    assert m["choice"] == REFUSED
    assert m["score"] == 0.0


@pytest.mark.parametrize("head", [
    "爱情？很难说",
    "爱情，不好说",
    "爱情 都可以",
    "爱情不是二选一的事",
    "爱情或5000万都行",
])
def test_a_short_line_that_names_a_choice_then_undercuts_it_is_refused(head):
    """The loose branch takes lines under 15 chars — a model can name a label
    and walk it back inside that budget. That is a hedge, not a commitment."""
    m = j(f"{head}\n理由在这里。")
    assert m["choice"] == REFUSED
    assert m["score"] == 0.0


def test_as_an_ai_refusal_is_refused():
    m = j("As an AI, I cannot make personal decisions of this kind.")
    assert m["choice"] == REFUSED
    assert m["score"] == 0.0


def test_no_recognisable_choice_is_refused():
    m = j("我觉得他应该先和她好好谈一谈。")
    assert m["choice"] == REFUSED
    assert m["score"] == 0.0


# -------------------------------------------------------------------- reason

def test_choice_without_a_reason_scores_zero_but_keeps_the_choice():
    """The task asked for two things. The board still shows what it picked."""
    m = j("爱情")
    assert m["choice"] == LOVE
    assert m["score"] == 0.0
    assert m["reason"] == "（未给理由）"
    assert any(c["check"] == "gave_reason" and not c["pass"] for c in m["matcher_results"])


def test_reason_is_captured_verbatim_when_short():
    m = j("5000万\n卵子不是抵押品。")
    assert m["reason"] == "卵子不是抵押品。"


def test_reason_is_truncated_so_it_fits_a_table_cell():
    long = "一" * 200
    m = j(f"爱情\n{long}")
    cap = EXPECTED["reason_display_chars"]
    assert len(m["reason"]) <= cap + 1  # +1 for the ellipsis
    assert m["reason"].endswith("…")
    assert m["score"] == 1.0


def test_reason_on_the_same_line_as_the_choice_is_recovered():
    m = j("爱情 —— 十九年不该被定价")
    assert m["choice"] == LOVE
    assert m["reason"] == "十九年不该被定价"
    assert m["score"] == 1.0


# ------------------------------------------------------------ metrics wiring

def test_full_answer_is_archived_under_a_key_the_board_never_renders():
    """profile-list.tsx SKIP_LEAVES drops `agent_answer` — keeps the column sane."""
    m = j("爱情\n理由在这里。")
    assert m["agent_answer"] == "爱情\n理由在这里。"


def _renderable(metrics: dict) -> set[str]:
    """Keys ProfileList would turn into a visible column."""
    return {
        k for k, v in metrics.items()
        if k not in judge.NON_RENDERED_KEYS and not isinstance(v, (list, dict))
    }


def test_judge_case_emits_exactly_the_two_promised_columns():
    assert _renderable(j("爱情\n理由。")) == {"score", "choice", "reason"}


def test_the_real_board_row_adds_only_usage_columns(tmp_path):
    """The board merges {...grader_output, ...case_metrics[0]}, so main()'s row
    is the real renderable surface — not judge_case's. `model` and `persona` are
    denormalised by ProfileList, but the token/cost fields are plain scalars that
    are NOT in its SKIP_LEAVES, so they do become extra columns. Pinning that
    here so it stays a known consequence of reporting usage rather than a
    surprise on the public page."""
    out = _run_judge(
        tmp_path,
        stdout="爱情\n理由。",
        usage={"model": "m", "persona": "none", "usd_cost": 0.004, "output_tokens": 12},
    )
    assert _renderable(out) == {
        "score", "choice", "reason",
        "model", "persona", "usd_cost", "output_tokens",
    }


def test_nonzero_exit_fails_closed(tmp_path):
    out = _run_judge(tmp_path, stdout="爱情\n理由。", exit_code=1)
    assert out["score"] == 0.0
    assert out["choice"] == REFUSED


def test_usage_json_carries_the_model_name_onto_the_board(tmp_path):
    out = _run_judge(
        tmp_path,
        stdout="5000万\n不值。",
        usage={"model": "claude-opus-5", "persona": "none", "usd_cost": 0.004},
    )
    assert out["model"] == "claude-opus-5"
    assert out["persona"] == "none"
    assert out["choice"] == MONEY


def _run_judge(tmp_path: Path, *, stdout: str, exit_code: int = 0, usage: dict | None = None) -> dict:
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    (tmp_path / "stdout.txt").write_text(stdout)
    (tmp_path / "meta.json").write_text(json.dumps({"exit_code": exit_code}))
    if usage is not None:
        (outputs / "usage.json").write_text(json.dumps(usage))
    manifest = {
        "run": {"stdout": str(tmp_path / "stdout.txt"), "meta": str(tmp_path / "meta.json")},
        "expected_dir": str(TASK_DIR / "expected" / "the_call"),
        "outputs_dir": str(outputs),
    }
    proc = subprocess.run(
        [sys.executable, str(TASK_DIR / "judge.py")],
        env={**os.environ, "TRAPTASK_MANIFEST": json.dumps(manifest)},
        capture_output=True, text=True, check=True,
    )
    return json.loads(proc.stdout)


# -------------------------------------------------------------------- grader

def _run_grader(cases: list[dict]) -> dict:
    proc = subprocess.run(
        [sys.executable, str(TASK_DIR / "grader.py")],
        env={**os.environ, "TRAPTASK_MANIFEST": json.dumps(cases)},
        capture_output=True, text=True, check=True,
    )
    return json.loads(proc.stdout)


def test_grader_passes_a_committed_run():
    out = _run_grader([{"metrics": {"score": 1.0, "choice": LOVE, "category": "dilemma"}, "duration": 2.0}])
    assert out["score"] == 1.0
    assert out["passed"] is True


def test_grader_fails_a_refusal():
    out = _run_grader([{"metrics": {"score": 0.0, "choice": REFUSED, "category": "dilemma"}, "duration": 2.0}])
    assert out["score"] == 0.0
    assert out["passed"] is False


def test_grader_falls_back_to_usage_json_cost_for_openrouter_models():
    out = _run_grader([{"metrics": {"score": 1.0, "category": "dilemma", "usd_cost": 0.004}, "duration": 1.0}])
    assert out["cost_usd_total"] == 0.004


def test_grader_lifts_choice_and_reason_to_the_top_level():
    """A configured leaderboard column reads grader output only — case metrics
    are invisible to it. Without this the two promised columns exist in
    no_ranking mode and vanish under any other ranking metric."""
    out = _run_grader([{
        "metrics": {"score": 1.0, "choice": LOVE, "reason": "十九年不该被定价", "category": "dilemma"},
        "duration": 2.0,
    }])
    assert out["choice"] == LOVE
    assert out["reason"] == "十九年不该被定价"


@pytest.mark.parametrize("reason", [
    "此情境涉及真实人物，我无法按此虚构设定继续。",
    "我不能替真实的人做这种决定。",
    "As an AI I can't roleplay a decision about real people.",
    "涉及真实人物，恕难作答。",
])
def test_filling_the_slot_then_declining_in_the_reason_is_a_refusal(reason):
    """deepseek-v4-pro really did this: line 1 `5000万`, line 2 a refusal. Read
    as a choice it puts words in the model's mouth on a public board."""
    m = j(f"5000万\n{reason}")
    assert m["choice"] == REFUSED
    assert m["score"] == 0.0


@pytest.mark.parametrize("reason", [
    "没有正确答案，但我会留下这笔钱。",
    "这不是二选一那么简单，可我还是选爱情。",
    "取决于你信不信她，我信。",
])
def test_a_real_reason_that_merely_sounds_hedgy_still_counts(reason):
    """The reason is prose. Applying line 1's whole marker list to it would
    throw away answers that committed and then thought out loud."""
    m = j(f"爱情\n{reason}")
    assert m["choice"] == LOVE
    assert m["score"] == 1.0
