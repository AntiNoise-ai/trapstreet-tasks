"""Tests for judge.py as wired to THIS task's gold.

The matchers are inherited from pdf_tables and covered by its suite. What is
tested here is the property this task is built on: that the gold answers for
image-only pages cannot be reached from the document's text layer.
"""
from __future__ import annotations

import json, os, re, subprocess, sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
TASK = HERE.parent
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


GOLD_ANSWERS = {
    "case_01": "+69 million dollars",
    "case_02": "-181,761 million dollars",
    "case_03": "-153,238 million dollars",
    "case_04": "970,442 million dollars",
    "case_05": "-179,225 million dollars",
    "case_06": "-77,579 million dollars",
    "case_07": "3,813,030 million dollars",
    "case_08": "+571,430 million dollars",
    "case_09": "323 million dollars",
    "case_10": "-582 million dollars",
    "case_11": "748,255 million dollars",
    "case_12": "289,170 million dollars",
    "case_13": "-40,560 million dollars",
    "case_14": "+154 million dollars",
    "case_15": "164,338 million dollars",
    "case_16": "694,042 million dollars",
    "case_17": "4,818 million dollars",
    "case_18": "1,488 million dollars",
    "case_19": "115,772 million dollars",
    "case_20": "1,719,915 million dollars"
}


@pytest.mark.parametrize("case_id", sorted(CASES))
def test_gold_answer_scores_one(case_id, tmp_path):
    m = run_judge(case_id, GOLD_ANSWERS[case_id], tmp_path)
    assert m["score"] == 1.0, f"{case_id} ({CASES[case_id]['label']}): {m}"


def test_every_case_has_a_gold_answer_fixture():
    assert set(GOLD_ANSWERS) == set(CASES)


def test_half_the_cases_are_image_only():
    """The task's whole design: a solution that never reaches an image-only
    page is capped at half marks, not merely penalised."""
    layers = [c["_layer"] for c in GOLD["cases"]]
    assert layers.count("scan") == 10 and layers.count("text") == 10


def test_image_only_answers_are_absent_from_the_text_layer():
    """The property that makes the cap real. If a scan-side figure also occurs
    on a digital page, a text-only solution could reach it by accident and the
    two halves stop being separable."""
    fitz = pytest.importorskip("fitz")
    flat = re.sub(r"[\s,]", "", "".join(p.get_text() for p in fitz.open(TASK / GOLD["document"])))
    for c in GOLD["cases"]:
        v = abs(c["matchers"][0]["value"])
        s = str(int(v)) if v == int(v) else str(v)
        if len(s) < 3:
            continue
        if c["_layer"] == "scan":
            assert s not in flat, f"{c['id']}: {s} is reachable from the text layer"
        else:
            assert s in flat, f"{c['id']}: {s} is missing from the text layer"


def test_pages_six_to_eleven_carry_no_text():
    fitz = pytest.importorskip("fitz")
    doc = fitz.open(TASK / GOLD["document"])
    for i, page in enumerate(doc, 1):
        n = len(page.get_text().strip())
        if i <= 5:
            assert n > 500, f"page {i} should be a digital text page, got {n} chars"
        else:
            assert n == 0, f"page {i} should be image-only, got {n} chars"


def test_hedging_fails(tmp_path):
    assert run_judge("case_11", "I cannot determine this from the document.", tmp_path)["score"] == 0.0


def test_sign_is_not_optional(tmp_path):
    """case_14 is the row where the sign flips: ten values negative, three
    positive. Answering with the row's prevailing sign must fail."""
    assert run_judge("case_14", "-154 million dollars", tmp_path)["score"] == 0.0


def test_wrong_column_fails(tmp_path):
    """case_04 is the cell pdfplumber got wrong during screening: it answered
    the Week-ended column instead of the Wednesday column."""
    assert run_judge("case_04", "910,776 million dollars", tmp_path)["score"] == 0.0


MALFORMED = ["", "not json at all {{{", "null", "[1, 2, 3]", '{"answer": NaN}',
             '{"answer": null}', "x" * 100_000]


@pytest.mark.parametrize("bad", MALFORMED)
def test_malformed_output_scores_zero_without_crashing(bad, tmp_path):
    assert run_judge("case_01", bad, tmp_path)["score"] == 0.0


# ------------------------------------------------- sign conventions
#
# The rendered page shows U+2212 MINUS SIGN, OCR engines emit en dashes, and
# financial tables conventionally parenthesise negatives. Half this task's
# answers are negative, so an unnormalised minus scored a correct answer zero.

