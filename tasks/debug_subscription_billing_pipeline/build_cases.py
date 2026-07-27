"""Generate inputs/<id>/... and expected/<id>/answer.json from
gold.cases.json, validating authoring invariants first.

Run:  python3 build_cases.py
inputs/ and expected/ are GENERATED -- never edit them by hand.
"""
from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOLD = HERE / "gold.cases.json"
SHARED_SCRIPTS = HERE / "shared_scripts"

VALID_OPS = {"update", "insert"}
VALID_FILES = {
    "customers.csv", "subscriptions.csv", "plans.csv", "tiers.csv",
    "addons.csv", "discount_codes.csv", "regions.csv", "invoices.csv",
}
REQUIRED_TABLES = ("customers", "subscriptions", "plans", "tiers", "addons",
                    "discount_codes", "regions", "invoices",
                    "support_tickets", "marketing_campaigns")

CUSTOMERS_COLS = ["customer_id", "customer_name", "region_id", "signup_date"]
SUBSCRIPTIONS_COLS = ["subscription_id", "customer_id", "plan_id", "addon_ids",
                       "discount_code", "status", "start_date"]
PLANS_COLS = ["plan_id", "plan_name", "tier_id", "base_price_usd"]
TIERS_COLS = ["tier_id", "tier_name", "seat_limit"]
ADDONS_COLS = ["addon_id", "addon_name", "addon_price_usd"]
DISCOUNT_CODES_COLS = ["code", "discount_pct", "discount_fixed_usd", "expires_on"]
REGIONS_COLS = ["region_id", "region_name", "tax_rate_pct"]
INVOICES_COLS = ["invoice_id", "subscription_id", "period", "baked_customer_name",
                  "baked_plan_name", "baked_addon_names", "baked_base_price_usd",
                  "baked_addon_total_usd", "baked_discount_applied_usd",
                  "baked_tax_usd", "baked_total_usd", "status"]
SUPPORT_TICKETS_COLS = ["ticket_id", "customer_id", "subject", "opened_on"]
MARKETING_CAMPAIGNS_COLS = ["campaign_id", "region_id", "campaign_name", "start_date"]

TABLE_COLS = {
    "customers": CUSTOMERS_COLS, "subscriptions": SUBSCRIPTIONS_COLS,
    "plans": PLANS_COLS, "tiers": TIERS_COLS, "addons": ADDONS_COLS,
    "discount_codes": DISCOUNT_CODES_COLS, "regions": REGIONS_COLS,
    "invoices": INVOICES_COLS, "support_tickets": SUPPORT_TICKETS_COLS,
    "marketing_campaigns": MARKETING_CAMPAIGNS_COLS,
}
TABLE_FILENAME = {
    "customers": "customers.csv", "subscriptions": "subscriptions.csv",
    "plans": "plans.csv", "tiers": "tiers.csv", "addons": "addons.csv",
    "discount_codes": "discount_codes.csv", "regions": "regions.csv",
    "invoices": "invoices.csv", "support_tickets": "support_tickets.csv",
    "marketing_campaigns": "marketing_campaigns.csv",
}


def validate_case(case: dict) -> None:
    for field in ("id", "category", "ticket", "data", "gold_edits"):
        if field not in case:
            raise ValueError(f"case {case.get('id', '<no-id>')}: missing field {field!r}")
    if not case["ticket"].strip():
        raise ValueError(f"case {case['id']}: empty ticket")

    data = case["data"]
    for table in REQUIRED_TABLES:
        if table not in data:
            raise ValueError(f"case {case['id']}: missing table {table!r}")
        for row in data[table]:
            for col in TABLE_COLS[table]:
                if col not in row:
                    raise ValueError(f"case {case['id']}: {table} row missing column {col!r}: {row}")

    region_ids = {r["region_id"] for r in data["regions"]}
    tier_ids = {r["tier_id"] for r in data["tiers"]}
    plan_ids = {r["plan_id"] for r in data["plans"]}
    addon_ids = {r["addon_id"] for r in data["addons"]}
    customer_ids = {r["customer_id"] for r in data["customers"]}
    subscription_ids = {r["subscription_id"] for r in data["subscriptions"]}

    for row in data["customers"]:
        if row["region_id"] not in region_ids:
            raise ValueError(f"case {case['id']}: customer {row['customer_id']} references unknown region_id {row['region_id']!r}")
    for row in data["plans"]:
        if row["tier_id"] not in tier_ids:
            raise ValueError(f"case {case['id']}: plan {row['plan_id']} references unknown tier_id {row['tier_id']!r}")
    for row in data["subscriptions"]:
        if row["customer_id"] not in customer_ids:
            raise ValueError(f"case {case['id']}: subscription {row['subscription_id']} references unknown customer_id {row['customer_id']!r}")
        if row["plan_id"] not in plan_ids:
            raise ValueError(f"case {case['id']}: subscription {row['subscription_id']} references unknown plan_id {row['plan_id']!r}")
        for aid in (row.get("addon_ids") or "").split(";"):
            aid = aid.strip()
            if aid and aid not in addon_ids:
                raise ValueError(f"case {case['id']}: subscription {row['subscription_id']} references unknown addon_id {aid!r}")
    for row in data["invoices"]:
        if row["subscription_id"] not in subscription_ids:
            raise ValueError(f"case {case['id']}: invoice {row['invoice_id']} references unknown subscription_id {row['subscription_id']!r}")

    for edit in case["gold_edits"]:
        for field in ("file", "op"):
            if field not in edit:
                raise ValueError(f"case {case['id']}: gold_edit missing {field!r}: {edit}")
        if edit["file"] not in VALID_FILES:
            raise ValueError(f"case {case['id']}: gold_edit references invalid file {edit['file']!r}")
        if edit["op"] not in VALID_OPS:
            raise ValueError(f"case {case['id']}: gold_edit has invalid op {edit['op']!r}")
        if edit["op"] == "update":
            if "match" not in edit or "set" not in edit:
                raise ValueError(f"case {case['id']}: update edit needs 'match' and 'set': {edit}")
        elif edit["op"] == "insert":
            if "row" not in edit:
                raise ValueError(f"case {case['id']}: insert edit needs 'row': {edit}")


