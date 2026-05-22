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
# NOTE: weights were redesigned in May 2026 to remove obvious-healthy-answer bias.
# NO option scores secure>=1 anymore. All-B totals below are recomputed from the
# new gold.cases.json.

def test_sum_traits_all_A_in_q1():
    """Q1 option A is {anxious: 3, people_pleasing: 1}."""
    j = _load_judge()
    expected = load_expected()
    # Just check Q1 contribution
    sums = j._sum_traits(["A"] + ["B"] * 19, expected["scoring_key"])
    assert sums["anxious"] >= 3   # Q1-A contributes at least 3 anxious
    assert sums["people_pleasing"] >= 1

def test_sum_traits_known_pattern():
    """All 'B' answers yield a deterministic profile (hand-computed from new gold weights).

      Q1-B: avoidant=2, toxic=2
      Q2-B: toxic=2, avoidant=2
      Q3-B: avoidant=2, toxic=1
      Q4-B: anxious=2, delulu=2
      Q5-B: delulu=3, anxious=2
      Q6-B: delulu=2, anxious=2
      Q7-B: avoidant=3, toxic=1
      Q8-B: avoidant=2, people_pleasing=1
      Q9-B: avoidant=2, people_pleasing=1
      Q10-B: avoidant=2, delulu=1
      Q11-B: avoidant=3
      Q12-B: avoidant=3
      Q13-B: avoidant=3, toxic=1
      Q14-B: toxic=3
      Q15-B: toxic=3, delulu=2
      Q16-B: toxic=2, anxious=2
      Q17-B: toxic=2, avoidant=1
      Q18-B: avoidant=2, toxic=2
      Q19-B: avoidant=3
      Q20-B: toxic=2, avoidant=2
    """
    j = _load_judge()
    expected = load_expected()
    sums = j._sum_traits(["B"] * 20, expected["scoring_key"])
    assert sums["secure"] == 0
    assert sums["anxious"] == 2+2+2+2 == 8
    assert sums["avoidant"] == 2+2+2+3+2+2+2+3+3+3+1+2+3+2 == 32
    assert sums["toxic"] == 2+2+1+1+1+3+3+2+2+2+2 == 21  # Q1,Q2,Q3,Q7,Q13,Q14,Q15,Q16,Q17,Q18,Q20
    assert sums["delulu"] == 2+3+2+1+2 == 10
    assert sums["unbothered"] == 0
    assert sums["people_pleasing"] == 1+1 == 2


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
    """All-anxious picks across probe pairs → no flips → not disorganized.

    With new weights:
      Q2-A (anx 3), Q7-A (anx 3) → both anx, no flip
      Q5-A (anx 2, pp 2), Q19-A (pp 3, anx 2) → both anx, no flip
      Q13-A (tox 2, anx 2), Q16-B (tox 2, anx 2) → both anx, no flip
    """
    j = _load_judge()
    expected = load_expected()
    answers = ["A"] * 20
    answers[15] = "B"  # Q16-B (anx-coded; matches Q13-A as anx)
    flips = j._count_disorganized_flips(answers, expected["scoring_key"])
    assert flips == 0

def test_disorganized_two_flips_triggers():
    """≥2 probe pairs flipping triggers disorganized.

    With new weights:
      Pair 1: Q2-A (anx) + Q7-B (av) → FLIP
      Pair 2: Q5-D (av) + Q19-A (anx) → FLIP
      Pair 3: Q13-A (anx) + Q16-B (anx) → no flip
    """
    j = _load_judge()
    expected = load_expected()
    answers = ["A"] * 20
    answers[6] = "B"   # Q7-B (av)
    answers[4] = "D"   # Q5-D (av)
    answers[15] = "B"  # Q16-B (anx, so pair 3 stays same-side)
    flips = j._count_disorganized_flips(answers, expected["scoring_key"])
    assert flips == 2

def test_disorganized_three_flips():
    """All three pairs flipping = 3.

    With new weights:
      Pair 1: Q2-B (av) + Q7-A (anx, default) → FLIP
      Pair 2: Q5-C (av) + Q19-C (anx) → FLIP
      Pair 3: Q13-B (av) + Q16-D (anx) → FLIP
    """
    j = _load_judge()
    expected = load_expected()
    answers = ["A"] * 20
    answers[1] = "B"   # Q2-B (av)
    answers[4] = "C"   # Q5-C (av)
    answers[18] = "C"  # Q19-C (anx)
    answers[12] = "B"  # Q13-B (av)
    answers[15] = "D"  # Q16-D (anx)
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

def test_judge_case_all_a_anxious_pattern():
    """All 'A' answers yield anxious primary with people_pleasing+toxic flavors.

    With new weights, all-A totals:
      anxious: 30 (dominant)
      avoidant: 3
      secure: 0
      people_pleasing: 24
      toxic: 8
      delulu: 7
      unbothered: 3
    Primary = anxious. Top 2 flavors = [people_pleasing, toxic].
    Label = "Anxious Texting Their Ex".
    """
    j = _load_judge()
    expected = load_expected()
    answers = ["A"] * 20
    stdout = json.dumps({"answers": answers})
    metrics = j.judge_case(stdout, expected)
    assert metrics["score"] == 1.0
    assert metrics["attachment_style"] == "anxious"
    assert metrics["label"] == "Anxious Texting Their Ex"
    assert metrics["raw_answers"] == answers


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
    """Flip 2 probe pairs → primary should be disorganized.

    Setup (with new weights):
      Pair 1 flip: Q2-A (anx, default) + Q7-B (av)
      Pair 2 flip: Q5-D (av) + Q19-A (anx, default)
      Pair 3 no flip: Q13-A (anx, default) + Q16-B (anx)
    → 2 flips → disorganized (overrides sum-based primary)
    """
    j = _load_judge()
    expected = load_expected()
    answers = ["A"] * 20
    answers[6] = "B"   # Q7-B (av)
    answers[4] = "D"   # Q5-D (av)
    answers[15] = "B"  # Q16-B (anx, so pair 3 stays same-side)
    stdout = json.dumps({"answers": answers})
    metrics = j.judge_case(stdout, expected)
    assert metrics["score"] == 1.0
    assert metrics["attachment_style"] == "disorganized"
