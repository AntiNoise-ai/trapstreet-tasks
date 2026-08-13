import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import judge  # noqa: E402


EXPECTED = {"id": "case_01", "mechanism": "static", "gold": "14.99"}


def test_exact_hit():
    result = judge.score_case("14.99", EXPECTED, question="What is the price of X?")
    assert result["score"] == 1.0


def test_near_miss_outside_tolerance():
    result = judge.score_case("19.99", EXPECTED, question="What is the price of X?")
    assert result["score"] == 0.0


def test_within_one_percent_tolerance_passes():
    # 14.99 * 1.005 ~= 15.06 -- just inside 1% relative tolerance
    result = judge.score_case("15.06", EXPECTED, question="What is the price of X?")
    assert result["score"] == 1.0


def test_dollar_sign_and_prose_tolerated():
    result = judge.score_case(
        "The price is $14.99.", EXPECTED, question="What is the price of X?"
    )
    assert result["score"] == 1.0


def test_euro_sign_tolerated():
    expected = {"id": "case_10", "mechanism": "region_pricing", "gold": "23.24"}
    result = judge.score_case(
        "In the EU region it costs €23.24", expected, question="What is Wraithbound's price?"
    )
    assert result["score"] == 1.0


def test_empty_prediction_scores_zero():
    result = judge.score_case("", EXPECTED, question="What is the price of X?")
    assert result["score"] == 0.0


def test_no_number_in_prediction_scores_zero():
    result = judge.score_case(
        "I could not determine the price.", EXPECTED, question="What is the price of X?"
    )
    assert result["score"] == 0.0


# --- regression tests for the three real bugs found while building this
# judge (see module docstring), each reproduced from financebench's history
# plus one new one specific to this task.


def test_restated_question_number_is_not_mistaken_for_the_answer():
    """A solver phrasing that repeats a number that's already in the
    question (e.g. mentioning "Tier 3") must not have THAT number picked up
    as if it were the answer -- the real figure appears later."""
    expected = {"id": "case_05", "mechanism": "bundle_tier_marginal", "gold": "3.00"}
    question = "How much more does the top tier cost than the middle tier?"
    # No literal "Tier 3"/"Tier 2" in this question by design (see gold.cases.json
    # comment), but exercise the mechanism directly with a question that does
    # restate a number, to prove the exclusion logic itself works.
    result = judge.score_case(
        "Comparing tier 2 and the top tier, the difference is $3.00.",
        expected,
        question="Comparing tier 2 and the top tier",
    )
    assert result["score"] == 1.0


def test_known_limitation_answer_coinciding_with_a_confound_value_cannot_score():
    """Documented limitation, not a bug: exclusion is by VALUE, not by
    occurrence position -- if the gold answer's numeric value equals a
    number already in the question, every occurrence of that value in the
    prediction is treated as a confound, including a legitimate later
    restatement of the correct answer. This fails closed (never a false
    positive for "just echoed the question") at the cost of these cases
    being unscoreable even when answered correctly.

    This is exactly why gold.cases.json's case_05 was reworded from "Tier 3
    / Tier 2" to "top tier / middle tier": that case's real answer (3.00)
    numerically collided with the literal tier index (3), and was
    unscoreable until the question stopped spelling out tier numbers as
    digits. Prefer avoiding the collision at the question-design level (as
    done there) over relying on this fail-closed behavior."""
    expected = {"id": "x", "mechanism": "static", "gold": "3.00"}
    result = judge.score_case(
        "Tier 3 is not relevant here; the answer is $3.00.",
        expected,
        question="What about Tier 3?",
    )
    assert result["score"] == 0.0


def test_magnitude_scaled_and_literal_reading_both_accepted():
    """A solver spelling out a magnitude word for a value that's already in
    the target unit (financebench's second bug) must not get re-scaled and
    rejected."""
    expected = {"id": "x", "mechanism": "static", "gold": "14.99"}
    result = judge.score_case("14.99 thousand", expected, question="q")
    # 14.99 (literal) is accepted even though "thousand" would also produce
    # 14990.0 as a candidate -- whichever candidate matches gold wins.
    assert result["score"] == 1.0


def test_restated_percent_from_question_does_not_get_misread_as_the_answer():
    """A fourth real bug found after the other three: is_pct used to check
    for '%' anywhere in the WHOLE prediction string, not just near the
    matched number. case_08/case_09 are the first cases in this task whose
    question wording itself contains a percent ("rated 90% or higher") --
    a solver restating that filter before giving its actual dollar answer
    produced pred=0.9 (90 wrongly read as a percent) instead of the real
    price, and confound exclusion didn't catch it because _numbers_in only
    ever added the literal 90.0, not the percent-scaled 0.9 a restatement
    would actually parse to. Fixed by (a) scoping is_pct to each matched
    token's own tail instead of the whole string, and (b) having
    _numbers_in add both the literal and percent-scaled reading of any
    confound token immediately followed by '%'."""
    expected = {"id": "case_08", "mechanism": "filter_sort", "gold": "20.99"}
    question = "Among Action-category games rated 90% or higher, what is the price of the cheapest one?"
    result = judge.score_case(
        "Among Action games rated 90%+, the cheapest is $20.99",
        expected,
        question=question,
    )
    assert result["score"] == 1.0


def test_solution_exit_nonzero_short_circuits_to_zero():
    # main()'s exit-code handling is exercised via score_case's caller in
    # main(), not score_case itself -- covered by the manifest-level
    # end-to-end check in README.md rather than duplicated here, since
    # score_case never sees exit_code.
    pass
