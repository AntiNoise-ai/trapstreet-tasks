# tests/test_judge.py
import sys, pathlib, json
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import judge  # noqa: E402


def _expected(**overrides):
    e = {
        "id": "case_01",
        "category": "gifting_disclosure",
        "trap": "gifting_disclosure",
        "expected_requires_disclosure": True,
    }
    e.update(overrides)
    return e


# -- exact hits per trap category -----------------------------------------

def test_gifting_disclosure_full_credit():
    out = {"requires_disclosure": True, "findings": [
        {"description": "Gifting is not a loophole -- a gifted post still requires disclosure, and it must be clear and conspicuous."}
    ]}
    result = judge.score_case(json.dumps(out), _expected())
    assert result["score"] == 1.0
    assert result["flagged_gifting_disclosure"] is True


def test_attribution_full_credit():
    out = {"requires_disclosure": True, "findings": [
        {"description": "Since links aren't clickable in a podcast, use a unique promo code as the primary attribution method."}
    ]}
    expected = _expected(category="attribution", trap="attribution")
    result = judge.score_case(json.dumps(out), expected)
    assert result["score"] == 1.0
    assert result["flagged_attribution"] is True


def test_no_script_full_credit():
    out = {"requires_disclosure": True, "findings": [
        {"description": "We won't write a word-for-word script -- instead here's a creative brief with 2-3 talking points and creative freedom for their own voice."}
    ]}
    expected = _expected(category="no_script", trap="no_script")
    result = judge.score_case(json.dumps(out), expected)
    assert result["score"] == 1.0
    assert result["flagged_no_script"] is True


def test_macro_flat_fee_full_credit():
    out = {"requires_disclosure": True, "findings": [
        {"description": "Don't just pay their rate -- negotiate a hybrid compensation structure and lock in usage rights, and consider a portfolio of micro and nano creators instead."}
    ]}
    expected = _expected(category="macro_flat_fee", trap="macro_flat_fee")
    result = judge.score_case(json.dumps(out), expected)
    assert result["score"] == 1.0
    assert result["flagged_macro_flat_fee"] is True


def test_clean_control_full_credit_when_no_false_alarm():
    out = {"requires_disclosure": False, "findings": []}
    expected = _expected(category="clean_control", trap="none", expected_requires_disclosure=False)
    result = judge.score_case(json.dumps(out), expected)
    assert result["score"] == 1.0


# -- partial credit / misses -----------------------------------------------

def test_gifting_case_misses_trap_partial_credit():
    out = {"requires_disclosure": True, "findings": []}
    result = judge.score_case(json.dumps(out), _expected())
    assert result["score"] == pytest.approx(0.4)  # disclosure correct, no trap credit


def test_clean_control_false_alarm_loses_trap_credit():
    """A solution that always warns about disclosure requirements, even
    when the situation is already correctly handled, must NOT get trap
    credit on a clean case -- shotgunning every trap category into every
    response is a losing strategy, not a free win."""
    out = {"requires_disclosure": True, "findings": [
        {"description": "Make sure this is a material connection that still requires disclosure."}
    ]}
    expected = _expected(category="clean_control", trap="none", expected_requires_disclosure=True)
    result = judge.score_case(json.dumps(out), expected)
    assert result["score"] == pytest.approx(0.4)  # disclosure correct only


def test_wrong_disclosure_answer_loses_that_component_only():
    out = {"requires_disclosure": False, "findings": [
        {"description": "Gifting is not a loophole -- a gifted post still requires disclosure."}
    ]}
    result = judge.score_case(json.dumps(out), _expected())
    assert result["score"] == pytest.approx(0.6)  # trap credit only, disclosure wrong


# -- malformed-output robustness (must never raise) ------------------------

def test_non_json_output_scores_zero():
    result = judge.score_case("sure, here's my advice: just post it!", _expected())
    assert result["score"] == 0.0


def test_json_wrapped_in_markdown_fence_still_parses():
    text = '```json\n{"requires_disclosure": true, "findings": []}\n```'
    result = judge.score_case(text, _expected())
    assert result["score"] == pytest.approx(0.4)


def test_non_dict_findings_entries_are_skipped_not_crashed():
    out = {"requires_disclosure": True,
           "findings": ["a plain string finding", 42,
                        {"description": "gifting still needs disclosure, not a loophole"}]}
    result = judge.score_case(json.dumps(out), _expected())
    assert result["flagged_gifting_disclosure"] is True


def test_findings_not_a_list_does_not_crash():
    out = {"requires_disclosure": True, "findings": "not a list"}
    result = judge.score_case(json.dumps(out), _expected())
    assert result["flagged_gifting_disclosure"] is False


def test_missing_requires_disclosure_field_does_not_crash():
    out = {"findings": []}
    result = judge.score_case(json.dumps(out), _expected())
    assert result["disclosure_correct"] is False


def test_deeply_nested_json_does_not_crash():
    nested = "{" * 200 + "}" * 200
    result = judge.score_case(nested, _expected())
    assert result["score"] == 0.0


# -- keyword-matching exploits (scoring-design.md) --------------------------

def test_bare_word_in_unrelated_sentence_does_not_false_match():
    """'material' alone (not the phrase 'material connection') must not
    trigger a gifting-disclosure match."""
    out = {"requires_disclosure": True, "findings": [
        {"description": "This is a material improvement to the campaign, unrelated to any disclosure question."}
    ]}
    result = judge.score_case(json.dumps(out), _expected())
    assert result["flagged_gifting_disclosure"] is False


def test_disclaiming_sentence_does_not_false_match():
    """Documents the known keyword-matching ceiling -- a sentence that
    denies the issue applies still counts as a match, same limitation
    accepted in the ab_test_planning task's judge."""
    out = {"requires_disclosure": True, "findings": [
        {"description": "There's no material connection here, so nothing still requires disclosure in this case."}
    ]}
    result = judge.score_case(json.dumps(out), _expected())
    assert result["flagged_gifting_disclosure"] is True


# -- anti-shotgun cap --------------------------------------------------------

def test_findings_beyond_cap_are_not_scored():
    padding = [{"description": f"unrelated note number {i}"} for i in range(5)]
    out = {"requires_disclosure": True,
           "findings": padding + [{"description": "gifting still needs disclosure, not a loophole"}]}
    assert len(out["findings"]) == 6
    result = judge.score_case(json.dumps(out), _expected())
    assert result["flagged_gifting_disclosure"] is False  # the real finding is 6th, past MAX_FINDINGS_SCORED=5


def test_shotgunning_all_four_traps_fails_the_clean_cases():
    """The structural anti-shotgun check: always flagging every trap
    category scores well on all 9 trap cases but fails both clean_control
    cases, netting out worse than being selective."""
    out = {"requires_disclosure": True, "findings": [
        {"description": "Gifting is not a loophole, still requires disclosure."},
        {"description": "Use a unique promo code for attribution."},
        {"description": "Don't script word-for-word, provide talking points instead."},
        {"description": "Negotiate hybrid compensation and usage rights, consider micro and nano creators."},
    ]}
    expected = _expected(category="clean_control", trap="none", expected_requires_disclosure=True)
    result = judge.score_case(json.dumps(out), expected)
    assert result["score"] == pytest.approx(0.4)  # disclosure only, all trap credit lost to false alarms
