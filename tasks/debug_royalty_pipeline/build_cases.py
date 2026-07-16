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
VALID_FILES = {"catalog.csv", "enterprise_deals.csv", "publishers.csv"}
REQUIRED_TABLES = ("publishers", "catalog", "enterprise_deals", "transactions")
CATALOG_COLS = ["product_id", "sku", "publisher_id", "royalty_pct", "royalty_fixed_usd", "effective_from"]
PUBLISHERS_COLS = ["publisher_id", "publisher_name"]
ENTERPRISE_COLS = ["product_id", "sku", "publisher_id", "publisher_name", "royalty_pct", "royalty_fixed_usd"]
TXN_COLS = ["transaction_id", "product_id", "channel", "sale_date", "revenue_usd"]


def validate_case(case: dict) -> None:
    """Fail loudly on authoring mistakes."""
    for field in ("id", "category", "ticket", "data", "gold_edits"):
        if field not in case:
            raise ValueError(f"case {case.get('id', '<no-id>')}: missing field {field!r}")

    if not case["ticket"].strip():
        raise ValueError(f"case {case['id']}: empty ticket")

    data = case["data"]
    for table in REQUIRED_TABLES:
        if table not in data:
            raise ValueError(f"case {case['id']}: missing data table {table!r}")

    for row in data["catalog"]:
        for col in CATALOG_COLS:
            if col not in row:
                raise ValueError(f"case {case['id']}: catalog row missing column {col!r}: {row}")

    for row in data["publishers"]:
        for col in PUBLISHERS_COLS:
            if col not in row:
                raise ValueError(f"case {case['id']}: publishers row missing column {col!r}: {row}")

    pids = {p["publisher_id"] for p in data["publishers"]}
    for row in data["catalog"]:
        if row["publisher_id"] not in pids:
            raise ValueError(f"case {case['id']}: catalog row references unknown publisher_id {row['publisher_id']!r}")

    for row in data["enterprise_deals"]:
        for col in ENTERPRISE_COLS:
            if col not in row:
                raise ValueError(f"case {case['id']}: enterprise_deals row missing column {col!r}: {row}")
        if row["publisher_id"] not in pids:
            raise ValueError(f"case {case['id']}: enterprise row references unknown publisher_id {row['publisher_id']!r}")

    for row in data["transactions"]:
        for col in TXN_COLS:
            if col not in row:
                raise ValueError(f"case {case['id']}: transaction row missing column {col!r}: {row}")
        if row["channel"] not in ("retail", "enterprise"):
            raise ValueError(f"case {case['id']}: unknown channel {row['channel']!r}")

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

You are a data engineer working on a royalty accounting pipeline.

A colleague has filed a ticket asking for a change. Your job:

1. Read `ticket.md` to understand the change request.
2. Read the data tables (`catalog.csv`, `enterprise_deals.csv`, `publishers.csv`, `transactions.csv`) and the report scripts (`publisher_statement.py`, `itemised_statement.py`) to understand how data flows into the two reports.
3. Determine EXACTLY which edits are needed so that BOTH reports (`publisher_statement.py` and `itemised_statement.py`) correctly reflect the change.

## Data schema

- `catalog.csv` — master product catalog. Columns: `product_id, sku, publisher_id, royalty_pct, royalty_fixed_usd, effective_from`
- `enterprise_deals.csv` — B2B contract overrides for SOME products. Columns: `product_id, sku, publisher_id, publisher_name, royalty_pct, royalty_fixed_usd`. When a transaction's `channel` is `enterprise` AND its `product_id` exists in this table, this row's terms are used instead of the catalog's.
- `publishers.csv` — publisher master. Columns: `publisher_id, publisher_name`
- `transactions.csv` — sales log. Columns: `transaction_id, product_id, channel, sale_date, revenue_usd`

## Business rules to keep in mind

- **SKU per publisher**: SKUs follow the naming convention `MED-nnn-XX` where `XX` is the publisher's 2-letter code. If a product's publisher changes, the SKU convention says it should also change to reflect the new publisher.
- **Effective date routing**: The catalog can have multiple rows for the same `product_id` with different `effective_from` dates. Scripts pick the row with the largest `effective_from` value that is <= the transaction's `sale_date`.
- **Royalty amount computation**: If `royalty_pct` is populated, royalty = revenue * pct. If `royalty_fixed_usd` is populated, royalty = fixed amount (per transaction). Only ONE of the two should be populated at a time.
- **Enterprise deals precedence**: For enterprise channel transactions, if the product is in `enterprise_deals.csv`, that row's terms take precedence over the catalog.

## Output format

Emit a JSON array of edits to stdout. Nothing else — no explanation, no markdown fences.

Each edit is one of:

```json
{"file": "catalog.csv", "op": "update", "match": {"product_id": "PID-XYZ"}, "set": {"publisher_id": "MG", "sku": "MED-XYZ-MG"}}
```

or

```json
{"file": "catalog.csv", "op": "insert", "row": {"product_id": "PID-XYZ", "sku": "MED-XYZ-MG", "publisher_id": "MG", "royalty_pct": 0.70, "royalty_fixed_usd": null, "effective_from": "2024-06-01"}}
```

For updates: `match` specifies WHICH rows to change (all matching rows are affected); `set` specifies WHICH columns to update to WHICH values.

For inserts: `row` is the new row to add (must include all columns for that table).

Use `null` (JSON literal) for empty values.

## Scoring

Your list of edits will be compared to the gold-standard edit set. To score 1.0:
- Every gold edit must have a matching edit in your list
- You must NOT include any extra edits beyond what's needed

**Anti-shotgun:** Extra edits DO count against you. Do not list every possibly-related edit; list only what's necessary.

Output ONLY the JSON array. No preamble, no explanation, no markdown fences.
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

        # Write data CSVs
        write_csv(in_dir / "catalog.csv", CATALOG_COLS, case["data"]["catalog"])
        write_csv(in_dir / "enterprise_deals.csv", ENTERPRISE_COLS, case["data"]["enterprise_deals"])
        write_csv(in_dir / "publishers.csv", PUBLISHERS_COLS, case["data"]["publishers"])
        write_csv(in_dir / "transactions.csv", TXN_COLS, case["data"]["transactions"])

        # Write ticket + instructions
        (in_dir / "ticket.md").write_text(f"# Ticket\n\n{case['ticket']}\n", encoding="utf-8")
        (in_dir / "README.md").write_text(AGENT_INSTRUCTIONS, encoding="utf-8")

        # Copy shared scripts
        for script in ("publisher_statement.py", "itemised_statement.py"):
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
