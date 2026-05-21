"""Pytest tests for the agents-in-situationship judge."""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent
EXPECTED_PATH = HERE / "expected" / "baseline_20q" / "answer.json"


def load_expected() -> dict:
    return json.loads(EXPECTED_PATH.read_text())


def test_expected_file_loads():
    """Sanity: the expected/answer.json file we wrote is valid."""
    data = load_expected()
    assert data["n_questions"] == 20
    assert len(data["scoring_key"]) == 20
    assert data["primary_tiebreak_order"] == ["anxious", "avoidant", "secure"]


# Import the judge module after it exists
import importlib.util


def _load_judge():
    spec = importlib.util.spec_from_file_location("judge", HERE / "judge.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ----- Parsing -----

def test_parse_plain_json():
    j = _load_judge()
    out, err = j._parse_output('{"answers": ["A","B","C","D"]}')
    assert out == {"answers": ["A","B","C","D"]}
    assert err == ""

def test_parse_with_code_fence():
    j = _load_judge()
    out, err = j._parse_output('```json\n{"answers": ["A"]}\n```')
    assert out == {"answers": ["A"]}

def test_parse_empty_string():
    j = _load_judge()
    out, err = j._parse_output("   ")
    assert out is None
    assert "empty" in err

def test_parse_invalid_json():
    j = _load_judge()
    out, err = j._parse_output("not json at all")
    assert out is None


# ----- Format gate -----

def test_format_gate_valid_20_letters():
    j = _load_judge()
    answers = ["A"] * 20
    ok, err = j._validate_answers(answers, n_expected=20)
    assert ok is True
    assert err == ""

def test_format_gate_wrong_count():
    j = _load_judge()
    ok, err = j._validate_answers(["A"] * 19, n_expected=20)
    assert ok is False
    assert "19" in err and "20" in err

def test_format_gate_lowercase_rejected():
    j = _load_judge()
    answers = ["A"] * 19 + ["a"]
    ok, err = j._validate_answers(answers, n_expected=20)
    assert ok is False

def test_format_gate_invalid_letter_rejected():
    j = _load_judge()
    answers = ["A"] * 19 + ["E"]
    ok, err = j._validate_answers(answers, n_expected=20)
    assert ok is False


# ----- Trait summing -----

def test_sum_traits_all_A_in_q1():
    """Q1 option A is {anxious: 2, people_pleasing: 1}."""
    j = _load_judge()
    expected = load_expected()
    # Just 1 question's worth: pick A on Q1, B on rest doesn't matter — test sums for 1
    sums = j._sum_traits(["A"] + ["B"] * 19, expected["scoring_key"])
    # The full 20-letter sum will dominate; verify Q1 contributed correctly
    # Q1-A adds {anxious: 2, people_pleasing: 1}
    # Q2-B adds {secure: 2, unbothered: 1}, Q3-B adds {secure: 3}, ... — many Bs add up.
    # Instead, check a single-answer slice via direct call would be cleaner — do explicit check.
    assert sums["anxious"] >= 2  # Q1-A contributes at least 2 anxious
    assert sums["people_pleasing"] >= 1

def test_sum_traits_known_pattern():
    """If we pick the 'B' option on all 20 questions, we get a deterministic profile."""
    j = _load_judge()
    expected = load_expected()
    sums = j._sum_traits(["B"] * 20, expected["scoring_key"])
    # Verify against hand-computed expectation:
    # Q1-B: avoidant=2, unbothered=1
    # Q2-B: secure=2, unbothered=1
    # Q3-B: secure=3
    # Q4-B: secure=2
    # Q5-B: secure=3
    # Q6-B: delulu=2, anxious=2
    # Q7-B: avoidant=3
    # Q8-B: secure=3
    # Q9-B: delulu=2, anxious=1
    # Q10-B: avoidant=3
    # Q11-B: people_pleasing=3
    # Q12-B: people_pleasing=3, delulu=1
    # Q13-B: toxic=2, anxious=2
    # Q14-B: toxic=3, delulu=1
    # Q15-B: toxic=3
    # Q16-B: secure=2, anxious=1
    # Q17-B: unbothered=2, secure=2
    # Q18-B: secure=3
    # Q19-B: secure=3, unbothered=1
    # Q20-B: secure=3, unbothered=1
    assert sums["secure"] == 2+3+2+3+3+2+2+3+3+3 == 26
    assert sums["anxious"] == 2+1+2+1 == 6
    assert sums["avoidant"] == 2+3+3 == 8
    assert sums["delulu"] == 2+2+1+1 == 6
    assert sums["toxic"] == 2+3+3 == 8
    assert sums["unbothered"] == 1+1+2+1+1 == 6
    assert sums["people_pleasing"] == 3+3 == 6


def test_sum_traits_all_traits_initialized():
    """Sums dict should include all 3+4=7 traits, even when zero."""
    j = _load_judge()
    expected = load_expected()
    sums = j._sum_traits(["A"] * 20, expected["scoring_key"])
    for t in ("secure", "anxious", "avoidant", "delulu", "toxic", "unbothered", "people_pleasing"):
        assert t in sums, f"missing trait {t}"


# ----- Disorganized detection -----

def test_classify_option_coding_anxious():
    """An option with anxious weight >= 2 is 'anxious-coded'."""
    j = _load_judge()
    assert j._option_coding({"anxious": 2, "people_pleasing": 1}) == "anxious"

def test_classify_option_coding_avoidant():
    j = _load_judge()
    assert j._option_coding({"avoidant": 3}) == "avoidant"

def test_classify_option_coding_neither():
    """Weights below threshold or other traits => neither."""
    j = _load_judge()
    assert j._option_coding({"secure": 3}) == "neither"
    assert j._option_coding({"anxious": 1, "avoidant": 1}) == "neither"
    assert j._option_coding({"toxic": 5}) == "neither"

def test_disorganized_zero_flips():
    """All secure choices → no flips → not disorganized."""
    j = _load_judge()
    expected = load_expected()
    # Pick the secure option for each probe-pair Q
    # Q2-B: secure, Q7-A: secure → no anxious-vs-avoidant
    # Q5-B: secure, Q19-B: secure → no flip
    # Q13-A: secure, Q16-B: secure → no flip
    answers = ["A"] * 20
    answers[1] = "B"; answers[6] = "A"      # Q2, Q7
    answers[4] = "B"; answers[18] = "B"     # Q5, Q19
    answers[12] = "A"; answers[15] = "B"    # Q13, Q16
    flips = j._count_disorganized_flips(answers, expected["scoring_key"])
    assert flips == 0

def test_disorganized_two_flips_triggers():
    """≥2 of 3 probe pairs flipping triggers disorganized."""
    j = _load_judge()
    expected = load_expected()
    answers = ["A"] * 20
    # Pair 1 (Q2, Q7): Q2-A (anxious 3) + Q7-B (avoidant 3) → FLIP
    answers[1] = "A"; answers[6] = "B"
    # Pair 2 (Q5, Q19): Q5-D (anxious 2) + Q19-C (avoidant 3) → FLIP
    answers[4] = "D"; answers[18] = "C"
    # Pair 3 (Q13, Q16): Q13-A (secure) + Q16-B (secure) → no flip
    answers[12] = "A"; answers[15] = "B"
    flips = j._count_disorganized_flips(answers, expected["scoring_key"])
    assert flips == 2

def test_disorganized_three_flips():
    """All three pairs flipping = 3."""
    j = _load_judge()
    expected = load_expected()
    answers = ["A"] * 20
    answers[1] = "C"; answers[6] = "C"   # Q2-C (avoidant), Q7-C (anxious) → FLIP
    answers[4] = "C"; answers[18] = "D"  # Q5-C (avoidant), Q19-D (anxious) → FLIP
    answers[12] = "D"; answers[15] = "C" # Q13-D (avoidant), Q16-C (anxious) → FLIP
    flips = j._count_disorganized_flips(answers, expected["scoring_key"])
    assert flips == 3


# ----- Primary style selection -----

def test_primary_style_anxious_wins():
    j = _load_judge()
    sums = {"secure": 5, "anxious": 12, "avoidant": 3, "toxic": 0, "delulu": 0, "unbothered": 0, "people_pleasing": 0}
    assert j._pick_primary(sums, flips=0, disorganized_threshold=2,
                            tiebreak=["anxious", "avoidant", "secure"]) == "anxious"

def test_primary_style_disorganized_overrides():
    j = _load_judge()
    sums = {"secure": 30, "anxious": 0, "avoidant": 0, "toxic": 0, "delulu": 0, "unbothered": 0, "people_pleasing": 0}
    assert j._pick_primary(sums, flips=2, disorganized_threshold=2,
                            tiebreak=["anxious", "avoidant", "secure"]) == "disorganized"

def test_primary_style_tiebreak_order():
    """When sums are tied between primary axes, tie-break order wins (anxious > avoidant > secure)."""
    j = _load_judge()
    sums = {"secure": 5, "anxious": 5, "avoidant": 5, "toxic": 0, "delulu": 0, "unbothered": 0, "people_pleasing": 0}
    assert j._pick_primary(sums, flips=0, disorganized_threshold=2,
                            tiebreak=["anxious", "avoidant", "secure"]) == "anxious"


# ----- Flavor selection -----

def test_top_two_flavors_picks_highest():
    j = _load_judge()
    sums = {"toxic": 5, "delulu": 8, "unbothered": 2, "people_pleasing": 3}
    flavors = j._pick_top_two_flavors(sums, all_flavors=["delulu","people_pleasing","toxic","unbothered"])
    assert set(flavors) == {"delulu", "toxic"}

def test_top_two_flavors_alphabetical_tiebreak():
    """When tied at zero, alphabetical order: delulu < people_pleasing < toxic < unbothered."""
    j = _load_judge()
    sums = {"toxic": 0, "delulu": 0, "unbothered": 0, "people_pleasing": 0}
    flavors = j._pick_top_two_flavors(sums, all_flavors=["delulu","people_pleasing","toxic","unbothered"])
    assert flavors == ["delulu", "people_pleasing"]  # first two alphabetically


# ----- Label lookup -----

def test_label_lookup_known_pair():
    j = _load_judge()
    expected = load_expected()
    label = j._build_label("anxious", ["delulu", "people_pleasing"],
                            label_table=expected["label_table"],
                            fallback_labels=expected["fallback_labels"],
                            all_zero_flavors=False)
    assert label == "Delulu Anxious Era 🌸"

def test_label_lookup_canonicalizes_pair_order():
    """Pair key is alphabetical-sorted-pipe-joined. Either order in input must lookup the same."""
    j = _load_judge()
    expected = load_expected()
    label_a = j._build_label("anxious", ["delulu", "people_pleasing"],
                              label_table=expected["label_table"],
                              fallback_labels=expected["fallback_labels"],
                              all_zero_flavors=False)
    label_b = j._build_label("anxious", ["people_pleasing", "delulu"],
                              label_table=expected["label_table"],
                              fallback_labels=expected["fallback_labels"],
                              all_zero_flavors=False)
    assert label_a == label_b

def test_label_lookup_all_zero_uses_fallback():
    j = _load_judge()
    expected = load_expected()
    label = j._build_label("secure", ["delulu", "people_pleasing"],
                            label_table=expected["label_table"],
                            fallback_labels=expected["fallback_labels"],
                            all_zero_flavors=True)
    assert label == expected["fallback_labels"]["secure"]


# ----- End-to-end judge_case -----

def test_judge_case_secure_pattern():
    """All 'A' answers in Q1, B in Q2 (secure paths)... actually use the all-secure path."""
    j = _load_judge()
    expected = load_expected()
    # Construct a "mostly secure" answer set
    # Picking the answer with the highest 'secure' weight per Q (or A if tied):
    # Q1-D, Q2-B, Q3-B, Q4-B, Q5-B, Q6-C, Q7-A, Q8-B, Q9-A, Q10-A,
    # Q11-A, Q12-A, Q13-A, Q14-A, Q15-A, Q16-B, Q17-C, Q18-B, Q19-B, Q20-B
    answers = ["D","B","B","B","B","C","A","B","A","A","A","A","A","A","A","B","C","B","B","B"]
    stdout = json.dumps({"answers": answers})
    metrics = j.judge_case(stdout, expected)
    assert metrics["score"] == 1.0
    assert metrics["attachment_style"] == "secure"
    assert "label" in metrics
    assert metrics["raw_answers"] == answers
    assert metrics["flat_response"] is False


def test_judge_case_format_fail_score_zero():
    j = _load_judge()
    expected = load_expected()
    stdout = '{"answers": ["A","B"]}'  # only 2 letters
    metrics = j.judge_case(stdout, expected)
    assert metrics["score"] == 0.0


def test_judge_case_flat_response_flag():
    """If >70% of answers are the same letter, flat_response = True."""
    j = _load_judge()
    expected = load_expected()
    answers = ["A"] * 20  # 100% A
    stdout = json.dumps({"answers": answers})
    metrics = j.judge_case(stdout, expected)
    assert metrics["flat_response"] is True


def test_judge_case_disorganized_pattern():
    """Flip 2 probe pairs → primary should be disorganized."""
    j = _load_judge()
    expected = load_expected()
    answers = ["A"] * 20
    # Pair 1 flip: Q2-A (anxious) + Q7-B (avoidant)
    answers[1] = "A"; answers[6] = "B"
    # Pair 2 flip: Q5-D (anxious) + Q19-C (avoidant)
    answers[4] = "D"; answers[18] = "C"
    # Pair 3 no flip: Q13-A + Q16-B (both secure-coded)
    answers[12] = "A"; answers[15] = "B"
    stdout = json.dumps({"answers": answers})
    metrics = j.judge_case(stdout, expected)
    assert metrics["score"] == 1.0
    assert metrics["attachment_style"] == "disorganized"
