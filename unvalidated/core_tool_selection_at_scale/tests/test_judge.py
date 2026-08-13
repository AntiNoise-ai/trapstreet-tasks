"""Judge unit tests. Run: python3 -m pytest tests/ -v"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from judge import safe_json_loads, score_case, value_matches  # noqa: E402

EXPECTED = {
    "correct_tool_name": "payments_refund_charge",
    "expected_args": {"charge_id": ["ch_8812"], "amount": [64.5, "64.50", "$64.50"]},
    "near_miss_names": [
        "payments_void_authorization", "payments_issue_store_credit",
        "payments_open_chargeback_dispute", "payments_refund_invoice_line",
        "payments_cancel_subscription",
    ],
}

LIST_EXPECTED = {
    "correct_tool_name": "calendar_find_common_free_slots",
    "expected_args": {
        "attendees": [["Priya", "Marco"]],
        "duration_minutes": [30],
    },
    "near_miss_names": ["calendar_find_free_slots"],
}


def call(name, args):
    return json.dumps({"name": name, "arguments": args})


# --- happy path --------------------------------------------------------------

def test_exact_match_scores_one():
    out = call("payments_refund_charge", {"charge_id": "ch_8812", "amount": 64.5})
    assert score_case(out, EXPECTED)["score"] == 1.0


def test_extra_arguments_do_not_break_a_correct_call():
    out = call("payments_refund_charge",
               {"charge_id": "ch_8812", "amount": 64.5, "reason": "requested_by_customer"})
    assert score_case(out, EXPECTED)["score"] == 1.0


def test_markdown_fenced_output_is_tolerated():
    out = "```json\n" + call("payments_refund_charge", {"charge_id": "ch_8812", "amount": "$64.50"}) + "\n```"
    assert score_case(out, EXPECTED)["score"] == 1.0


def test_numeric_string_amount_matches():
    out = call("payments_refund_charge", {"charge_id": "ch_8812", "amount": "64.50"})
    assert score_case(out, EXPECTED)["score"] == 1.0


# --- failure classification --------------------------------------------------

def test_near_miss_is_labelled_as_such():
    out = call("payments_void_authorization", {"charge_id": "ch_8812"})
    r = score_case(out, EXPECTED)
    assert r["score"] == 0.0
    assert r["failure_mode"] == "near_miss"
    assert r["called_tool"] == "payments_void_authorization"


def test_unrelated_filler_tool_is_distinguished_from_a_near_miss():
    out = call("inventory_item_archive", {"inventory_item_id": "x"})
    r = score_case(out, EXPECTED)
    assert r["score"] == 0.0
    assert r["failure_mode"] == "unrelated_tool"


def test_correct_tool_wrong_argument_is_its_own_mode():
    out = call("payments_refund_charge", {"charge_id": "ch_8812", "amount": 129.0})
    r = score_case(out, EXPECTED)
    assert r["score"] == 0.0
    assert r["failure_mode"] == "bad_arguments"


def test_missing_expected_argument_fails():
    out = call("payments_refund_charge", {"charge_id": "ch_8812"})
    assert score_case(out, EXPECTED)["score"] == 0.0


def test_unparseable_output_degrades_to_zero_not_a_crash():
    for bad in ["", "I would call payments_refund_charge", "{{{", "null"]:
        r = score_case(bad, EXPECTED)
        assert r["score"] == 0.0


def test_arguments_field_must_be_an_object():
    out = json.dumps({"name": "payments_refund_charge", "arguments": "ch_8812"})
    assert score_case(out, EXPECTED)["score"] == 0.0


# --- anti-shotgun ------------------------------------------------------------

def test_array_output_scores_only_the_first_call():
    shotgun = json.dumps([
        {"name": "payments_void_authorization", "arguments": {"charge_id": "ch_8812"}},
        {"name": "payments_refund_charge", "arguments": {"charge_id": "ch_8812", "amount": 64.5}},
    ])
    r = score_case(shotgun, EXPECTED)
    assert r["score"] == 0.0, "listing every plausible tool must not earn credit"
    assert r["called_tool"] == "payments_void_authorization"


def test_array_output_with_correct_call_first_still_scores():
    shotgun = json.dumps([
        {"name": "payments_refund_charge", "arguments": {"charge_id": "ch_8812", "amount": 64.5}},
        {"name": "payments_void_authorization", "arguments": {"charge_id": "ch_8812"}},
    ])
    assert score_case(shotgun, EXPECTED)["score"] == 1.0


# --- collection arguments ----------------------------------------------------

def test_attendee_list_order_does_not_matter():
    out = call("calendar_find_common_free_slots",
               {"attendees": ["Marco", "Priya"], "duration_minutes": 30})
    assert score_case(out, LIST_EXPECTED)["score"] == 1.0


def test_attendees_as_delimited_string_is_accepted():
    out = call("calendar_find_common_free_slots",
               {"attendees": "Priya, Marco", "duration_minutes": "30"})
    assert score_case(out, LIST_EXPECTED)["score"] == 1.0


def test_wrong_attendee_set_fails():
    out = call("calendar_find_common_free_slots",
               {"attendees": ["Priya"], "duration_minutes": 30})
    assert score_case(out, LIST_EXPECTED)["score"] == 0.0


def test_single_element_list_satisfies_a_scalar_expectation():
    assert value_matches(["design-team@corp.example"], ["design-team@corp.example"])


# --- parsing -----------------------------------------------------------------

def test_json_embedded_in_prose_is_recovered():
    out = 'Sure! Here is the call:\n{"name": "payments_refund_charge", "arguments": {"charge_id": "ch_8812", "amount": 64.5}}\nHope that helps.'
    assert score_case(out, EXPECTED)["score"] == 1.0


def test_safe_json_loads_never_raises():
    for bad in ["", "[", "{'a': 1}", "\x00", "[" * 200]:
        safe_json_loads(bad)


# --- serialisation quirks that must not count as selection failures ----------

def test_stringified_python_list_is_accepted():
    """Flat-text solutions often serialise collections as a repr. Rejecting
    that penalises the presentation mode, not the model's selection."""
    out = call("calendar_find_common_free_slots",
               {"attendees": "['Priya', 'Marco']", "duration_minutes": 30})
    assert score_case(out, LIST_EXPECTED)["score"] == 1.0


