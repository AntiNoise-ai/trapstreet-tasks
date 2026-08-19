# tests/test_judge.py
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import judge  # noqa: E402

MONEY = {"id": "case_01", "category": "closing_balance",
         "answer": "27940.01", "answer_kind": "money"}
VOUCHER = {"id": "case_03", "category": "largest_debit_voucher",
           "answer": "AR-2026-0004", "answer_kind": "voucher"}


# --- the contract: the value alone on the last line ---

def test_bare_value_scores_one():
    assert judge.score_case("27940.01", MONEY)["score"] == 1.0


def test_formatted_value_scores_one():
    assert judge.score_case("$27,940.01", MONEY)["score"] == 1.0


def test_bare_voucher_scores_one():
    assert judge.score_case("AR-2026-0004", VOUCHER)["score"] == 1.0


# --- prose around the value is tolerated (agent harnesses emit it) ---

def test_value_ending_a_sentence_scores_one():
    out = "The closing balance is 27,940.01."
    assert judge.score_case(out, MONEY)["score"] == 1.0


def test_value_cited_alongside_a_voucher_scores_one():
    out = "From ledger AR-2026-0016: 27,940.01"
    assert judge.score_case(out, MONEY)["score"] == 1.0


def test_value_after_a_match_count_scores_one():
    out = "Retrieved from memory (1 match): 27,940.01"
    assert judge.score_case(out, MONEY)["score"] == 1.0


def test_value_cited_alongside_a_date_scores_one():
    out = "Recalled from the session of 2026-01-01: 27,940.01"
    assert judge.score_case(out, MONEY)["score"] == 1.0


def test_value_in_prose_after_a_preamble_scores_one():
    out = "Checking my memory store now.\nThe closing balance is 27,940.01."
    assert judge.score_case(out, MONEY)["score"] == 1.0


def test_voucher_in_prose_scores_one():
    out = "The largest debit was voucher AR-2026-0004."
    assert judge.score_case(out, VOUCHER)["score"] == 1.0


# --- nothing survived, or the wrong thing did ---

def test_unknown_scores_zero():
    assert judge.score_case("UNKNOWN", MONEY)["score"] == 0.0


def test_final_line_reporting_a_different_value_scores_zero():
    assert judge.score_case("The closing balance is 12,345.67.", MONEY)["score"] == 0.0


def test_correct_value_in_preamble_but_wrong_value_on_final_line_scores_zero():
    out = "I recall 27,940.01 from earlier.\nFinal answer: 12,345.67"
    assert judge.score_case(out, MONEY)["score"] == 0.0


def test_shotgun_of_candidates_on_the_final_line_scores_zero():
    out = "It is one of 27,940.01, 21,393.47 or 19,413.20"
    assert judge.score_case(out, MONEY)["score"] == 0.0


def test_reprinting_the_whole_ledger_scores_zero():
    out = ("15,875.74\n19,632.67\n15,241.63\n10,226.07\n"
           "1,239.68\n5,068.17\n11,369.27\n27,940.01\n23,062.29\nDone.")
    assert judge.score_case(out, MONEY)["score"] == 0.0


def test_shotgun_of_vouchers_scores_zero():
    out = "Could be AR-2026-0004, AR-2026-0007 or AR-2026-0011. See above."
    assert judge.score_case(out, VOUCHER)["score"] == 0.0
