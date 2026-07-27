# tests/test_judge.py
import json
import sys
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import judge  # noqa: E402

CASE_IDS = ["case_01", "case_02", "case_03", "case_04", "case_05", "case_06"]


def _expected(cid):
    return json.loads((ROOT / "expected" / cid / "answer.json").read_text())


def _inputs_dir(cid):
    return ROOT / "inputs" / cid


@pytest.mark.parametrize("cid", CASE_IDS)
def test_gold_edits_score_perfect(cid):
    """Applying the gold edits verbatim must score 1.0 -- proves the gold
    edits are internally consistent and all four scripts run cleanly."""
    expected = _expected(cid)
    r = judge.score_case(json.dumps(expected["gold_edits"]), expected, _inputs_dir(cid))
    assert r["score"] == 1.0, r.get("reason")


@pytest.mark.parametrize("cid", CASE_IDS)
def test_noop_fails(cid):
    """An agent that makes no edits at all must NOT score 1.0 -- proves
    each case's ticket describes a real bug, not a no-op."""
    expected = _expected(cid)
    r = judge.score_case("[]", expected, _inputs_dir(cid))
    assert r["score"] == 0.0


@pytest.mark.parametrize("cid", CASE_IDS)
def test_gold_edits_wrapped_in_code_fence_still_scores_perfect(cid):
    """Solutions often wrap JSON in markdown fences -- the parser must
    tolerate that rather than penalizing formatting choices."""
    expected = _expected(cid)
    stdout = "```json\n" + json.dumps(expected["gold_edits"]) + "\n```"
    r = judge.score_case(stdout, expected, _inputs_dir(cid))
    assert r["score"] == 1.0


def test_case03_restraint_extra_invoice_edit_penalized():
    """case_03's ticket explicitly says NOT to touch past invoices. An
    otherwise-correct fix that also shotguns an unrelated invoice edit
    must be penalized (anti-shotgun / precision test)."""
    expected = _expected("case_03")
    shotgun = expected["gold_edits"] + [
        {"file": "invoices.csv", "op": "update",
         "match": {"invoice_id": "INV-3001"},
         "set": {"baked_addon_names": "Premium Support"}},
    ]
    r = judge.score_case(json.dumps(shotgun), expected, _inputs_dir("case_03"))
    assert r["score"] == 0.0
    assert "invoice_detail.py" in r.get("mismatched_reports", [])


def test_case02_partial_fix_missing_invoice_recompute_fails():
    """Only updating plans.csv without correcting the affected historical
    invoice must fail -- proves the two edits are both required, not
    redundant with each other."""
    expected = _expected("case_02")
    partial = [e for e in expected["gold_edits"] if e["file"] == "plans.csv"]
    r = judge.score_case(json.dumps(partial), expected, _inputs_dir("case_02"))
    assert r["score"] == 0.0


def test_case03_restraint_only_matches_billing_and_statement():
    """case_03's noop should differ ONLY on the two LIVE reports
    (billing_summary, customer_statement) -- invoice_detail and
    finance_ledger read baked columns the ticket doesn't touch, so they
    must already agree even before any fix is applied."""
    expected = _expected("case_03")
    r = judge.score_case("[]", expected, _inputs_dir("case_03"))
    assert set(r["mismatched_reports"]) == {"billing_summary.py", "customer_statement.py"}


@pytest.mark.parametrize("stdout,label", [
    ("not json at all, just prose explaining my fix", "prose"),
    ('{"file": "customers.csv"}', "json_object_not_list"),
    ("", "empty_string"),
])
def test_unparseable_output_scores_zero_no_crash(stdout, label):
    expected = _expected("case_01")
    r = judge.score_case(stdout, expected, _inputs_dir("case_01"))
    assert r["score"] == 0.0
    assert "reason" in r


def test_non_dict_list_entries_do_not_crash():
    expected = _expected("case_01")
    stdout = json.dumps(["a string", 42, None, {"file": "customers.csv"}])
    r = judge.score_case(stdout, expected, _inputs_dir("case_01"))
    assert r["score"] == 0.0


def test_infinity_value_does_not_crash():
    expected = _expected("case_01")
    stdout = ('[{"file":"customers.csv","op":"update",'
              '"match":{"customer_id":"CUST-001"},"set":{"region_id":Infinity}}]')
    r = judge.score_case(stdout, expected, _inputs_dir("case_01"))
    assert r["score"] == 0.0


def test_deeply_nested_json_does_not_crash():
    expected = _expected("case_01")
    stdout = "[" * 2000 + "]" * 2000
    r = judge.score_case(stdout, expected, _inputs_dir("case_01"))
    assert r["score"] == 0.0


def test_real_fix_pushed_beyond_cap_is_dropped_and_case_fails():
    """MAX_EDITS_SCORED caps how many edits are actually applied. Pad the
    list with MAX_EDITS_SCORED harmless-but-real edits (they touch an
    existing row/column no report reads) so the genuine fix edits land
    past the cap and get truncated -- proves the cap is enforced by
    dropping edits, not just present as an unused constant."""
    expected = _expected("case_01")
    filler = [{"file": "customers.csv", "op": "update",
               "match": {"customer_id": "CUST-001"}, "set": {"signup_date": "1999-01-01"}}
              for _ in range(judge.MAX_EDITS_SCORED)]
    padded = filler + expected["gold_edits"]
    r = judge.score_case(json.dumps(padded), expected, _inputs_dir("case_01"))
    assert r["score"] == 0.0


def test_missing_inputs_dir_scores_zero():
    expected = _expected("case_01")
    r = judge.score_case("[]", expected, ROOT / "inputs" / "does_not_exist")
    assert r["score"] == 0.0
