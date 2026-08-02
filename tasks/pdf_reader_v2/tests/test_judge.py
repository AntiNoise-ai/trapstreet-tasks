"""Tests for judge.py as wired to THIS task's gold.

judge.py is inherited verbatim from tasks/pdf_reader and is not modified
here, so these tests deliberately do not re-test its matcher primitives.
What they do test is the thing a fork can silently break: that each case's
`answer` still satisfies its own `matchers` after the question rewrites, and
that a plausible wrong answer still fails.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
TASK = HERE.parent
GOLD = json.loads((TASK / "gold.cases.json").read_text())
CASES = {c["id"]: c for c in GOLD["cases"]}


def run_judge(case_id: str, agent_stdout: str, tmp_path: Path, exit_code: int = 0) -> dict:
    stdout_f = tmp_path / "stdout.txt"
    stdout_f.write_text(agent_stdout)
    meta_f = tmp_path / "meta.json"
    meta_f.write_text(json.dumps({"exit_code": exit_code, "duration": 1.0}))

    manifest = {
        "inputs_dir": str(TASK / "inputs" / case_id),
        "expected_dir": str(TASK / "expected" / case_id),
        "outputs_dir": str(tmp_path),
        "run": {"stdout": str(stdout_f), "stderr": str(stdout_f), "meta": str(meta_f)},
    }
    proc = subprocess.run(
        [sys.executable, "judge.py"],
        cwd=TASK, capture_output=True, text=True,
        env={**os.environ, "TRAPTASK_MANIFEST": json.dumps(manifest)},
    )
    assert proc.returncode == 0, f"judge crashed: {proc.stderr}"
    return json.loads(proc.stdout)


# ------------------------------------------------- gold self-consistency

GOLD_ANSWERS = {
    "case_01": "£2,100.00 per calendar month.",
    "case_02": "£2,400.00 per calendar month.",
    "case_03": "£2,250.00",
    "case_04": "05/09/2022",
    "case_05": "Rent is due on or prior to the 5th of the month.",
    "case_06": "No.",
    "case_07": "Yes.",
    "case_08": "Yes.",
    "case_09": "The tenancy automatically extends for a further six months.",
    "case_10": "The automatic extension period only, not the original fixed term.",
    "case_11": "The Tenancy Deposit Scheme (TDS).",
    "case_12": "Only with the prior written consent of the Landlord.",
    "case_13": "12x1950 + 12x2100 + 12x2400 = 77400. Total £77,400.",
    "case_14": "3% per annum above the Bank of England base rate.",
    "case_15": "Housing Act 1988, Section 19A.",
    "case_16": "Yes.",
    "case_17": "It may be referred to the Independent Case Examiner (ICE) for adjudication.",
    "case_18": "Void £2100 + fee £4078.80 + inventory £56.00 + admin £186.67 = £6421.47",
    "case_19": "No. Section 6 gives the outgoing tenant no refund or credit where the "
               "replacement pays more; the tenant only bears any shortfall.",
    "case_20": (
        "Section 6 lists five categories. First, rent payable under the agreement "
        "until the new tenancy has started. Second, any difference in rental payments "
        "where the replacement tenant pays a lower amount. Third, the Landlord's new "
        "letting fee for the remainder of the term. Fourth, a share of the inventory "
        "clerk's cost of checking the new tenants in. Fifth, a share of the Landlord's "
        "cost of administering the new tenancy. The fourth and fifth are scaled by the "
        "number of months surrendered early as a percentage of the current fixed term."
    ),
}


@pytest.mark.parametrize("case_id", sorted(CASES))
def test_gold_answer_scores_one(case_id, tmp_path):
    """Every case's own gold answer must score 1.0 against its own matchers.

    This is what catches a question rewrite that drifted away from its gold,
    or a matcher tightened without updating the expected answer.
    """
    m = run_judge(case_id, GOLD_ANSWERS[case_id], tmp_path)
    assert m["score"] == 1.0, f"{case_id} ({CASES[case_id]['label']}): {m}"


def test_every_case_has_a_gold_answer_fixture():
    assert set(GOLD_ANSWERS) == set(CASES)


# ------------------------------------------------- negative cases

def test_hedging_fails(tmp_path):
    m = run_judge("case_14", "I cannot determine this from the document.", tmp_path)
    assert m["score"] == 0.0


def test_empty_output_fails(tmp_path):
    m = run_judge("case_03", "", tmp_path)
    assert m["score"] == 0.0


def test_nonzero_exit_fails(tmp_path):
    m = run_judge("case_03", "£2,250.00", tmp_path, exit_code=1)
    assert m["score"] == 0.0


def test_wrong_number_fails(tmp_path):
    m = run_judge("case_01", "£1,950.00 per calendar month.", tmp_path)
    assert m["score"] == 0.0


def test_case_15_requires_the_section_not_just_the_act(tmp_path):
    """The v1 answer ('Housing Act 1988') is textbook knowledge for any AST.
    v2 anchors the case to clause 1.13's section number so it can't be
    answered closed-book."""
    m = run_judge("case_15", "Housing Act 1988.", tmp_path)
    assert m["score"] == 0.0


def test_case_10_rejects_bare_echo_of_the_question(tmp_path):
    """The v1 failure this case exists to fix: repeating the question's own
    option list scored 1.0."""
    m = run_judge("case_10", "The automatic extension period.", tmp_path)
    assert m["score"] == 0.0


def test_case_18_partial_calculation_fails(tmp_path):
    """Omitting a component lands on a different total, which must not pass."""
    m = run_judge("case_18", "£2100 + £4078.80 = £6178.80", tmp_path)
    assert m["score"] == 0.0


def test_case_19_bare_yes_no_fails_min_words(tmp_path):
    m = run_judge("case_19", "No.", tmp_path)
    assert m["score"] == 0.0


def test_case_20_generic_list_without_the_scaling_basis_fails(tmp_path):
    """The anti-shotgun guard. A model can list plausible early-surrender
    charges from general UK tenancy knowledge and hit the five category
    matchers. The scaling basis is document-specific, so it is what
    distinguishes having read Section 6 from having guessed."""
    m = run_judge("case_20", (
        "The Landlord may charge: rent until the new tenancy has started; any "
        "shortfall where the replacement pays a lower amount; the new letting fee; "
        "the inventory check-in cost; and the administration cost of setting up the "
        "new tenancy. These are all recoverable from the outgoing tenant."
    ), tmp_path)
    assert m["score"] == 0.0


def test_case_20_missing_a_category_fails(tmp_path):
    """Four of five is not a pass — every category matcher must hit."""
    m = run_judge("case_20", (
        "Rent until the new tenancy has started, the new letting fee, the inventory "
        "check-in cost, and the administration cost, the last two scaled by the number "
        "of months surrendered early as a percentage of the current fixed term."
    ), tmp_path)
    assert m["score"] == 0.0


# ------------------------------------------------- currency_amount regression

# Verbatim shapes recorded from four real solutions on 2026-08-02. Under the
# original `leading_numeric` matcher the first three scored 0 while holding the
# correct answer, because the first number in the string is a clause number or a
# date. That single matcher choice moved mineru above pdf-inspector by exactly
# one point on word order alone.
CITATION_FIRST = {
    "case_01": (
        "Based on clause 1.9b, the rent for the period 05/09/2023 to 04/09/2024 "
        "is £2,100.00 per calendar month. This corresponds to months 13-24."
    ),
    "case_02": (
        "Based on clause 1.9b, the rent for the period 05/09/2024 to 04/09/2025 "
        "(which covers months 25-36 of the 36-month tenancy) is £2,400.00 per "
        "calendar month."
    ),
    "case_03": (
        "Based on clauses 1.10 and the Prescribed Information section, the "
        "deposit amount is £2,250.00."
    ),
}


@pytest.mark.parametrize("case_id", sorted(CITATION_FIRST))
def test_citing_the_source_first_still_passes(case_id, tmp_path):
    """Answering correctly while citing the clause it came from must score 1.0.
    Leading with 'clause 1.9b' or a date is good legal-review practice, not a
    wrong answer."""
    m = run_judge(case_id, CITATION_FIRST[case_id], tmp_path)
    assert m["score"] == 1.0, m


def test_walking_the_schedule_then_committing_passes(tmp_path):
    """A model may quote the whole rent schedule while reasoning; the figure it
    ends on is the one it is answering with."""
    m = run_judge("case_02",
                  "The schedule is £1,950.00, then £2,100.00, then £2,400.00. "
                  "For months 25-36 the rent is £2,400.00.", tmp_path)
    assert m["score"] == 1.0, m


def test_committing_to_the_wrong_amount_still_fails(tmp_path):
    """The anti-decoy property survives: naming the right figure in passing but
    committing to another one is still wrong. This is the real error one
    solution made on case_02."""
    m = run_judge("case_02",
                  "Rents run £1,950.00 and £2,400.00 across the term. For the "
                  "period 05/09/2024 to 04/09/2025 the rent is £2100.00.", tmp_path)
    assert m["score"] == 0.0, m


def test_answer_with_no_currency_formatting_fails(tmp_path):
    """The question asks for a GBP figure; a bare number is not a committed
    amount, and accepting one would re-admit clause numbers and month counts."""
    m = run_judge("case_03", "The deposit is 2250.", tmp_path)
    assert m["score"] == 0.0, m


def test_gbp_prefix_is_accepted_as_currency(tmp_path):
    m = run_judge("case_03", "Per clause 1.10 the deposit is GBP 2,250.00.", tmp_path)
    assert m["score"] == 1.0, m


# ------------------------------------------------- malformed-output robustness

# A judge that crashes on garbage reads as "task infrastructure is broken"
# rather than "solution produced garbage" — the wrong signal entirely. Note
# json.loads accepts NaN/Infinity by default, and int(float("nan")) raises.
MALFORMED = {
    "empty": "",
    "garbage": "not json at all {{{",
    "json_null": "null",
    "json_array": "[1, 2, 3]",
    "obj_missing_keys": '{"unexpected_key": true}',
    "answer_is_nan": '{"answer": NaN}',
    "answer_is_infinity": '{"answer": Infinity}',
    "deeply_nested": '{"a":' * 200 + "1" + "}" * 200,
    "answer_is_list": '{"answer": [1,2,3]}',
    "answer_is_null": '{"answer": null}',
    "very_long": "x" * 200_000,
}


@pytest.mark.parametrize("name", sorted(MALFORMED))
def test_malformed_output_scores_zero_without_crashing(name, tmp_path):
    m = run_judge("case_03", MALFORMED[name], tmp_path)
    assert m["score"] == 0.0
