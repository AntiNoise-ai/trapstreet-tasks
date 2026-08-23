"""Tests for pdf_chart_reading.

Two things are worth protecting. The gold, because it is measured rather than
typed and a silent drift in the measurement would be invisible in review. And
the judge's answer contract, because the task it replaces had its judge reject
correct answers four times, every time through a rule about where in the reply
the answer sits.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

TASK = Path(__file__).parent.parent
GOLD = json.loads((TASK / "gold.cases.json").read_text())
CASES = {c["id"]: c for c in GOLD["cases"]}
GEOMETRY = json.loads((TASK / "gold_geometry.json").read_text())
STATED_TOTALS = {"2026": 18, "2027": 18, "2028": 17, "longer run": 18}


def run_judge(case_id: str, reply: str, tmp_path: Path) -> dict:
    (tmp_path / "stdout.txt").write_text(reply)
    manifest = {
        "inputs_dir": str(TASK / "inputs" / case_id),
        "expected_dir": str(TASK / "expected" / case_id),
        "outputs_dir": str(tmp_path),
        "run": {"stdout": str(tmp_path / "stdout.txt")},
    }
    p = subprocess.run([sys.executable, "judge.py"], cwd=TASK, capture_output=True, text=True,
                       env={**os.environ, "TRAPTASK_MANIFEST": json.dumps(manifest)})
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


# ------------------------------------------------------------------ the gold

def test_the_measurement_still_reproduces(tmp_path):
    """extract_gold.py against the original release must reproduce the committed file."""
    out = tmp_path / "regenerated.json"
    subprocess.run([sys.executable, "extract_gold.py", "sep_original.pdf", str(out)],
                   cwd=TASK, check=True, capture_output=True)
    assert json.loads(out.read_text()) == GEOMETRY


@pytest.mark.parametrize("figure", sorted(GEOMETRY))
def test_every_panel_sums_to_the_stated_participant_count(figure):
    """The release says eighteen submitted in June, one without a 2028 projection."""
    for panel, bins in GEOMETRY[figure].items():
        assert sum(bins.values()) == STATED_TOTALS[panel], f"{figure} {panel}"


def test_the_dot_plot_and_the_histogram_agree():
    """Figure 2 and figure 3.E encode the same variable; binning one must give the other."""
    for panel, bins in GEOMETRY["figure_3.E"].items():
        for label, expected in bins.items():
            # Bin labels are the eighth-point edges rounded to two places:
            # "3.63-3.87" is the half-open range [3.625, 3.875).
            lo, hi = (float(x) for x in label.split("-"))
            got = sum(c for level, c in GEOMETRY["figure_2"][panel].items()
                      if lo - 0.006 <= float(level) <= hi + 0.004)
            assert got == expected, f"{panel} {label}: figure 2 gives {got}, figure 3.E {expected}"


def test_questions_are_authored_from_the_measurement(tmp_path):
    out = tmp_path / "regenerated.cases.json"
    subprocess.run([sys.executable, "author_cases.py", "gold_geometry.json", str(out)],
                   cwd=TASK, check=True, capture_output=True)
    assert json.loads(out.read_text()) == GOLD


def test_no_case_is_answerable_from_the_text_layer():
    """Pages 1, 2, 16 and 17 ship with their text, and table 1 is a real table.

    It reports medians, central tendencies and ranges -- never a count of
    participants. The only counts stated anywhere in the text are the totals
    who submitted (nineteen in March, eighteen in June, one of those without a
    2028 projection), so no case may answer with one of those.
    """
    import pymupdf

    doc = pymupdf.open(TASK / "sep_charts.pdf")
    text = " ".join(p.get_text() for p in doc)
    stated = {"17", "18", "19"}
    for case in GOLD["cases"]:
        assert case["answer"] not in stated, (
            f"{case['id']} answers with a participant total the text states outright")

    # And the figure pages really are pixels.
    for i in range(3, 16):
        assert not doc[i - 1].get_text().strip()


# ----------------------------------------------------------------- the judge

# case_20 also requires both tied range labels, so a bare number is not enough;
# it gets its own test below.
NUMERIC_CASES = [c["id"] for c in GOLD["cases"]
                 if any(m["kind"] == "committed_value" for m in c["matchers"])
                 and not any(m["kind"] == "regex_required" for m in c["matchers"])]


@pytest.mark.parametrize("case_id", NUMERIC_CASES)
def test_a_committed_correct_answer_scores_one(case_id, tmp_path):
    answer = CASES[case_id]["answer"]
    reply = f"Reading the panel bar by bar and adding them up.\n\nANSWER: {answer}"
    assert run_judge(case_id, reply, tmp_path)["score"] == 1.0


@pytest.mark.parametrize("case_id", NUMERIC_CASES[:5])
def test_an_off_by_one_scores_zero(case_id, tmp_path):
    """The failure mode this task is built on: a bar of 9 read as 10."""
    wrong = float(CASES[case_id]["answer"]) + 1
    result = run_judge(case_id, f"ANSWER: {wrong:g}", tmp_path)
    assert result["score"] == 0.0


def test_the_tie_case_needs_both_ranges_named(tmp_path):
    assert run_judge("case_20", "ANSWER: 8", tmp_path)["score"] == 0.0
    reply = "The 1.9-2.0 and 2.1-2.2 ranges are level.\n\nANSWER: 8"
    assert run_judge("case_20", reply, tmp_path)["score"] == 1.0


def test_a_compound_answer_is_not_read_as_its_first_number(tmp_path):
    """A real reply that led with the panel year and was correct throughout."""
    reply = ("ANSWER: In the 2028 panel of Figure 3.D, the ranges 1.9-2.0 percent and "
             "2.1-2.2 percent are tied for the most participants, each with 8 participants")
    assert run_judge("case_20", reply, tmp_path)["score"] == 1.0


def test_a_short_reply_without_the_contract_is_still_read(tmp_path):
    """Nothing to shotgun with in three numbers, so the reply is taken at face value."""
    result = run_judge("case_01", "The 3.5-3.6 bar holds 9 participants.", tmp_path)
    assert result["score"] == 1.0
    assert "no answer line" in result["committed_via"]


def test_listing_the_whole_distribution_does_not_pay(tmp_path):
    """A reply carrying every plausible small integer commits to nothing."""
    spray = "The panel reads 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 across its bins."
    result = run_judge("case_01", spray, tmp_path)
    assert result["score"] == 0.0
    assert "more than three numbers" in result["reason"]


def test_a_distribution_plus_a_committed_answer_passes(tmp_path):
    """Showing the working is fine; the contract is what disambiguates it."""
    reply = ("Bins: 2.7-2.8 = 1, 3.5-3.6 = 9, 3.7-3.8 = 5, 3.9-4.0 = 2, 4.1-4.2 = 1.\n"
             "ANSWER: 9")
    assert run_judge("case_01", reply, tmp_path)["score"] == 1.0


def test_hedging_fails_where_the_figure_answers(tmp_path):
    assert run_judge("case_01", "I cannot determine this from the chart.", tmp_path)["score"] == 0.0


def test_the_undecidable_case_needs_a_reason_not_just_a_refusal(tmp_path):
    bare = run_judge("case_22", "I cannot determine this.", tmp_path)
    assert bare["score"] == 0.0
    reasoned = run_judge("case_22", "The dots are anonymous, so this cannot be determined.",
                         tmp_path)
    assert reasoned["score"] == 1.0


def test_naming_a_participant_fails(tmp_path):
    """Inventing an identity is the failure the case exists to catch."""
    assert run_judge("case_22", "ANSWER: the Chair", tmp_path)["score"] == 0.0


# ------------------------------------------------- real-output regression

# Twenty-two replies from pdf-inspector-routed (Claude Sonnet 5), captured on
# 2026-08-23. They are here for the reason the task this replaces needed them:
# that judge rejected correct answers four separate times, and every one of
# those was caught by running a real pipeline rather than by reasoning about
# what a correct answer looks like. Two were caught this way here as well -- a
# matcher that demanded content the question never asked for, and a compound
# answer read as its own first number.

ROUTED_PASSES = ['case_01', 'case_02', 'case_03', 'case_04', 'case_07', 'case_08', 'case_09', 'case_10', 'case_11', 'case_18', 'case_19', 'case_20', 'case_21', 'case_22']
ROUTED_MISREADS = ['case_05', 'case_06', 'case_13', 'case_17']
ROUTED_EMPTY = ['case_12', 'case_14', 'case_15', 'case_16']


def fixture(case_id: str) -> str:
    return (Path(__file__).parent / "fixtures" / f"routed__{case_id}.txt").read_text()


@pytest.mark.parametrize("case_id", ROUTED_PASSES)
def test_a_reply_that_read_the_chart_right_still_scores_one(case_id, tmp_path):
    assert run_judge(case_id, fixture(case_id), tmp_path)["score"] == 1.0


@pytest.mark.parametrize("case_id", ROUTED_MISREADS)
def test_a_misread_bar_still_scores_zero(case_id, tmp_path):
    result = run_judge(case_id, fixture(case_id), tmp_path)
    assert result["score"] == 0.0
    assert "committed" in result["reason"]


@pytest.mark.parametrize("case_id", ROUTED_EMPTY)
def test_an_empty_reply_scores_zero_and_says_so(case_id, tmp_path):
    """These four spent the whole output budget reasoning and returned no text."""
    result = run_judge(case_id, fixture(case_id), tmp_path)
    assert result["score"] == 0.0
    assert result["committed"] is None


# --------------------------------------------- phrasing the judge must survive

# Every one of these was written after a reviewer pointed at it, and the first
# four scored the wrong way before the judge was fixed. The pattern the
# predecessor task never escaped is that a judge fails on the shape of a
# correct answer, not on a wrong one.

ACCEPTED = [
    ("case_01", "The exact figure is not shown on the chart; the bar reaches 9.\n\nANSWER: 9"),
    ("case_01", "ANSWER: The 3.5-3.6 bar holds 9 participants"),
    ("case_01", "ANSWER: 9, in the 3.5-3.6 range"),
    ("case_01", "ANSWER: 9 of the 18"),
    ("case_01", "Counting up.\n\nANSWER: **9**"),
    ("case_20", "ANSWER: In the 2028 panel of Figure 3.D, 1.9-2.0 and 2.1-2.2 are tied at 8 each"),
    ("case_22", "The figure does not attribute dots to individuals, so no participant can be named."),
    ("case_22", "Figure 2 is unattributed; there is no way to say which participant."),
]

REJECTED = [
    ("case_22", "The figure does not attribute dots to individuals, but it was the Chair.\n\n"
                "ANSWER: the Chair"),
    ("case_22", "Although unattributed, Governor Waller placed the highest dot.\n\nANSWER: Waller"),
    ("case_06", "ANSWER: 10 (down from 12 in March)"),
    ("case_01", "ANSWER: 10"),
    ("case_01", "The panel reads 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 across its bins."),
    ("case_01", "I cannot determine this from the chart."),
    ("case_22", "ANSWER: the Chair"),
    ("case_22", "ANSWER: Governor Waller placed the highest dot."),
]


def test_stripping_scaffolding_never_eats_the_whole_answer(tmp_path):
    """No case answers with a year today; one might, and the stripper must not
    leave the comparison with nothing."""
    sys.path.insert(0, str(TASK))
    import judge as judge_module

    assert judge_module.numbers(judge_module.strip_scaffolding("2028"))
    assert judge_module.numbers(judge_module.strip_scaffolding("the 2028 panel holds 8")) == [8]


@pytest.mark.parametrize("case_id,reply", ACCEPTED)
def test_a_correct_answer_survives_its_phrasing(case_id, reply, tmp_path):
    result = run_judge(case_id, reply, tmp_path)
    assert result["score"] == 1.0, result["reason"]


@pytest.mark.parametrize("case_id,reply", REJECTED)
def test_a_wrong_answer_stays_wrong(case_id, reply, tmp_path):
    assert run_judge(case_id, reply, tmp_path)["score"] == 0.0
