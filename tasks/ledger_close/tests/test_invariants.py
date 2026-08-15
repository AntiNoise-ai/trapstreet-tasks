"""Invariant tests for ledger_close.

These assert the properties the task's validity rests on. Each one exists
because a calibration run produced a number the task had not earned.
"""
from __future__ import annotations

import importlib.util
import json
import random
import re
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("bc", HERE / "build_cases.py")
bc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bc)

CASES = json.loads((HERE / "gold.cases.json").read_text())["cases"]


def year(case):
    rng = random.Random(case["seed"])
    entries = bc.make_entries(rng, case["months"], case["per_month"])
    bc.apply_rename(entries)
    bc.mark_demonstration(case["id"], entries)
    return rng, entries


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_gold_carries_no_answer(case):
    assert "answer" not in case, "the answer is computed, never authored"


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_case_id_is_opaque(case):
    assert re.fullmatch(r"case_\d\d", case["id"]), \
        "a solution can read its own inputs path; ids must not leak the answer"


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_settlement_identity(case):
    _, entries = year(case)
    open_res, unapplied = bc.settle(entries)
    debits = round(sum(r["debit"] for r in entries if r["debit"] is not None), 2)
    credits = round(sum(r["credit"] for r in entries if r["credit"] is not None), 2)
    assert abs(sum(res for _, res in open_res.values())
               - (debits - credits + unapplied)) < 0.05


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_policy_is_inducible(case):
    """Two discriminating examples across two narration types, and enough
    post-changeover evidence that the change reads as a regime rather than a
    keying error."""
    _, entries = year(case)
    shown = [r for r in entries if r["credit"] is not None and r.get("demonstrated")]
    disc = [r for r in shown if r["discriminating"]]
    assert len(disc) >= bc.MIN_DISCRIMINATING
    assert len({r["narration"] for r in disc}) >= 2
    assert sum(1 for r in shown if r["shows_change"]) >= bc.MIN_CHANGE_EVIDENCE


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_something_is_left_to_solve(case):
    _, entries = year(case)
    rest = [r for r in entries if r["credit"] is not None and not r.get("demonstrated")]
    assert len(rest) >= 6, "the memo must not work through the whole year"


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_every_mechanism_moves_the_answer(case):
    """Compared invoice by invoice, not by total: total open is
    debits - credits + unapplied, so an error that only moves money between
    invoices leaves the total unchanged and would look harmless."""
    rng, entries = year(case)
    by_month = bc.split_months(entries)
    gap_month = bc.choose_gap(rng, by_month, case["months"])
    gap = by_month[gap_month][-max(3, case["per_month"] // 4):]
    decoy = bc.make_entries(random.Random(case["seed"] + 7), 2, case["per_month"])
    for r in decoy:
        r["date"] = r["date"].replace("2026", "2025")
        r["voucher"] = r["voucher"].replace("AR-", "AR-9")

    truth, _ = bc.settle(entries)
    for name, alt in {
        "missing the supplement": bc.settle([r for r in entries if r not in gap])[0],
        "folding in the prior year": bc.settle(entries + decoy)[0],
        "splitting the re-coded customer": bc.settle(entries, merge_renamed=False)[0],
    }.items():
        assert bc._residual_distance(truth, alt) >= 100.0, f"{name} is decoration"


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_answer_has_no_shortcut(case):
    _, entries = year(case)
    answer = json.loads((HERE / "expected" / case["id"] / "answer.json").read_text())["answer"]
    debits = round(sum(r["debit"] for r in entries if r["debit"] is not None), 2)
    credits = round(sum(r["credit"] for r in entries if r["credit"] is not None), 2)
    for shortcut in (debits, credits, round(debits - credits, 2)):
        assert abs(float(answer) - shortcut) >= bc.SHORTCUT_TOLERANCE
    assert len(answer.split(".")[0]) >= 4, "too few digits to be unguessable"


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_answer_does_not_leak_into_the_inputs(case):
    answer = json.loads((HERE / "expected" / case["id"] / "answer.json").read_text())["answer"]
    for path in (HERE / "inputs" / case["id"]).rglob("*"):
        if path.is_file():
            assert not re.search(rf"(?<![\d.]){re.escape(answer)}(?![\d.])",
                                 path.read_text()), f"answer appears in {path.name}"


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_the_short_month_is_detectable(case):
    """The gap must be findable the only way it can be: a month's closing
    balance failing to tie to the next month's opening."""
    ledgers = sorted((HERE / "inputs" / case["id"] / "ledgers").glob("2026-??.txt"))
    breaks, previous = 0, None
    for path in ledgers:
        text = path.read_text()
        opening = float(re.search(r"Opening balance\s+([\d,\.]+)", text).group(1).replace(",", ""))
        closing = float(re.search(r"Closing balance\s+([\d,\.]+)", text).group(1).replace(",", ""))
        if previous is not None and abs(previous - opening) > 0.01:
            breaks += 1
        previous = closing
    assert breaks == 1, f"expected exactly one tie-out break, found {breaks}"
