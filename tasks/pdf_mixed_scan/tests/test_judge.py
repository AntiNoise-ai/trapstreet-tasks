"""Tests for judge.py as wired to THIS task's gold.

The fixtures are the point. This judge has rejected correct answers four
times, each in a shape that was not anticipated: a figure cap that counted the
numbers inside a date, a closing window that assumed the answer comes last, a
first-or-last window that broke on "preamble, answer, explanation". Reasoning
about what a correct answer looks like kept failing, so the suite is built on
sixty answers actually produced by three pipelines against this document.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
TASK = HERE.parent
FIXTURES = HERE / "fixtures"
GOLD = json.loads((TASK / "gold.cases.json").read_text())
CASES = {c["id"]: c for c in GOLD["cases"]}


def run_judge(case_id, agent_stdout, tmp_path, exit_code=0):
    (tmp_path / "stdout.txt").write_text(agent_stdout)
    (tmp_path / "meta.json").write_text(json.dumps({"exit_code": exit_code, "duration": 1.0}))
    manifest = {
        "inputs_dir": str(TASK / "inputs" / case_id),
        "expected_dir": str(TASK / "expected" / case_id),
        "outputs_dir": str(tmp_path),
        "run": {"stdout": str(tmp_path / "stdout.txt"),
                "stderr": str(tmp_path / "stdout.txt"),
                "meta": str(tmp_path / "meta.json")},
    }
    p = subprocess.run([sys.executable, "judge.py"], cwd=TASK, capture_output=True, text=True,
                       env={**os.environ, "TRAPTASK_MANIFEST": json.dumps(manifest)})
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


def fixture(tag, case_id):
    return (FIXTURES / f"{tag}__{case_id}.txt").read_text()


# ------------------------------------------------- real-output regression

@pytest.mark.parametrize("case_id", sorted(CASES))
def test_a_pipeline_that_reads_the_whole_document_answers_every_case(case_id, tmp_path):
    """MinerU reaches both halves and answered all twenty. Any future change to
    the judge that scores one of these zero is rejecting a correct answer."""
    assert run_judge(case_id, fixture("mineru", case_id), tmp_path)["score"] == 1.0


DOCLING_MISSES = {"case_13", "case_17"}


@pytest.mark.parametrize("case_id", sorted(CASES))
def test_second_ocr_pipeline_scores_as_measured(case_id, tmp_path):
    """docling reaches both halves too but drops the two hardest cross-table
    cases — it locates the pieces and stops short of the arithmetic. Pinning
    that keeps a later loosening of the judge from quietly turning misses into
    passes."""
    want = 0.0 if case_id in DOCLING_MISSES else 1.0
    assert run_judge(case_id, fixture("docling-ocr", case_id), tmp_path)["score"] == want


@pytest.mark.parametrize("case_id", sorted(c for c in CASES if CASES[c]["_layer"] != "text"))
def test_text_only_pipeline_cannot_reach_the_image_pages(case_id, tmp_path):
    assert run_judge(case_id, fixture("pdf-inspector", case_id), tmp_path)["score"] == 0.0


@pytest.mark.parametrize("case_id", sorted(c for c in CASES if CASES[c]["_layer"] != "text"))
def test_the_gold_figure_never_appears_in_a_text_only_answer(case_id):
    """The distinction that matters: those cases must be unanswerable, not
    merely mis-answered. Phrasing varies — some answers say the table is
    absent, some reason as far as they can and stop — so what is asserted is
    the thing that would signal a leak: the target figure turning up at all."""
    said = fixture("pdf-inspector", case_id)
    v = abs(CASES[case_id]["matchers"][0]["value"])
    for form in ({f"{v:,.0f}", f"{v:.0f}"} if v >= 1000 else {f"{v:.2f}", f"{v:.1f}"}):
        assert form not in said, f"{case_id}: {form} reachable from the text layer"


# ------------------------------------------------- structure

def test_the_split_is_what_the_gold_says_it_is():
    fitz = pytest.importorskip("fitz")
    doc = fitz.open(TASK / GOLD["document"])
    for i, page in enumerate(doc, 1):
        n = len(page.get_text().strip())
        assert (n > 500) if i <= 5 else (n == 0), f"page {i}: {n} chars"


def test_every_case_records_where_its_gold_came_from():
    for c in GOLD["cases"]:
        assert c["_layer"] in ("text", "scan", "both")
        assert isinstance(c.get("_pages"), list) and c["_pages"]


def test_cases_needing_both_halves_exist():
    layers = [c["_layer"] for c in GOLD["cases"]]
    assert layers.count("both") >= 5, "the cross-half cases are the discriminating ones"


def test_traptask_case_list_matches_gold():
    listed = re.findall(r"^- id:\s*(\S+)", (TASK / "traptask.yaml").read_text(), re.M)
    assert listed == [c["id"] for c in GOLD["cases"]]


# ------------------------------------------------- scoring rules

def test_a_ratio_may_be_written_either_way(tmp_path):
    """0.62% and 0.0062 are the same answer."""
    assert run_judge("case_13", "The share is 0.62%.", tmp_path)["score"] == 1.0
    assert run_judge("case_13", "The share is 0.0062.", tmp_path)["score"] == 1.0


def test_dumping_a_page_is_rejected(tmp_path):
    dump = " ".join(str(x) for x in range(100_000, 100_040))
    assert run_judge("case_08", dump, tmp_path)["score"] == 0.0


def test_hedging_fails(tmp_path):
    assert run_judge("case_08", "I cannot determine this from the document.", tmp_path)["score"] == 0.0


def test_the_wrong_direction_of_a_ratio_fails(tmp_path):
    """case_18 asks for larger over smaller; inverting gives 0.363."""
    assert run_judge("case_18", "The ratio is 0.363.", tmp_path)["score"] == 0.0


MALFORMED = ["", "not json at all {{{", "null", "[1, 2, 3]", '{"answer": NaN}',
             '{"answer": null}', "x" * 100_000]


@pytest.mark.parametrize("bad", MALFORMED)
def test_malformed_output_scores_zero_without_crashing(bad, tmp_path):
    assert run_judge("case_01", bad, tmp_path)["score"] == 0.0


def test_a_worked_answer_is_not_a_shotgun(tmp_path):
    """Verbatim from a real run, and the fifth time an anti-shotgun rule
    rejected a correct answer. It sets its arithmetic out as numbered steps —
    twenty-nine figures, every one load-bearing:

        Step 1: 2,917,756 - (-310,644) = 3,228,400
        Step 2: 2,638,757 - (-250,396) = 2,889,153
        Step 3: 2,889,153 / 3,228,400 = 89.49%

    Questions that ask for a derived figure invite exactly this, so the cap
    has to sit well above a worked answer rather than near it."""
    worked = (FIXTURES / "worked__case_01.txt").read_text()
    assert run_judge("case_01", worked, tmp_path)["score"] == 1.0


# ------------------------------------------------- phrasing robustness
#
# Five separate rules in this judge have rejected correct answers, each in a
# shape that was not predicted: a figure cap tripped by the numbers inside a
# date, three different positional windows, and keyword patterns written too
# literally ("face value" rejecting "at face"). The fixtures pin what real
# pipelines produced; these pin the shapes they might produce next.

def _phrasings(case):
    """Ways the same correct answer legitimately gets written."""
    v = case["matchers"][0]["value"]
    words = {"treasury|tga|general account": "the U.S. Treasury, General Account",
             "atlanta": "Atlanta", "chicago": "Chicago", "new\\s*york": "New York",
             "richmond": "Richmond", "\\bface\\b": "face value", "\\bcash\\b": "cash value"}
    named = ", ".join(words.get(m["pattern"], m["pattern"])
                      for m in case["matchers"] if m["kind"] == "regex_required")
    tag = (named + ", ") if named else ""
    n = f"{v:,.2f}".rstrip("0").rstrip(".") if abs(v) < 1000 else f"{v:,.0f}"
    out = [
        f"{tag}{n}",
        f"**{tag}{n}**\n\nThat figure comes straight from the table.",
        f"Working through it ({tag}the two inputs are 1,234,567 and 89,012), "
        f"dividing gives {n}.",
        f"On Wednesday, Jul 29, 2026 the answer is {tag}{n} — see table 6, page 9.",
        "## Calculation\n"
        + "\n".join(f"Step {i}: {1000*i:,} - {7*i} = {1000*i - 7*i:,}" for i in range(1, 7))
        + f"\n\n**Result: {tag}{n}**",
    ]
    if case["matchers"][0].get("accept_percent_forms"):
        out.append(f"{tag}{v / 100:.6g} as a fraction")
    return out


@pytest.mark.parametrize("case_id", sorted(CASES))
def test_every_natural_phrasing_of_the_right_answer_passes(case_id, tmp_path):
    for i, answer in enumerate(_phrasings(CASES[case_id])):
        score = run_judge(case_id, answer, tmp_path)["score"]
        assert score == 1.0, f"{case_id} phrasing {i}: {answer[:90]!r}"


NON_VERBATIM = [
    ("case_20", "The gap is 51,203. Table 1 carries these at cash value while table 7 "
                "states them at face.", 1.0),
    ("case_20", "51,203 — one is a cash measure, the other a face measure.", 1.0),
    ("case_20", "The difference is 51,203 million dollars.", 0.0),
    ("case_02", "The largest weekly move was in the Treasury's General Account, up 81,153.", 1.0),
    ("case_09", "New York holds 2,768,498 of 4,158,647 — about 66.6%.", 1.0),
    ("case_15", "It sits almost entirely with the New York Fed: 970,442.", 1.0),
]


@pytest.mark.parametrize("case_id,answer,want", NON_VERBATIM)
def test_keyword_requirements_are_not_literal(case_id, answer, want, tmp_path):
    """'face value' as a required phrase rejected 'at face' and 'a face
    measure', both of which are how the answer actually gets written. Naming
    the reason is still required — the bare figure fails."""
    assert run_judge(case_id, answer, tmp_path)["score"] == want
