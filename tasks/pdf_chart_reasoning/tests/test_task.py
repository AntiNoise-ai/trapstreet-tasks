"""Tests for pdf_chart_reasoning.

Three things need protecting: the measurements, which are made rather than
typed; the capability budget, which is what this task exists to fix; and the
judge, which in the predecessor rejected correct answers nine times and never
once let a wrong one through.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

TASK = Path(__file__).parent.parent
GOLD = json.loads((TASK / "gold.cases.json").read_text())
CASES = {c["id"]: c for c in GOLD["cases"]}
GEOM = json.loads((TASK / "gold_geometry.json").read_text())
SERIES = json.loads((TASK / "series_gold.json").read_text())
STATED_TOTALS = {"2026": 18, "2027": 18, "2028": 17, "longer run": 18}


def run_judge(case_id: str, reply: str, tmp_path: Path) -> dict:
    (tmp_path / "stdout.txt").write_text(reply)
    manifest = {"inputs_dir": str(TASK / "inputs" / case_id),
                "expected_dir": str(TASK / "expected" / case_id),
                "outputs_dir": str(tmp_path),
                "run": {"stdout": str(tmp_path / "stdout.txt")}}
    p = subprocess.run([sys.executable, "judge.py"], cwd=TASK, capture_output=True, text=True,
                       env={**os.environ, "TRAPTASK_MANIFEST": json.dumps(manifest)})
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


# ------------------------------------------------------------- measurements

def test_the_bar_and_dot_measurement_reproduces(tmp_path):
    out = tmp_path / "g.json"
    subprocess.run([sys.executable, "extract_gold.py", "sep_original.pdf", str(out)],
                   cwd=TASK, check=True, capture_output=True)
    assert json.loads(out.read_text()) == GEOM


def test_the_series_measurement_reproduces(tmp_path):
    out = tmp_path / "s.json"
    subprocess.run([sys.executable, "extract_series.py", "sep_original.pdf", str(out)],
                   cwd=TASK, check=True, capture_output=True)
    assert json.loads(out.read_text()) == SERIES


@pytest.mark.parametrize("figure", sorted(GEOM))
def test_every_panel_sums_to_the_stated_participant_count(figure):
    for panel, bins in GEOM[figure].items():
        assert sum(bins.values()) == STATED_TOTALS[panel], f"{figure} {panel}"


def test_the_dot_plot_and_the_histogram_agree():
    """Figures 2 and 3.E encode the same judgments in two chart types."""
    for panel, bins in GEOM["figure_3.E"].items():
        for label, expected in bins.items():
            lo, hi = (float(x) for x in label.split("-"))
            got = sum(c for level, c in GEOM["figure_2"][panel].items()
                      if lo - 0.006 <= float(level) <= hi + 0.004)
            assert got == expected, f"{panel} {label}"


@pytest.mark.parametrize("figure", sorted(SERIES))
def test_each_series_is_quarterly_and_skips_the_meeting_the_note_omits(figure):
    for name, pts in SERIES[figure].items():
        # "~" marks a month counted back rather than read, so it sorts after
        # the digits and has to come off before the ordering is checked.
        dates = [d.lstrip("~") for d, _ in pts]
        assert len(pts) == 75, f"{figure} {name}"
        assert "2020-03" not in dates, "the note says March 2020 is excluded"
        assert dates == sorted(dates)
        assert {d.lstrip("~")[5:] for d in dates} <= {"03", "06", "09", "12"}


@pytest.mark.parametrize("figure", sorted(SERIES))
def test_no_case_is_authored_against_an_inferred_month(figure):
    """Months before the SEP's settled quarterly calendar are counted back from
    the anchor rather than read, and carry a "~". The fourth SEP was published
    with the January 2009 minutes, so those months are not March/June/September/
    December and this file does not pretend otherwise."""
    inferred = {d for name in SERIES[figure] for d, _ in SERIES[figure][name]
                if d.startswith("~")}
    for c in GOLD["cases"]:
        for d in inferred:
            assert d.lstrip("~") not in c["question"], f"{c['id']} uses {d}"


@pytest.mark.parametrize("figure", sorted(SERIES))
def test_series_values_are_multiples_of_one_over_the_participant_count(figure):
    """The index is (higher - lower) / participants, so it moves in 1/N steps."""
    for name, pts in SERIES[figure].items():
        best = min(range(15, 21),
                   key=lambda N: sorted(abs(v * N - round(v * N)) for _, v in pts)[len(pts)//2])
        dev = sorted(abs(v * best - round(v * best)) for _, v in pts)[len(pts) // 2]
        assert dev < 0.25, f"{figure} {name}: median deviation {dev:.3f} at N={best}"


def test_questions_are_authored_from_the_measurements(tmp_path):
    out = tmp_path / "c.json"
    subprocess.run([sys.executable, "author_cases.py", str(out)],
                   cwd=TASK, check=True, capture_output=True)
    assert json.loads(out.read_text()) == GOLD


# ------------------------------------------------------- the capability budget

def test_no_capability_takes_more_than_a_third_of_the_set():
    """The predecessor spent 59% of its cases on one capability and spanned four
    independent directions with twenty-two items."""
    counts = Counter(c["capability"] for c in GOLD["cases"])
    n = len(GOLD["cases"])
    worst, k = counts.most_common(1)[0]
    assert k / n <= 1 / 3, f"{worst} holds {k} of {n} cases"


def test_every_capability_has_at_least_three_cases():
    """One case cannot separate 'cannot do this' from 'unlucky once'."""
    for cap, k in Counter(c["capability"] for c in GOLD["cases"]).items():
        assert k >= 3, f"{cap} has only {k}"


def test_continuous_answers_carry_a_tolerance_and_counts_do_not():
    for c in GOLD["cases"]:
        for m in c["matchers"]:
            if m["kind"] != "committed_value":
                continue
            fractional = float(m["value"]) != int(float(m["value"]))
            assert (m.get("tolerance", 0) > 0) == fractional, c["id"]


# ------------------------------------------------------------------ the judge

@pytest.mark.parametrize("case_id", sorted(CASES))
def test_the_gold_answer_passes_its_own_judge(case_id, tmp_path):
    c = CASES[case_id]
    a = c["answer"]
    if a.startswith("Not derivable"):
        reply = f"ANSWER: {a}; the release says so -- not collected, and the dots carry no names"
    elif a.startswith("No --"):
        reply = "ANSWER: No -- it comes from historical forecast errors of outside forecasters"
    else:
        reply = f"Working shown above.\n\nANSWER: {a}"
    assert run_judge(case_id, reply, tmp_path)["score"] == 1.0


def test_a_reading_case_is_not_answerable_from_the_text_layer():
    """The reading capabilities must need the figures. The semantic and
    abstention ones deliberately need the footnotes, so they are exempt."""
    import pymupdf

    doc = pymupdf.open(TASK / "sep_charts.pdf")
    text = " ".join(p.get_text() for p in doc)
    reading = {"read_length", "read_position", "count_marks", "derived_value"}
    for c in GOLD["cases"]:
        if c["capability"] in reading and c["answer"].lstrip("-").replace(".", "").isdigit():
            assert f" {c['answer']} " not in text, f"{c['id']} answers with a printed figure"
    for i in range(3, 16):
        assert not doc[i - 1].get_text().strip(), "figure pages must carry no text"


ACCEPTED_15 = [
    "ANSWER: No -- it is based on historical forecast errors of outside forecasters",
    "ANSWER: It does not. The band comes from the root mean squared error of past forecasts",
    "ANSWER: The interval reflects historical projection errors, not the participants' spread",
]
REJECTED_15 = [
    "ANSWER: Yes, it shows how widely the participants' projections are spread",
    "ANSWER: Yes -- it is the spread of the eighteen projections",
]


@pytest.mark.parametrize("reply", ACCEPTED_15)
def test_the_band_question_survives_its_phrasing(reply, tmp_path):
    """Keying on the bare word "no" rejected two correct replies: a reader who
    writes "it does not" has answered the question."""
    assert run_judge("case_15", reply, tmp_path)["score"] == 1.0


@pytest.mark.parametrize("reply", REJECTED_15)
def test_the_band_question_still_rejects_the_wrong_answer(reply, tmp_path):
    assert run_judge("case_15", reply, tmp_path)["score"] == 0.0


def test_the_tolerance_admits_one_legal_value_only(tmp_path):
    """0.025 is under half of a 1/18 step, so the next legal value fails."""
    c = CASES["case_04"]
    gold = float(c["answer"])
    assert run_judge("case_04", f"ANSWER: {gold + 0.02:.3f}", tmp_path)["score"] == 1.0
    assert run_judge("case_04", f"ANSWER: {gold + 1/18:.3f}", tmp_path)["score"] == 0.0


def test_a_reply_without_the_contract_scores_zero(tmp_path):
    r = run_judge("case_01", "The bar reaches 13 participants.", tmp_path)
    assert r["score"] == 0.0 and r["committed_via"] == "no ANSWER line"


def test_naming_a_participant_fails(tmp_path):
    assert run_judge("case_19", "ANSWER: the Chair", tmp_path)["score"] == 0.0


def test_the_reverse_abstention_case_punishes_refusing(tmp_path):
    """case_20 looks unanswerable and is stated in a footnote."""
    assert run_judge("case_20", "ANSWER: cannot be determined from the document",
                     tmp_path)["score"] == 0.0
    assert run_judge("case_20", "ANSWER: 17", tmp_path)["score"] == 1.0
