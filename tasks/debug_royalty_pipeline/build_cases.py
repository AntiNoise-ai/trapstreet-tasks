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
VALID_FILES = {"catalog.csv", "suppliers.csv", "transactions.csv"}
REQUIRED_TABLES = ("suppliers", "catalog", "transactions")

CATALOG_COLS = ["product_id", "sku", "product_name", "supplier_id", "royalty_pct", "royalty_fixed_usd", "effective_from"]
SUPPLIERS_COLS = ["supplier_id", "supplier_name"]
TXN_COLS = ["transaction_id", "product_id", "channel", "sku", "supplier_name", "sale_date", "revenue_usd", "royalty_pct", "royalty_fixed_usd"]


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

    for row in data["catalog"]:
        for col in CATALOG_COLS:
            if col not in row:
                raise ValueError(f"case {case['id']}: catalog row missing column {col!r}: {row}")
    for row in data["suppliers"]:
        for col in SUPPLIERS_COLS:
            if col not in row:
                raise ValueError(f"case {case['id']}: suppliers row missing column {col!r}: {row}")

    sids = {s["supplier_id"] for s in data["suppliers"]}
    for row in data["catalog"]:
        if row["supplier_id"] not in sids:
            raise ValueError(f"case {case['id']}: catalog references unknown supplier_id {row['supplier_id']!r}")

    for row in data["transactions"]:
        for col in TXN_COLS:
            if col not in row:
                raise ValueError(f"case {case['id']}: transaction row missing column {col!r}: {row}")
        if row["channel"] not in ("retail", "b2b"):
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

A colleague filed a ticket asking for a change to the royalty pipeline. Read the ticket, the data files, and the two report scripts. Figure out EXACTLY which edits are needed so both reports (`publisher_statement.py` and `itemised_statement.py`) come out correct.

## Files in this directory

- `ticket.md` — the change request
- `catalog.csv`, `suppliers.csv`, `transactions.csv` — data tables
- `publisher_statement.py`, `itemised_statement.py` — the two report scripts

## Output format

Emit a JSON array of edits to stdout. Nothing else — no explanation, no markdown fences.

Each edit is one of:

```
{"file": "<name>.csv", "op": "update", "match": {"<col>": "<value>"}, "set": {"<col>": <value>, ...}}
{"file": "<name>.csv", "op": "insert", "row": {"<col>": <value>, ...}}
```

For updates: `match` specifies which rows to change (all matching rows are affected); `set` specifies which columns to update to which values.
For inserts: `row` is the new row to add (include all columns for that table).
Use `null` (JSON literal) for empty values.

## Scoring

Your list of edits is compared to the gold edit set. Score 1.0 only if every gold edit is present AND there are no extra edits. **Extras count against you** — do not list every possibly-related edit; list only what is necessary.

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

        write_csv(in_dir / "catalog.csv", CATALOG_COLS, case["data"]["catalog"])
        write_csv(in_dir / "suppliers.csv", SUPPLIERS_COLS, case["data"]["suppliers"])
        write_csv(in_dir / "transactions.csv", TXN_COLS, case["data"]["transactions"])

        (in_dir / "ticket.md").write_text(f"# Ticket\n\n{case['ticket']}\n", encoding="utf-8")
        (in_dir / "README.md").write_text(AGENT_INSTRUCTIONS, encoding="utf-8")

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