def write_csv(path: Path, cols: list, rows: list) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for row in rows:
            r = {c: ("" if row.get(c) is None else row.get(c)) for c in cols}
            w.writerow(r)


AGENT_INSTRUCTIONS = """# Task

A colleague filed a ticket asking for a change to the subscription billing pipeline.

**Your goal:** ensure all FOUR reports (`billing_summary.py`, `invoice_detail.py`, `finance_ledger.py`, `customer_statement.py`) come out CORRECT after the fix is applied.

You will not be graded on your intermediate reasoning or on the structure of your edits. You will be graded on **whether the reports these four scripts produce match the reports they would produce after a correct fix**. The judge applies your edits, runs all four scripts, and compares stdout to the gold reports.

## Business context

This is a SaaS company's subscription billing system. Customers subscribe to plans (which belong to tiers), can add optional add-ons, and may have a discount code applied. Each billing period an invoice is generated and its financial fields are BAKED into `invoices.csv` at that point in time -- they are a historical record, not something that gets silently recomputed later.

The four reports read the same underlying facts through DIFFERENT paths:
- `billing_summary.py` -- LIVE: "if we billed today," fully resolved from current customers/plans/tiers/addons/discount_codes/regions. No invoice history involved.
- `invoice_detail.py` -- pure BAKED: reads `invoices.csv`'s own columns directly, no lookups at all. This is the historical record customers see.
- `finance_ledger.py` -- MIXED: pretax subtotal always from baked invoice columns; tax is baked-tax-if-present, else a LIVE fallback lookup (invoice -> subscription -> customer -> region).
- `customer_statement.py` -- MIXED differently: base price stays BAKED (grandfather pricing), but add-on names/prices, discount, and tax are all resolved LIVE against current tables.

Because each report resolves differently, the SAME underlying change can require touching different combinations of files. A change to "current state" tables (plans/addons/discount_codes/customers) flows automatically into the two LIVE reports. A change that must also correct HISTORICAL invoices requires directly editing the affected row(s) in `invoices.csv` -- and only the affected row(s); untouched historical invoices must stay untouched.

## How to approach this

- The data tables are meant to be read in full, but do not touch rows the ticket doesn't call for -- edits to invoices outside the ticket's stated scope will be scored as incorrect, even if well-intentioned.
- Read all four report scripts to understand exactly which table/column each one reads and whether that path is baked, live, or a fallback of one to the other.
- If a ticket changes a rate/price/code definition, decide: does this only affect the live view going forward, or does a specific historical invoice also need its baked figures corrected?

## Files in this directory

- `ticket.md` -- the change request
- `customers.csv`, `subscriptions.csv`, `plans.csv`, `tiers.csv`, `addons.csv`, `discount_codes.csv`, `regions.csv` -- current-state master tables
- `invoices.csv` -- historical baked invoice records
- `support_tickets.csv`, `marketing_campaigns.csv` -- unrelated auxiliary tables (not used by any report)
- `billing_summary.py`, `invoice_detail.py`, `finance_ledger.py`, `customer_statement.py` -- the four report scripts

## Output format

Emit a JSON array of edits to stdout. Nothing else -- no explanation, no markdown fences.

Each edit is one of:

```
{"file": "<name>.csv", "op": "update", "match": {"<col>": "<value>"}, "set": {"<col>": <value>, ...}}
{"file": "<name>.csv", "op": "insert", "row": {"<col>": <value>, ...}}
```

For updates: `match` specifies which rows to change; `set` specifies which columns to update to which values.
For inserts: `row` is the new row to add (include all columns for that table).
Use `null` (JSON literal) for empty values.

Only your first 30 edits will be applied by the judge -- padding the list with extra guesses past that point does not help.

Output ONLY the JSON array.
"""


def build() -> None:
    data = json.loads(GOLD.read_text())
    seen_ids: set[str] = set()
    for case in data["cases"]:
        validate_case(case)
        cid = case["id"]
        if cid in seen_ids:
            raise ValueError(f"duplicate case id: {cid}")
        seen_ids.add(cid)

        in_dir = HERE / "inputs" / cid
        in_dir.mkdir(parents=True, exist_ok=True)

        for table, filename in TABLE_FILENAME.items():
            write_csv(in_dir / filename, TABLE_COLS[table], case["data"][table])

        (in_dir / "ticket.md").write_text(f"# Ticket\n\n{case['ticket']}\n", encoding="utf-8")
        (in_dir / "README.md").write_text(AGENT_INSTRUCTIONS, encoding="utf-8")

        for script in ("billing_summary.py", "invoice_detail.py",
                       "finance_ledger.py", "customer_statement.py"):
            src = SHARED_SCRIPTS / script
            if src.exists():
                shutil.copy(src, in_dir / script)

        exp_dir = HERE / "expected" / cid
        exp_dir.mkdir(parents=True, exist_ok=True)
        (exp_dir / "answer.json").write_text(json.dumps({
            "id": cid,
            "category": case["category"],
            "gold_edits": case["gold_edits"],
        }, indent=2), encoding="utf-8")

    print(f"Built {len(data['cases'])} cases.")


if __name__ == "__main__":
    build()