def test_stringified_list_with_wrong_members_still_fails():
    out = call("calendar_find_common_free_slots",
               {"attendees": "['Priya', 'Dana']", "duration_minutes": 30})
    assert score_case(out, LIST_EXPECTED)["score"] == 0.0


PATH_EXPECTED = {
    "correct_tool_name": "storage_copy_object",
    "expected_args": {
        "source_path": ["/shared/planning/q3_forecast.xlsx"],
        "destination_folder": ["Finance", "/Finance", "finance", "/shared/finance"],
    },
    "near_miss_names": ["storage_move_object"],
}


@pytest.mark.parametrize("folder", ["Finance", "/Finance", "folder/Finance", "/folder/Finance",
                                    "/shared/finance", "finance/"])
def test_path_like_folder_matches_on_final_component(folder):
    out = call("storage_copy_object",
               {"source_path": "/shared/planning/q3_forecast.xlsx", "destination_folder": folder})
    assert score_case(out, PATH_EXPECTED)["score"] == 1.0


@pytest.mark.parametrize("folder", ["/shared/planning", "Legal", "/finance_archive"])
def test_wrong_folder_still_fails(folder):
    out = call("storage_copy_object",
               {"source_path": "/shared/planning/q3_forecast.xlsx", "destination_folder": folder})
    assert score_case(out, PATH_EXPECTED)["score"] == 0.0


# --- clock times vs full timestamps ------------------------------------------

TIME_EXPECTED = {
    "correct_tool_name": "logs_query_range",
    "expected_args": {
        "service": ["checkout"],
        "level": ["error"],
        "start_time": ["09:00", "9:00", "0900"],
        "end_time": ["09:30", "9:30", "0930"],
    },
    "near_miss_names": ["logs_tail_stream"],
}


def test_iso_timestamp_satisfies_a_clock_time_expectation():
    """The query says 'this morning' and gives no date, so a model taking the
    schema's ISO-8601 option must invent one. The hour and minute are the part
    it could get right, and this task scores tool selection, not formatting."""
    out = call("logs_query_range", {
        "service": "checkout", "level": "error",
        "start_time": "2023-02-20T09:00:00.000Z", "end_time": "2023-02-20T09:30:00.000Z"})
    assert score_case(out, TIME_EXPECTED)["score"] == 1.0


def test_wrong_time_inside_a_timestamp_still_fails():
    out = call("logs_query_range", {
        "service": "checkout", "level": "error",
        "start_time": "2023-02-20T10:00:00.000Z", "end_time": "2023-02-20T09:30:00.000Z"})
    assert score_case(out, TIME_EXPECTED)["score"] == 0.0


def test_date_only_expectations_stay_strict():
    """The analytics family expects real dates from the query; the time
    leniency must not spill over into accepting the wrong date."""
    date_expected = {
        "correct_tool_name": "analytics_count_events",
        "expected_args": {"start_date": ["2025-03-03"], "end_date": ["2025-03-09"]},
        "near_miss_names": [],
    }
    ok = call("analytics_count_events", {"start_date": "2025-03-03", "end_date": "2025-03-09"})
    assert score_case(ok, date_expected)["score"] == 1.0
    bad = call("analytics_count_events", {"start_date": "2025-04-03", "end_date": "2025-03-09"})
    assert score_case(bad, date_expected)["score"] == 0.0


@pytest.mark.parametrize("got,accepted,expected", [
    (64.5, [64.5], True),
    ("$64.50", [64.5], True),
    ("reader", ["reader", "read"], True),
    ("READER ", ["reader"], True),
    (True, [1], False),          # bool must not satisfy a numeric expectation
    (None, ["reader"], False),
])
def test_value_matches_table(got, accepted, expected):
    assert value_matches(got, accepted) is expected
