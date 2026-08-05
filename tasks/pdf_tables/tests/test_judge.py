"""Tests for judge.py as wired to THIS task's gold.

The inherited matchers are already covered by pdf_reader_v2's suite and are
not re-tested here. What is tested is (a) that every gold answer still
satisfies its own matchers, and (b) the two matchers added for this task —
`sci_value` and `regex_forbidden` — against the failure modes that motivated
them.
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
    "case_01": "Hazardous waste at A1 is 2.81E+01 kg.",
    "case_02": "The A1 figure for ADP-fossil resources is 4.66E+03 MJ.",
    "case_03": "Renew. PER as material at A3 is 2.34E+02 MJ.",
    "case_04": "GWP - biogenic at A3 is -2.70E+01 kg CO2e.",
    "case_05": "Non-hazardous waste at A5 is 2.60E+01 kg.",
    "case_06": "EP-marine at A4 is 3.60E-03 kg Ne.",
    "case_07": "Eutrophication at A3 under CML is 1.45E-01 kg PO4^3e.",
    "case_08": "Ionizing radiation over A1-A3 is 2.14E+01 kBq U235e.",
    "case_09": "Only column B6 is populated; Acidification potential there is 2.32E-08 mol H+e.",
    "case_10": "ADP-fossil resources under module D is -3.57E+02 MJ.",
    "case_11": "Radioactive waste at C3 is 4.97E-06 kg.",
    "case_12": "Human toxicity, cancer at B6 is 2.21E-15 CTUh.",
    "case_13": "POCP at C2 under CML is 1.44E-04 kg C2H4e.",
    "case_14": "Under CML, Global Warming Pot. over A1-A3 is 3.19E+02 kg CO2e.",
    "case_15": "Under CML, Global Warming Pot. at module D is -2.45E+01 kg CO2e.",
    "case_16": "Under CML, ADP-fossil at A1 is 4.29E+03 MJ.",
    "case_17": "Non-re. PER as energy at C3 is -3.86E+02 MJ.",
    "case_18": "Exported energy - Electricity at A5 is 7.78E+00 MJ and Exported energy - Heat at A5 is 1.07E+01 MJ; together 1.85E+01 MJ.",
    "case_19": "GWP - biogenic is the only negative A1-A3 total, at -2.64E+01 kg CO2e.",
    "case_20": "EP-freshwater A1-A3 is 2.28E-01 kg Pe; multiplying by 3.07 gives 7.00E-01 kg PO4e.",
}

@pytest.mark.parametrize("case_id", sorted(CASES))
def test_gold_answer_scores_one(case_id, tmp_path):
    m = run_judge(case_id, GOLD_ANSWERS[case_id], tmp_path)
    assert m["score"] == 1.0, f"{case_id} ({CASES[case_id]['label']}): {m}"


def test_every_case_has_a_gold_answer_fixture():
    assert set(GOLD_ANSWERS) == set(CASES)


# ------------------------------------------------- sci_value

def test_scientific_notation_is_not_shredded(tmp_path):
    """The bug this matcher exists for: the inherited NUMBER_RE splits
    '2.25E+01' into [2.25, 1], so `numeric` can never see the value 22.5 and
    every cell-lookup case would be unscoreable."""
    m = run_judge("case_01", "2.81E+01", tmp_path)
    assert m["score"] == 1.0, m


def test_expanded_decimal_is_accepted(tmp_path):
    """22.5 and 2.25E+01 are the same number; a model that expands the
    notation has not got the answer wrong."""
    m = run_judge("case_01", "The value is 28.1 kg.", tmp_path)
    assert m["score"] == 1.0, m


def test_unit_digits_are_not_read_as_the_answer(tmp_path):
    """'kg CO2e' and 'kBq U235e' carry digits. Preferring E-notation tokens
    keeps 2 and 235 from being treated as candidate answers."""
    m = run_judge("case_08", "kg CO2e, CFC-11e, U235e — the figure is 2.14E+01.", tmp_path)
    assert m["score"] == 1.0, m


def test_wrong_exponent_fails(tmp_path):
    """Right mantissa, wrong magnitude. This is what silent parser corruption
    looks like, and a magnitude-insensitive check would pass it."""
    m = run_judge("case_12", "2.21E-05 CTUh", tmp_path)
    assert m["score"] == 0.0, m


def test_last_scientific_value_is_the_committed_one(tmp_path):
    """A model may walk the row before settling. The figure it ends on is its
    answer — the same anti-decoy rule the tenancy task's currency matcher uses."""
    ok = run_judge("case_17", "The renewable row reads 5.36E-01, but the "
                              "non-renewable row at C3 is -3.86E+02 MJ.", tmp_path)
    assert ok["score"] == 1.0, ok


