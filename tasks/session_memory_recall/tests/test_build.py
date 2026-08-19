# tests/test_build.py
import json
import pathlib
import random
import re
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_cases as b  # noqa: E402

VOUCHER_KINDS = ("largest_debit_voucher", "nth_largest_voucher")


def _answers(kind, n=200):
    out = []
    for s in range(n):
        rng = random.Random(s * 7 + 13)
        rows = b.make_table(rng, rng.choice([16, 17, 18, 20]))
        out.append(b.derive(kind, rows, rng)[2])
    return out


def test_voucher_answers_are_not_confined_to_the_row_count():
    """The answer space must be the voucher numbering, not the table height.

    Numbering every table from AR-2026-0001 made the real space `size` wide --
    20 distinct answers over 2000 tables, best fixed guess 6.9% -- while
    assert_answer_hard_to_guess only checked the four-digit *shape* and so
    reported nothing.
    """
    for kind in VOUCHER_KINDS:
        answers = _answers(kind)
        assert len(set(answers)) >= 0.8 * len(answers), (
            f"{kind}: only {len(set(answers))} distinct answers in {len(answers)} tables"
        )


def test_no_fixed_voucher_guess_beats_two_percent():
    for kind in VOUCHER_KINDS:
        answers = _answers(kind)
        best = Counter(answers).most_common(1)[0][1] / len(answers)
        assert best < 0.02, f"{kind}: best fixed guess scores {best:.1%}"


def test_vouchers_within_one_table_are_unique_and_contiguous():
    rng = random.Random(4242)
    rows = b.make_table(rng, 18)
    nums = [int(r["voucher"].split("-")[-1]) for r in rows if r["voucher"]]
    assert len(set(nums)) == len(nums) == 18
    assert nums == list(range(nums[0], nums[0] + 18))


def test_every_voucher_keeps_the_four_digit_shape():
    for kind in VOUCHER_KINDS:
        for a in _answers(kind, n=50):
            assert re.fullmatch(r"AR-2026-\d{4}", a), a


def test_money_answers_clear_the_four_digit_minimum():
    for kind in ("closing_balance", "period_debits", "counterparty_total"):
        for s in range(50):
            rng = random.Random(s * 11 + 5)
            rows = b.make_table(rng, rng.choice([16, 18, 22]))
            answer = b.derive(kind, rows, rng)[2]
            b.assert_answer_hard_to_guess(f"sim_{s}", answer, "money")


def test_gold_cases_carry_no_answers():
    gold = json.loads((ROOT / "gold.cases.json").read_text())
    for case in gold["cases"]:
        assert "answer" not in case and "expected" not in case


def test_shipped_cases_do_not_leak_their_answer():
    for edir in sorted((ROOT / "expected").iterdir()):
        answer = json.loads((edir / "answer.json").read_text())["answer"]
        cdir = ROOT / "inputs" / edir.name
        b.assert_no_answer_leak(
            (cdir / "step2.txt").read_text(), (cdir / "README.md").read_text(), answer
        )
