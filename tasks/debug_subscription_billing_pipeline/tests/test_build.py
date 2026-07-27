# tests/test_build.py
import json
import sys
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_cases  # noqa: E402


def _valid_case():
    return {
        "id": "case_test",
        "category": "unit_test",
        "ticket": "Do the thing.",
        "data": {
            "customers": [
                {"customer_id": "CUST-X", "customer_name": "Test Co",
                 "region_id": "REG-CA", "signup_date": "2024-01-01"},
            ],
            "subscriptions": [
                {"subscription_id": "SUB-X", "customer_id": "CUST-X",
                 "plan_id": "PLAN-STARTER", "addon_ids": "ADDON-SSO",
                 "discount_code": "", "status": "active", "start_date": "2024-01-01"},
            ],
            "plans": [
                {"plan_id": "PLAN-STARTER", "plan_name": "Starter Monthly",
                 "tier_id": "TIER-STARTER", "base_price_usd": 29.0},
            ],
            "tiers": [
                {"tier_id": "TIER-STARTER", "tier_name": "Starter", "seat_limit": 5},
            ],
            "addons": [
                {"addon_id": "ADDON-SSO", "addon_name": "Single Sign-On", "addon_price_usd": 49.0},
            ],
            "discount_codes": [
                {"code": "WELCOME10", "discount_pct": 0.10, "discount_fixed_usd": None, "expires_on": "2099-12-31"},
            ],
            "regions": [
                {"region_id": "REG-CA", "region_name": "California", "tax_rate_pct": 8.5},
            ],
            "invoices": [
                {"invoice_id": "INV-X", "subscription_id": "SUB-X", "period": "2024-01",
                 "baked_customer_name": "Test Co", "baked_plan_name": "Starter Monthly",
                 "baked_addon_names": "Single Sign-On", "baked_base_price_usd": 29.0,
                 "baked_addon_total_usd": 49.0, "baked_discount_applied_usd": 0.0,
                 "baked_tax_usd": 6.63, "baked_total_usd": 84.63, "status": "paid"},
            ],
            "support_tickets": [],
            "marketing_campaigns": [],
        },
        "gold_edits": [
            {"file": "customers.csv", "op": "update",
             "match": {"customer_id": "CUST-X"}, "set": {"region_id": "REG-CA"}},
        ],
    }


def test_valid_case_passes():
    build_cases.validate_case(_valid_case())  # should not raise


def test_missing_top_level_field_rejected():
    case = _valid_case()
    del case["ticket"]
    with pytest.raises(ValueError, match="missing field"):
        build_cases.validate_case(case)


def test_empty_ticket_rejected():
    case = _valid_case()
    case["ticket"] = "   "
    with pytest.raises(ValueError, match="empty ticket"):
        build_cases.validate_case(case)


def test_missing_table_rejected():
    case = _valid_case()
    del case["data"]["regions"]
    with pytest.raises(ValueError, match="missing table"):
        build_cases.validate_case(case)


def test_row_missing_column_rejected():
    case = _valid_case()
    del case["data"]["customers"][0]["signup_date"]
    with pytest.raises(ValueError, match="missing column"):
        build_cases.validate_case(case)


def test_customer_unknown_region_rejected():
    case = _valid_case()
    case["data"]["customers"][0]["region_id"] = "REG-NOWHERE"
    with pytest.raises(ValueError, match="unknown region_id"):
        build_cases.validate_case(case)


def test_plan_unknown_tier_rejected():
    case = _valid_case()
    case["data"]["plans"][0]["tier_id"] = "TIER-NOWHERE"
    with pytest.raises(ValueError, match="unknown tier_id"):
        build_cases.validate_case(case)


def test_subscription_unknown_customer_rejected():
    case = _valid_case()
    case["data"]["subscriptions"][0]["customer_id"] = "CUST-NOWHERE"
    with pytest.raises(ValueError, match="unknown customer_id"):
        build_cases.validate_case(case)


def test_subscription_unknown_plan_rejected():
    case = _valid_case()
    case["data"]["subscriptions"][0]["plan_id"] = "PLAN-NOWHERE"
    with pytest.raises(ValueError, match="unknown plan_id"):
        build_cases.validate_case(case)


def test_subscription_unknown_addon_rejected():
    case = _valid_case()
    case["data"]["subscriptions"][0]["addon_ids"] = "ADDON-NOWHERE"
    with pytest.raises(ValueError, match="unknown addon_id"):
        build_cases.validate_case(case)


def test_invoice_unknown_subscription_rejected():
    case = _valid_case()
    case["data"]["invoices"][0]["subscription_id"] = "SUB-NOWHERE"
    with pytest.raises(ValueError, match="unknown subscription_id"):
        build_cases.validate_case(case)


def test_gold_edit_invalid_file_rejected():
    case = _valid_case()
    case["gold_edits"][0]["file"] = "not_a_real_table.csv"
    with pytest.raises(ValueError, match="invalid file"):
        build_cases.validate_case(case)


def test_gold_edit_invalid_op_rejected():
    case = _valid_case()
    case["gold_edits"][0]["op"] = "delete"
    with pytest.raises(ValueError, match="invalid op"):
        build_cases.validate_case(case)


def test_gold_edit_update_missing_set_rejected():
    case = _valid_case()
    del case["gold_edits"][0]["set"]
    with pytest.raises(ValueError, match="needs 'match' and 'set'"):
        build_cases.validate_case(case)


def test_gold_edit_insert_missing_row_rejected():
    case = _valid_case()
    case["gold_edits"][0] = {"file": "customers.csv", "op": "insert"}
    with pytest.raises(ValueError, match="needs 'row'"):
        build_cases.validate_case(case)


def test_real_gold_cases_json_all_valid():
    """The actual gold.cases.json shipped with this task must validate cleanly."""
    gold = json.loads((ROOT / "gold.cases.json").read_text())
    ids = set()
    for case in gold["cases"]:
        build_cases.validate_case(case)
        assert case["id"] not in ids, f"duplicate case id {case['id']}"
        ids.add(case["id"])
    assert len(ids) == 6