def test_committing_to_the_adjacent_table_fails(tmp_path):
    """The real error case_05 exists to catch: reading 'Renew. PER as energy'
    instead of 'Non-re. PER as energy' from the twin table on the same page."""
    m = run_judge("case_17", "At stage C3 the value is 5.36E-01 MJ.", tmp_path)
    assert m["score"] == 0.0, m


def test_sign_is_not_optional(tmp_path):
    m = run_judge("case_04", "The A3 figure is 2.70E+01 kg CO2e.", tmp_path)
    assert m["score"] == 0.0, m


def test_comma_decimal_separator_is_parsed(tmp_path):
    """The EPD writes its own conversion factor as '3,07'. A model echoing
    European decimal style must not be marked wrong for it."""
    m = run_judge("case_20", "2,28E-01 x 3,07 = 7,00E-01 kg PO4e", tmp_path)
    assert m["score"] == 1.0, m


def test_footnote_factor_misread_as_307_fails(tmp_path):
    """Reading '3,07' as 307 instead of 3.07 lands two orders of magnitude out."""
    m = run_judge("case_20", "2.28E-01 x 307 = 7.00E+01 kg PO4e", tmp_path)
    assert m["score"] == 0.0, m


# ------------------------------------------------- regex_forbidden

def test_shotgunning_every_b_column_fails(tmp_path):
    """Naming the whole range satisfies the required pattern on B6, so the
    value is what has to carry the weight."""
    m = run_judge("case_09", "B1, B2, B3, B4, B5, B6 and B7 all carry values.", tmp_path)
    assert m["score"] == 0.0, m


def test_excluding_the_other_b_columns_by_name_still_passes(tmp_path):
    """The regression this pair of cases was rewritten for. pdf-inspector
    answered case_08 completely correctly — 'only B6 carries values; B1, B2,
    B3, B4, B5 and B7 are ND' — and scored 0, because a forbidden pattern over
    the other columns cannot tell naming-to-exclude from naming-to-claim."""
    m = run_judge("case_09", "Only B6 carries numeric values across the use stage. "
                             "B1, B2, B3, B4, B5 and B7 are all marked ND. Acidification "
                             "potential there is 2.32E-08 mol H+e.", tmp_path)
    assert m["score"] == 1.0, m


def test_listing_every_gwp_variant_fails(tmp_path):
    m = run_judge("case_19", "GWP - total, GWP - fossil, GWP - biogenic and "
                             "GWP - LULUC are all negative over A1-A3.", tmp_path)
    assert m["score"] == 0.0, m


def test_ruling_out_the_other_gwp_variants_by_name_still_passes(tmp_path):
    m = run_judge("case_19", "Unlike GWP - fossil and GWP - LULUC, which are positive, "
                             "GWP - biogenic is negative over A1-A3 at -2.64E+01.", tmp_path)
    assert m["score"] == 1.0, m


def test_answering_from_the_other_standards_table_fails(tmp_path):
    """The point of the cross_table stratum. EF 3.1 (page 11) puts GWP - total
    at module D at -2.47E+01; CML (page 13) puts it at -2.45E+01. 0.8% apart —
    close enough that any forgiving tolerance would let the wrong table pass,
    which is why this case tightens rel_tolerance to 0.002."""
    m = run_judge("case_15", "Global Warming Pot. at module D is -2.47E+01 kg CO2e.", tmp_path)
    assert m["score"] == 0.0, m


def test_adjacent_column_drift_fails(tmp_path):
    """case_06's neighbour is 4% away. A one-column drift must not pass."""
    m = run_judge("case_06", "EP-marine at A4 is 3.44E-03 kg Ne.", tmp_path)
    assert m["score"] == 0.0, m


def test_committing_to_the_twin_row_fails(tmp_path):
    m = run_judge("case_17", "At stage C3 the value is 5.36E-01 MJ.", tmp_path)
    assert m["score"] == 0.0, m


# ------------------------------------------------- general

def test_hedging_fails(tmp_path):
    m = run_judge("case_10", "I cannot determine this from the document.", tmp_path)
    assert m["score"] == 0.0


def test_nonzero_exit_fails(tmp_path):
    m = run_judge("case_01", "2.81E+01", tmp_path, exit_code=1)
    assert m["score"] == 0.0


MALFORMED = {
    "empty": "",
    "garbage": "not json at all {{{",
    "json_null": "null",
    "json_array": "[1, 2, 3]",
    "answer_is_nan": '{"answer": NaN}',
    "answer_is_infinity": '{"answer": Infinity}',
    "answer_is_list": '{"answer": [1,2,3]}',
    "answer_is_null": '{"answer": null}',
    "deeply_nested": '{"a":' * 200 + "1" + "}" * 200,
    "very_long": "x" * 200_000,
}


@pytest.mark.parametrize("name", sorted(MALFORMED))
def test_malformed_output_scores_zero_without_crashing(name, tmp_path):
    m = run_judge("case_01", MALFORMED[name], tmp_path)
    assert m["score"] == 0.0
