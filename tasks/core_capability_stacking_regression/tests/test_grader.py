"""Tests for grader.py -- the pre-registered analysis itself.

The sign test and the curve-shape rule ARE the conclusion this task reaches.
An error in either produces a confident wrong answer rather than a crash, so
they are tested against hand-computed cases.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import grader  # noqa: E402

SCENARIOS = [f"s{i:02d}" for i in range(1, 7)]
LEVELS = ["L0", "L1", "L2", "L3", "L4"]


def run_grader(cases: list[dict]) -> dict:
    env = {**os.environ, "TRAPTASK_MANIFEST": json.dumps(cases)}
    out = subprocess.run(
        [sys.executable, str(HERE / "grader.py")],
        capture_output=True, text=True, env=env, check=True,
    )
    return json.loads(out.stdout)


def manifest(score_of, failure_of=None, difficulty_of=None) -> list[dict]:
    """Build a full manifest from score_of(scenario, level, arm).

    Scenarios default to the `medium` tier, i.e. inside PRIMARY_TIERS, so a
    test that does not care about tiering behaves as if every scenario counts.
    """
    cases = []
    for s in SCENARIOS:
        for lvl in LEVELS:
            for arm in (["none"] if lvl == "L0" else ["high", "low"]):
                m = {
                    "scenario": s, "stack_level": lvl, "overlap_class": arm,
                    "score": score_of(s, lvl, arm),
                    "completion": 1.0, "correctness": 1.0,
                    "difficulty": (difficulty_of or {}).get(s, "medium"),
                }
                if failure_of:
                    fr = failure_of(s, lvl, arm)
                    if fr:
                        m["failure_reason"] = fr
                cases.append({"case_id": f"{s}_{lvl}_{arm}", "duration": 1.0,
                              "metrics": m, "cost": None})
    return cases


# --- the sign test -------------------------------------------------------

def test_sign_test_matches_hand_computation():
    assert grader.sign_test_p(6, 6) == 1 / 64          # 0.015625
    assert grader.sign_test_p(5, 6) == 7 / 64
    assert grader.sign_test_p(3, 6) == 42 / 64
    assert grader.sign_test_p(0, 0) == 1.0             # no discordant pairs


def test_all_six_scenarios_favouring_the_hypothesis_reaches_significance():
    """high scores below low at L3 in every scenario -- the smallest p this
    design can attain, and it clears 0.05."""
    res = run_grader(manifest(
        lambda s, lvl, arm: 0.5 if (lvl == "L3" and arm == "high") else 1.0
    ))
    eff = res["secondary_sign_test_L3"]
    assert eff["n_favouring_hypothesis"] == 6
    assert eff["n_against"] == 0
    assert eff["sign_test_p"] == 0.0156


def test_ties_are_not_counted_as_evidence():
    """Identical scores in both arms must not be read as support."""
    res = run_grader(manifest(lambda s, lvl, arm: 1.0))
    eff = res["secondary_sign_test_L3"]
    assert eff["n_tied"] == 6
    assert eff["n_favouring_hypothesis"] == 0
    assert eff["sign_test_p"] == 1.0


def test_effect_running_the_wrong_way_is_reported_as_such():
    res = run_grader(manifest(
        lambda s, lvl, arm: 0.5 if (lvl == "L3" and arm == "low") else 1.0
    ))
    eff = res["secondary_sign_test_L3"]
    assert eff["n_favouring_hypothesis"] == 0 and eff["n_against"] == 6
    assert eff["sign_test_p"] == 1.0


# --- the curve-shape rule ------------------------------------------------

def test_flat_curve_is_called_flat_not_linear():
    """A curve that wobbles below the absolute floor has no shape to report."""
    jitter = {"L0": 1.0, "L1": 0.98, "L2": 0.99, "L3": 0.95, "L4": 0.95}
    res = run_grader(manifest(lambda s, lvl, arm: jitter[lvl]))
    assert res["curve_shape"] == "flat"


def test_evenly_declining_curve_is_called_linear():
    steady = {"L0": 1.0, "L1": 0.8, "L2": 0.6, "L3": 0.4, "L4": 0.4}
    res = run_grader(manifest(lambda s, lvl, arm: steady[lvl]))
    assert res["curve_shape"] == "linear"


def test_a_cliff_is_called_an_inflection_at_the_right_level():
    cliff = {"L0": 1.0, "L1": 0.98, "L2": 0.96, "L3": 0.30, "L4": 0.30}
    res = run_grader(manifest(lambda s, lvl, arm: cliff[lvl]))
    assert res["curve_shape"] == "inflection@L3"


def test_inflection_can_be_detected_mid_curve():
    mid = {"L0": 1.0, "L1": 0.98, "L2": 0.40, "L3": 0.38, "L4": 0.38}
    res = run_grader(manifest(lambda s, lvl, arm: mid[lvl]))
    assert res["curve_shape"] == "inflection@L2"


def test_curve_is_read_off_the_high_overlap_arm_only():
    """A cliff in the low-overlap arm must not be reported as the curve."""
    def score(s, lvl, arm):
        if arm == "low" and lvl == "L3":
            return 0.1
        return 1.0
    res = run_grader(manifest(score))
    assert res["curve_shape"] == "flat"
    assert res["curve_low_overlap"]["L3"] == 0.1


# --- the quarantine ------------------------------------------------------

def test_solution_errors_are_reported_next_to_the_number_they_corrupt():
    """Provider failures concentrated at L3-high are the most likely false
    positive this task can produce; they must stay visible."""
    def score(s, lvl, arm):
        return 0.0 if (lvl == "L3" and arm == "high") else 1.0

    def failure(s, lvl, arm):
        return "solution_error" if (lvl == "L3" and arm == "high") else None

    res = run_grader(manifest(score, failure))
    assert res["n_solution_error"] == 6
    assert res["solution_errors_by_stack_level"] == {"L3": 6}
    # the headline still counts them 0.0 ...
    assert res["score"] < 1.0
    # ... but the uncorrupted number sits right beside it
    assert res["score_excluding_solution_errors"] == 1.0
    # and the "effect" they fabricate is visible as an error concentration
    assert res["secondary_sign_test_L3"]["n_favouring_hypothesis"] == 6


def test_degradation_surface_is_reported_per_cell():
    res = run_grader(manifest(
        lambda s, lvl, arm: 0.5 if (lvl == "L3" and arm == "high") else 1.0
    ))
    assert res["by_cell"]["L3/high"] == 0.5
    assert res["by_cell"]["L3/low"] == 1.0
    assert res["by_stack_level"]["L0"] == 1.0
    assert res["n_total"] == 54


def test_curve_is_also_reported_against_competitor_dose():
    """The level axis counts packs added, not overlap added -- at L2 one
    scenario sits at 3 competitors and another at 4. Reporting only the level
    curve would hide that."""
    doses = {("s01", "L3"): 4, ("s02", "L3"): 6, ("s03", "L3"): 6,
             ("s04", "L3"): 5, ("s05", "L3"): 5, ("s06", "L3"): 7}
    cases = []
    for (s, lvl), dose in doses.items():
        cases.append({"case_id": f"{s}_{lvl}", "duration": 1.0, "cost": None, "metrics": {
            "scenario": s, "stack_level": lvl, "overlap_class": "high",
            "n_competitors": dose, "score": 1.0 - dose / 10,
            "completion": 1.0, "correctness": 1.0}})
    res = run_grader(cases)
    assert res["by_competitor_dose"]["4"] == 0.6
    assert res["by_competitor_dose"]["7"] == 0.3
    assert res["dose_by_cell"]["L3/high"] == [4, 5, 6, 7]


# --- pre-registered tier restriction -------------------------------------

def test_easy_tier_cannot_enter_the_primary_test():
    """The easy tier states its own disqualifier in the request, so it is a
    floor check. Letting it into the sign test would mean the reported n
    depended on which scenarios happened to separate."""
    tiers = {"s01": "easy", "s02": "easy", "s03": "easy",
             "s04": "medium", "s05": "medium", "s06": "hard"}
    res = run_grader(manifest(
        lambda s, lvl, arm: 0.5 if (lvl == "L3" and arm == "high") else 1.0,
        difficulty_of=tiers,
    ))
    eff = res["secondary_sign_test_L3"]
    assert eff["n_scenarios"] == 3
    assert eff["n_favouring_hypothesis"] == 3
    assert sorted(eff["excluded_scenarios"]) == ["s01", "s02", "s03"]
    # three discordant pairs cannot reach 0.05 however one-sided they are
    assert eff["sign_test_p"] == 0.125


def test_headline_curve_is_read_off_the_pre_registered_tiers_only():
    """An easy tier pinned at ceiling would flatten the averaged curve, and the
    inflection call is made from that curve."""
    tiers = {"s01": "easy", "s02": "easy", "s03": "easy",
             "s04": "medium", "s05": "medium", "s06": "hard"}

    def score(s, lvl, arm):
        if tiers[s] == "easy":
            return 1.0
        return {"L0": 1.0, "L1": 0.9, "L2": 0.8, "L3": 0.2, "L4": 0.2}[lvl] if arm != "low" else 1.0

    res = run_grader(manifest(score, difficulty_of=tiers))
    assert res["curve_high_overlap"]["L3"] == 0.2           # tiers that count
    assert res["curve_high_overlap_all_tiers"]["L3"] == 0.6  # diluted by easy
    assert res["curve_shape"] == "inflection@L3"
    assert res["curve_high_by_difficulty"]["easy"]["L3"] == 1.0


def test_difficulty_breakdown_is_reported():
    tiers = {"s01": "easy", "s02": "easy", "s03": "easy",
             "s04": "medium", "s05": "medium", "s06": "edge"}
    res = run_grader(manifest(lambda s, lvl, arm: 1.0, difficulty_of=tiers))
    assert set(res["by_difficulty"]) == {"easy", "medium", "edge"}
    assert res["primary_tiers"] == ["medium", "hard"]


# --- the primary statistic: sign-flip permutation ------------------------

def test_permutation_matches_hand_computation():
    """Every scenario favouring the hypothesis by the same amount is the most
    extreme arrangement there is: exactly one of 2^n sign assignments."""
    assert grader.permutation_p([0.2] * 6) == 1 / 64
    assert grader.permutation_p([0.2] * 9) == 1 / 512
    # a single flat zero doubles the count of ties-as-extreme arrangements
    assert grader.permutation_p([0.0]) == 1.0
    # symmetric evidence cannot be significant
    assert grader.permutation_p([0.2, -0.2]) > 0.4


def test_permutation_survives_one_wrong_direction_scenario():
    """The whole reason for switching off the L3 sign test: one scenario going
    the wrong way must not be fatal when the rest are strongly with it."""
    diffs = [0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, -0.05]
    assert grader.permutation_p(diffs) < 0.05
    # the same shape kills the sign test (8 favour, 1 against, n=9)
    assert grader.sign_test_p(8, 9) > 0.019
    assert grader.sign_test_p(5, 6) > 0.10        # and at n=6 it is hopeless


def test_primary_test_uses_all_three_overlap_levels():
    def score(s, lvl, arm):
        if arm == "high":
            return {"L0": 1.0, "L1": 0.9, "L2": 0.8, "L3": 0.7, "L4": 0.7}[lvl]
        return 1.0
    res = run_grader(manifest(score))
    pt = res["primary_test"]
    assert pt["n_scenarios"] == 6
    # mean of (1-0.9, 1-0.8, 1-0.7) = 0.2 for every scenario
    assert pt["mean_diff"] == 0.2
    assert pt["permutation_p"] == round(1 / 64, 4)


def test_l4_is_a_separate_probe_and_never_enters_the_curve():
    """L4 raises bulk in both arms. If it leaked into the dose curve, a bulk
    effect would be read as an overlap inflection."""
    def score(s, lvl, arm):
        if lvl == "L4" and arm == "high":
            return 0.1
        return 1.0
    res = run_grader(manifest(score))
    assert res["curve_shape"] == "flat"                    # L0-L3 untouched
    assert res["curve_high_overlap"]["L4"] == 0.1          # still reported
    assert res["bulk_probe_L4"]["mean_low_minus_high"] == 0.9
    assert res["bulk_probe_L4"]["permutation_p"] == round(1 / 64, 4)
    assert res["primary_test"]["mean_diff"] == 0.0         # primary is L1-L3
