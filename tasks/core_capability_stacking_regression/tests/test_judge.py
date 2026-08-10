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