@pytest.mark.parametrize("written", ["-179,225", "−179,225", "–179,225",
                                     "− 179,225", "(179,225)", "-179225",
                                     "-1.79225E+05"])
def test_every_way_of_writing_a_negative_is_accepted(written, tmp_path):
    assert run_judge("case_05", f"{written} million dollars", tmp_path)["score"] == 1.0


def test_dropping_the_minus_still_fails(tmp_path):
    assert run_judge("case_05", "179,225 million dollars", tmp_path)["score"] == 0.0


# ------------------------------------------------- anti-shotgun

WHOLE_ROW = ("-233,419 -5,380 -135,162 -3,664 -9,738 -40,560 154 -22,960 30 "
             "-319 -1,424 86 -14,482")
WHOLE_COL = ("748,255 171,275 2,768,498 1,719,915 970,442 9,425 68,716 "
             "-135,162 0 2,259 3,555,124")


def test_dumping_a_whole_row_fails(tmp_path):
    """Before the cap, this scored 1.0 — the answer is in there somewhere, so a
    solution that echoed the parser's text near the row label passed without
    having extracted anything."""
    assert run_judge("case_14", WHOLE_ROW, tmp_path)["score"] == 0.0


def test_dumping_a_whole_column_fails(tmp_path):
    assert run_judge("case_20", WHOLE_COL, tmp_path)["score"] == 0.0


@pytest.mark.parametrize("answer,case", [
    ("748,255 (see table 6, page 9)", "case_11"),
    ("Richmond is -40,560 but Atlanta is 154.", "case_14"),
    ("The value is 154, up from -319 last week.", "case_14"),
])
def test_citing_or_contrasting_does_not_trip_the_cap(answer, case, tmp_path):
    """The cap must not punish an answer for showing where it came from or what
    it is being compared against."""
    assert run_judge(case, answer, tmp_path)["score"] == 1.0


def test_thousands_separator_is_not_a_decimal_point(tmp_path):
    """748,255 is not 748.255. Treating every comma as a decimal point — which
    the inherited matcher did, because ../pdf_tables' document writes its
    conversion factor as '3,07' — failed sixteen of these twenty cases."""
    assert run_judge("case_11", "748,255", tmp_path)["score"] == 1.0
    assert run_judge("case_11", "748.255", tmp_path)["score"] == 0.0


REAL_CITED_ANSWER = '''**+69** (million dollars)

In the continued Table 1, the "Currency in circulation" row reads: 2,470,970 | \
**+ 69** | + 71,550 | 2,472,177 — so the change from the week ended Jul 22, \
2026 is **+69**.'''


# Verbatim from real solution runs. Every one leads with the figure and
# explains afterwards, which is the natural shape for a direct question and the
# shape two versions of the anti-shotgun rule rejected. Note R2: its closing
# prose says "a decrease of 77,579" — the sign is gone — so a rule that only
# inspects the end of the answer cannot score it, even though the answer opens
# with **-77,579**.
REAL_ANSWER_FIRST = {
    "case_01": '**+69** (million dollars)\n\nThis is the "Change from week ended '
               'Jul 22, 2026" figure for Currency in circulation, as shown in Table 1: '
               'Currency in circulation \u2014 2,470,970 (week ended Jul 29, 2026), '
               '**+69**, +71,550, 2,472,177 (Wednesday Jul 29, 2026).',
    "case_06": '**-77,579**\n\nThis is the "Change from week ended Jul 22, 2026" '
               'figure for "Reserve balances with Federal Reserve Banks" (2,984,570 for '
               'the week ended Jul 29, 2026, a decrease of 77,579 from the prior week).',
    "case_10": '**-582**\n\nIn the "Foreign official" row the figures are: 9,469 '
               '(week ended Jul 29, 2026) | **-582** | +31 | 9,452 (Wednesday Jul 29, '
               '2026).',
}


@pytest.mark.parametrize("case_id", sorted(REAL_ANSWER_FIRST))
def test_leading_with_the_figure_then_explaining_passes(case_id, tmp_path):
    assert run_judge(case_id, REAL_ANSWER_FIRST[case_id], tmp_path)["score"] == 1.0


def test_showing_the_row_you_read_it_from_is_not_a_shotgun(tmp_path):
    """Also verbatim from a real run: answer, then the row it came from, then
    the answer again. Nine figures once the two in the date are counted, which
    an anti-shotgun cap of 8 rejected."""
    assert run_judge("case_01", REAL_CITED_ANSWER, tmp_path)["score"] == 1.0
