"""Tests for judge.py's scoring.

The discrimination test is the important one: a plausible-but-wrong answer --
the kind a genuine but weak attempt actually produces, not an empty string --
must score clearly below the gold answer. That is a direct function call with
no LLM involved, it costs nothing, and it catches a judge too lenient to tell
weak from strong before any money is spent on a real run.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import judge  # noqa: E402


def expected_for(case_id: str) -> dict:
    return json.loads((HERE / "expected" / case_id / "answer.json").read_text())


def case_id_for(scenario: str, level: str, arm: str) -> str:
    grid = json.loads((HERE / "gold.cases.json").read_text())["cases"]
    return next(
        c["id"] for c in grid
        if c["scenario"] == scenario and c["stack_level"] == level and c["overlap_class"] == arm
    )


S04_L3_HIGH = case_id_for("s04", "L3", "high")

GOLD_S04 = json.dumps([
    {"name": "storage_copy_object",
     "arguments": {"source_path": "/planning/renewals-model.xlsx", "destination_folder": "/finance"}},
    {"name": "chat_post_message", "arguments": {"channel": "#finance", "text": "Your copy is in /finance."}},
])


# --- exact hit -----------------------------------------------------------

def test_gold_answer_scores_one():
    m = judge.score_case(GOLD_S04, expected_for(S04_L3_HIGH))
    assert m["score"] == 1.0
    assert m["completion"] == 1.0 and m["correctness"] == 1.0
    assert m["failure_reason"] is None


def test_order_is_not_scored():
    reordered = json.dumps(list(reversed(json.loads(GOLD_S04))))
    assert judge.score_case(reordered, expected_for(S04_L3_HIGH))["score"] == 1.0


# --- discrimination: plausible-but-wrong must score clearly lower --------

def test_near_miss_substitution_scores_well_below_gold():
    """storage_share_object grants access to the one existing file instead of
    producing a second copy -- exactly the confusion the high-overlap pack is
    built to provoke."""
    weak = json.dumps([
        {"name": "storage_share_object",
         "arguments": {"source_path": "/planning/renewals-model.xlsx", "grantees": ["finance"]}},
        {"name": "chat_post_message", "arguments": {"channel": "#finance", "text": "Shared."}},
    ])
    m = judge.score_case(weak, expected_for(S04_L3_HIGH))
    assert m["score"] < 0.75
    assert m["failure_reason"] == "near_miss"
    assert m["missing_calls"] == ["storage_copy_object"]


def test_shotgunning_the_catalog_collapses_the_score():
    """Listing every plausible skill to catch the right one must not pay."""
    shotgun = json.loads(GOLD_S04) + [
        {"name": n, "arguments": {}} for n in
        ["storage_move_object", "storage_create_shortcut", "storage_share_object", "chat_send_dm"]
    ]
    m = judge.score_case(json.dumps(shotgun), expected_for(S04_L3_HIGH))
    assert m["completion"] == 1.0          # both right calls are in there
    assert m["correctness"] < 0.4          # but drowned in speculation
    assert m["score"] < 0.6


def test_partial_workflow_separates_completion_from_correctness():
    partial = json.dumps([json.loads(GOLD_S04)[0]])
    m = judge.score_case(partial, expected_for(S04_L3_HIGH))
    assert m["completion"] == 0.5
    assert m["correctness"] == 1.0
    assert m["failure_reason"] == "incomplete"


def test_right_tool_wrong_argument_is_classified_as_bad_arguments():
    wrong = json.dumps([
        {"name": "storage_copy_object",
         "arguments": {"source_path": "/planning/renewals-model.xlsx", "destination_folder": "/planning"}},
        {"name": "chat_post_message", "arguments": {"channel": "#finance", "text": "done"}},
    ])
    m = judge.score_case(wrong, expected_for(S04_L3_HIGH))
    assert m["failure_reason"] == "bad_arguments"
    assert m["completion"] == 0.5


def test_hallucinated_tool_is_classified_unrelated():
    made_up = json.dumps([
        {"name": "storage_duplicate_file", "arguments": {"path": "x"}},
        {"name": "chat_post_message", "arguments": {"channel": "#finance", "text": "done"}},
    ])
    assert judge.score_case(made_up, expected_for(S04_L3_HIGH))["failure_reason"] == "unrelated_tool"


# --- argument generosity: correct answers must not fail on formatting ----

def test_attendee_list_accepted_as_delimited_string_and_as_repr():
    exp = expected_for(case_id_for("s02", "L3", "high"))
    for attendees in ('Priya, Marco', "['Priya', 'Marco']", ["Marco", "Priya"]):
        ans = json.dumps([
            {"name": "calendar_create_event",
             "arguments": {"title": "Design review", "attendees": attendees,
                           "start": "10:00", "duration_minutes": 30}},
            {"name": "mail_create_draft",
             "arguments": {"to": ["Priya", "Marco"], "subject": "Agenda", "body": "..."}},
        ])
        assert judge.score_case(ans, exp)["score"] == 1.0, attendees


def test_iso_timestamp_satisfies_a_clock_time_expectation():
    exp = expected_for(case_id_for("s02", "L3", "high"))
    ans = json.dumps([
        {"name": "calendar_create_event",
         "arguments": {"title": "Design review", "attendees": ["Priya", "Marco"],
                       "start": "2026-08-13T10:00:00Z", "duration_minutes": 30}},
        {"name": "mail_create_draft",
         "arguments": {"to": ["Priya", "Marco"], "subject": "Agenda", "body": "..."}},
    ])
    assert judge.score_case(ans, exp)["score"] == 1.0


def test_wrong_clock_time_still_fails():
    exp = expected_for(case_id_for("s02", "L3", "high"))
    ans = json.dumps([
        {"name": "calendar_create_event",
         "arguments": {"title": "Design review", "attendees": ["Priya", "Marco"],
                       "start": "10:30", "duration_minutes": 30}},
        {"name": "mail_create_draft",
         "arguments": {"to": ["Priya", "Marco"], "subject": "Agenda", "body": "..."}},
    ])
    assert judge.score_case(ans, exp)["completion"] == 0.5


def test_path_final_component_matches_but_a_different_folder_does_not():
    exp = expected_for(S04_L3_HIGH)
    ok = json.dumps([
        {"name": "storage_copy_object",
         "arguments": {"source_path": "/planning/renewals-model.xlsx",
                       "destination_folder": "drive/finance"}},
        {"name": "chat_post_message", "arguments": {"channel": "#finance", "text": "done"}},
    ])
    assert judge.score_case(ok, exp)["score"] == 1.0


def test_alternative_argument_key_names_are_accepted():
    ans = json.dumps([
        {"name": "storage_copy_object",
         "args": {"source_path": "/planning/renewals-model.xlsx", "destination_folder": "/finance"}},
        {"name": "chat_post_message", "params": {"channel": "#finance", "text": "done"}},
    ])
    assert judge.score_case(ans, expected_for(S04_L3_HIGH))["score"] == 1.0


def test_code_fenced_output_is_accepted():
    fenced = f"```json\n{GOLD_S04}\n```"
    assert judge.score_case(fenced, expected_for(S04_L3_HIGH))["score"] == 1.0


def test_prose_wrapped_output_is_accepted():
    wrapped = f"Here are the calls I would make:\n{GOLD_S04}\nLet me know if that works."
    assert judge.score_case(wrapped, expected_for(S04_L3_HIGH))["score"] == 1.0


# --- malformed output degrades, never crashes ---------------------------

def test_non_json_output_scores_zero_without_raising():
    m = judge.score_case("I'm not sure which tools to use here.", expected_for(S04_L3_HIGH))
    assert m["score"] == 0.0 and m["failure_reason"] == "unparseable"


def test_empty_array_scores_zero():
    assert judge.score_case("[]", expected_for(S04_L3_HIGH))["failure_reason"] == "unparseable"


def test_non_dict_entries_in_the_list_are_ignored_not_assumed():
    ans = json.dumps(["storage_copy_object", 42, None] + json.loads(GOLD_S04))
    assert judge.score_case(ans, expected_for(S04_L3_HIGH))["score"] == 1.0


def test_nan_and_infinity_arguments_degrade_cleanly():
    ans = '[{"name": "calendar_create_event", "arguments": {"title": "x", "attendees": ["Priya", "Marco"], "start": "10:00", "duration_minutes": Infinity}}]'
    m = judge.score_case(ans, expected_for(case_id_for("s02", "L3", "high")))
    assert m["score"] == 0.0

    ans_nan = ans.replace("Infinity", "NaN")
    assert judge.score_case(ans_nan, expected_for(case_id_for("s02", "L3", "high")))["score"] == 0.0


def test_deeply_nested_json_does_not_crash_the_judge():
    deep = "[" * 400 + "]" * 400
    assert judge.score_case(deep, expected_for(S04_L3_HIGH))["score"] == 0.0


def test_single_object_is_accepted_as_a_one_call_answer():
    m = judge.score_case(json.dumps(json.loads(GOLD_S04)[0]), expected_for(S04_L3_HIGH))
    assert m["completion"] == 0.5 and m["correctness"] == 1.0


def test_wrapped_calls_key_is_unwrapped():
    ans = json.dumps({"tool_calls": json.loads(GOLD_S04)})
    assert judge.score_case(ans, expected_for(S04_L3_HIGH))["score"] == 1.0


def test_duplicate_correct_call_does_not_double_count():
    """A repeated right call is one match and one surplus, not two matches."""
    dup = json.loads(GOLD_S04)
    ans = json.dumps(dup + [dup[0]])
    m = judge.score_case(ans, expected_for(S04_L3_HIGH))
    assert m["completion"] == 1.0
    assert m["correctness"] < 1.0


def test_malformed_gold_degrades_to_a_legible_verdict_not_a_crash():
    """A judge that raises reads as broken infrastructure rather than as the
    authoring mistake it is. Cannot fire on a built case -- build_cases.py
    refuses to render a scenario with fewer than two required calls."""
    for bad in ({}, {"required_calls": []}, {"required_calls": None}):
        m = judge.score_case("[]", bad)
        assert m["score"] == 0.0 and m["failure_reason"] == "no_gold"


def test_doing_the_job_then_volunteering_extra_is_not_a_near_miss():
    """A model that makes the copy correctly and then helpfully shares it takes
    a precision hit that is IMPOSSIBLE in the low-overlap arm, because the
    sharing skill only exists in the high arm. That is eagerness, not
    confusion, and conflating the two would let politeness fabricate the
    finding."""
    eager = json.loads(GOLD_S04) + [
        {"name": "storage_share_object",
         "arguments": {"source_path": "/planning/renewals-model.xlsx", "grantees": ["finance"]}},
    ]
    m = judge.score_case(json.dumps(eager), expected_for(S04_L3_HIGH))
    assert m["completion"] == 1.0
    assert m["correctness"] < 1.0
    assert m["failure_reason"] == "unsolicited_addition"


def test_substitution_is_still_a_near_miss():
    """The distinction must not swallow the failure it was split out of."""
    swapped = json.dumps([
        {"name": "storage_share_object",
         "arguments": {"source_path": "/planning/renewals-model.xlsx", "grantees": ["finance"]}},
        {"name": "chat_post_message", "arguments": {"channel": "#finance", "text": "done"}},
    ])
    m = judge.score_case(swapped, expected_for(S04_L3_HIGH))
    assert m["completion"] < 1.0
    assert m["failure_reason"] == "near_miss"


def test_l4_carries_the_bulk_filler_in_both_arms():
    for arm in ("high", "low"):
        exp = expected_for(case_id_for("s04", "L4", arm))
        assert exp["n_skills"] > 100, arm
    hi = expected_for(case_id_for("s04", "L4", "high"))["n_skills"]
    lo = expected_for(case_id_for("s04", "L4", "low"))["n_skills"]
    assert hi == lo, "L4 must not make one arm bigger than the other"


def test_following_an_installed_skills_guidance_is_classified_as_instruction_bleed():
    """The job is done correctly and the only surplus call is one an installed
    skill's own guidance told the agent to make. This is the mechanism a
    practitioner means by 'installing a skill broke my agent'."""
    exp = expected_for(S04_L3_HIGH)
    assert "compliance_record_action" in exp["bleed_names"]
    bled = json.loads(GOLD_S04) + [
        {"name": "compliance_record_action",
         "arguments": {"action": "copied for Finance", "artefact": "/planning/renewals-model.xlsx"}},
    ]
    m = judge.score_case(json.dumps(bled), exp)
    assert m["completion"] == 1.0
    assert m["correctness"] < 1.0
    assert m["failure_reason"] == "instruction_bleed"


def test_doing_the_job_through_the_wrong_backend_is_its_own_failure():
    """storage_copy_to_cold_tier really does make an independent copy. Nothing
    in its description rules it out -- only the house rules do."""
    exp = expected_for(S04_L3_HIGH)
    assert "storage_copy_to_cold_tier" in exp["backend_names"]
    wrong = json.dumps([
        {"name": "storage_copy_to_cold_tier",
         "arguments": {"source_path": "/planning/renewals-model.xlsx", "destination_folder": "/finance"}},
        {"name": "chat_post_message", "arguments": {"channel": "#finance", "text": "done"}},
    ])
    m = judge.score_case(wrong, exp)
    assert m["failure_reason"] == "wrong_backend"
    assert m["completion"] == 0.5


def test_a_confusable_neighbour_is_still_a_near_miss_not_a_backend_error():
    """The new reasons must not swallow the one they were split out of."""
    swapped = json.dumps([
        {"name": "storage_share_object",
         "arguments": {"source_path": "/planning/renewals-model.xlsx", "grantees": ["finance"]}},
        {"name": "chat_post_message", "arguments": {"channel": "#finance", "text": "done"}},
    ])
    assert judge.score_case(swapped, expected_for(S04_L3_HIGH))["failure_reason"] == "near_miss"


def test_competitor_dose_reaches_the_metrics_dict():
    """grader.py's dose plot reads `n_competitors` off the judge's output. It
    was absent for several revisions, so `by_competitor_dose` came back empty
    on a full matrix run -- a diagnostic reporting nothing reads as no signal,
    which is worse than having no diagnostic."""
    m = judge.score_case("[]", expected_for(S04_L3_HIGH))
    assert m["n_competitors"] is not None and m["n_competitors"] > 0


def test_volunteering_a_base_skill_is_over_eager_not_incomplete():
    """completion == 1.0 with surplus calls is never 'incomplete'. Surplus base
    skills had no label and fell through to the wrong one. They need their own:
    base skills sit in both arms, so that surplus is arm-neutral and cannot
    produce the arm difference instruction_bleed does."""
    eager = json.loads(GOLD_S04) + [
        {"name": "contacts_lookup_person", "arguments": {"name": "someone"}},
    ]
    m = judge.score_case(json.dumps(eager), expected_for(S04_L3_HIGH))
    assert m["completion"] == 1.0
    assert m["failure_reason"] == "over_eager"


def test_incomplete_still_fires_when_a_call_is_actually_missing():
    m = judge.score_case(json.dumps([json.loads(GOLD_S04)[0]]), expected_for(S04_L3_HIGH))
    assert m["completion"] < 1.0 and m["failure_reason"] == "incomplete"


def test_interfering_pair_is_derived_exactly_not_guessed():
    """(skill that should have been used, skill used instead) -- the pair a
    merge decision is actually about."""
    exp = expected_for(S04_L3_HIGH)
    swapped = json.dumps([
        {"name": "storage_share_object",
         "arguments": {"source_path": "/planning/renewals-model.xlsx", "grantees": ["finance"]}},
        {"name": "chat_post_message", "arguments": {"channel": "#finance", "text": "done"}},
    ])
    m = judge.score_case(swapped, exp)
    assert m["interfering_pairs"] == [["storage_copy_object", "storage_share_object"]]


def test_surplus_without_displacement_yields_no_pair():
    """Instruction bleed adds work rather than replacing any. Emitting a pair
    would fabricate a substitution that did not happen -- and it is exactly the
    case a merge decision cannot help with."""
    bled = json.loads(GOLD_S04) + [
        {"name": "compliance_record_action",
         "arguments": {"action": "copied", "artefact": "/planning/renewals-model.xlsx"}},
    ]
    m = judge.score_case(json.dumps(bled), expected_for(S04_L3_HIGH))
    assert m["failure_reason"] == "instruction_bleed"
    assert m["interfering_pairs"] == []


def test_a_missing_call_with_an_unrelated_surplus_yields_no_pair():
    """Only a competitor that declares it stands in for the missing skill
    counts. A hallucinated call displaced nothing in particular.

    (The first draft of this test used chat_send_dm as the 'unrelated' call and
    failed -- correctly. It declares competes_with chat_post_message, which is
    one of the calls s04 was missing, so it IS a displacement. The test premise
    was wrong, not the judge.)"""
    m = judge.score_case(json.dumps([
        {"name": "storage_duplicate_file", "arguments": {"path": "x"}},
    ]), expected_for(S04_L3_HIGH))
    assert m["missing_calls"] and m["interfering_pairs"] == []


def test_every_substituting_competitor_can_form_a_pair():
    """A competitor that declares competes_with but never appears in a pair
    would be a mapping that silently does nothing -- the same shape of fault as
    the dose plot that read n_competitors nobody emitted."""
    exp = expected_for(S04_L3_HIGH)
    for name, base in exp["competes_with"].items():
        m = judge.score_case(json.dumps([{"name": name, "arguments": {}}]), exp)
        if base in m["missing_calls"]:
            assert [base, name] in m["interfering_pairs"], f"{name} -> {base}"


def test_matched_cases_share_a_pair_key_and_differ_by_arm():
    """The two halves of a comparison must be findable from the metrics alone.

    Run pages list cases flat and default to hiding the perfect ones, and the
    control arm here is mostly perfect -- so without a key that survives into
    the metrics, a reader sees orphaned failures with nothing to compare them
    against. `pair` has to match across the arms and `arm` has to distinguish
    them, or the grouping this exists for silently stops working.
    """
    for scenario, level in [("s04", "L3"), ("s01", "L1"), ("s08", "L2")]:
        hi = judge.pair_labels(expected_for(case_id_for(scenario, level, "high")))
        lo = judge.pair_labels(expected_for(case_id_for(scenario, level, "low")))
        assert hi["pair"] == lo["pair"] == f"{scenario}/{level}"
        assert hi["arm"] != lo["arm"]
        assert hi["arm"].startswith("high") and lo["arm"].startswith("low")


def test_pair_key_reaches_the_metrics_a_run_actually_reports():
    """pair_labels() being right is not enough -- score_case has two exit
    paths that build their own dicts, and a key added to one and not the other
    is invisible exactly on the cases that failed."""
    exp = expected_for(S04_L3_HIGH)
    m = judge.score_case(GOLD_S04, exp)
    assert m["pair"] == "s04/L3"
    assert m["arm"].startswith("high")
