# debug_royalty_pipeline — Multi-Source Consistency Debugging

An open-source evaluation task for **cross-file consistency debugging** — when a ticket asks for a change to a data pipeline, does the agent identify ALL the places that need updating so that TWO reports (with DIFFERENT lookup paths) both come out correct?

Useful for evaluating agents that maintain data pipelines, do schema migrations, or fix data + code together — the class of task where "I changed one thing and now half my reports are wrong."

## What this task tests

**Given a ticket asking for a change to a royalty accounting pipeline, does the agent produce the correct MINIMAL edit set so BOTH reports come out consistent?**

The two reports use DIFFERENT lookup paths for the same conceptual data:
- **`publisher_statement.py`** — uses LOOKUP: `catalog[product_id] → suppliers[supplier_id] → supplier_name`. Aggregates revenue and royalty by supplier.
- **`itemised_statement.py`** — uses BAKED text: reads `transactions.supplier_name` and `transactions.sku` DIRECTLY (recorded at time of sale, no lookup).

Because the two reports read supplier from different sources, a supplier change requires TWO edits (one for each lookup path). This is the core trap — agent reading only ONE report's code won't find it.

## Case structure: 4 cases × 4 trap types

| Case | Trap | Fix requires |
|---|---|---|
| **case_01** | Change supplier for a SKU (all-time) | catalog.supplier_id (fixes publisher_statement via lookup) + transactions.supplier_name (fixes itemised via baked text) |
| **case_02** | Change supplier from a specific date onward | INSERT new catalog row + UPDATE only transactions after the date |
| **case_03** | Change royalty pct→fixed, SKU has retail only | catalog.royalty_pct/fixed (both reports use catalog for retail royalty) |
| **case_04** | Change royalty pct→fixed, SKU has retail+b2b transactions | catalog + transactions (b2b rows have BAKED royalty terms; must update both) |

## Data schema

- `catalog.csv` — product master. Columns: `product_id, sku, supplier_id, royalty_pct, royalty_fixed_usd, effective_from`. Can have multiple rows per product_id for effective-date routing.
- `suppliers.csv` — supplier registry. Columns: `supplier_id, supplier_name`.
- `transactions.csv` — sales log with BAKED fields. Columns: `transaction_id, product_id, channel, sku, supplier_name, sale_date, revenue_usd, royalty_pct, royalty_fixed_usd`. Retail rows have null royalty_pct/fixed (use catalog); b2b rows have BAKED royalty terms.

## Script behavior

### `publisher_statement.py`
For each transaction:
- Supplier via LOOKUP: `catalog[product_id].supplier_id → suppliers[supplier_id].supplier_name`
- Royalty: retail uses catalog terms, b2b uses transaction's BAKED terms
- Aggregate by supplier_name

### `itemised_statement.py`
For each transaction:
- SKU and supplier_name from transaction DIRECTLY (BAKED text)
- Royalty: same as publisher_statement (retail from catalog, b2b from transaction BAKED)
- Per-row output

## Input

Per case (`inputs/<case_id>/`):
- `README.md` — task instructions + output format
- `ticket.md` — the change request
- `catalog.csv`, `suppliers.csv`, `transactions.csv` — data tables
- `publisher_statement.py`, `itemised_statement.py` — report scripts

## Expected output

A JSON array of edits:

```json
[
  {"file": "catalog.csv", "op": "update", "match": {"product_id": "PID-042"}, "set": {"supplier_id": "MG"}},
  {"file": "transactions.csv", "op": "update", "match": {"product_id": "PID-042"}, "set": {"supplier_name": "Meridian Group"}}
]
```

Or:
```json
[
  {"file": "catalog.csv", "op": "insert", "row": {"product_id": "PID-107", "sku": "MED-107-BW", "supplier_id": "MG", "royalty_pct": 0.70, "royalty_fixed_usd": null, "effective_from": "2024-06-01"}}
]
```

## Scoring — data-aware equivalence

Judge applies BOTH agent's edits AND gold's edits to the initial input tables, then compares the resulting states row-by-row. Score is 1.0 only if resulting states are IDENTICAL.

**This means agent has flexibility in HOW to express edits:**
- Can match by `product_id` OR `sku` OR `transaction_id` (as long as it uniquely identifies the same row)
- Can use `set: {supplier_id: "MG"}` alone OR bundle multiple field updates in one edit
- Order of edits doesn't matter

**What agent CAN'T get away with:**
- Missing updates that gold requires (any table row differs from expected)
- Adding updates that gold didn't require (any table row differs from expected)
- Over-matching (e.g., updating ALL rows when only some should change)

## Why extras count against the agent

An agent that carpet-bombs the change across every plausible table/column would pass "did you cover it" checks trivially. The real skill is **the MINIMAL correct edit set** — bloating the change surface in a real pipeline creates its own bugs.

## Measured baseline (2026-07-10, sparse tickets + data-aware judge)

| Model | Score | Cost | Failure mode |
|---|---|---|---|
| Haiku 4.5 | 3/4 | ~$0.01 | Misses `case_04`: doesn't update b2b transactions' baked royalty terms |
| Sonnet 4.6 | 3/4 | ~$0.06 | Over-edits `case_03`: adds unnecessary royalty updates to retail transactions |
| Opus 4.8 | 4/4 | ~$0.36 | — |

Each model fails a different case, exposing different real gaps in cross-file consistency reasoning.

## Cost

4 small cases, ~2-4k input tokens per case. Full run: **$0.03-$0.60 depending on model**.

## Honest limitations

- **4 cases is a small sample.** Production version should have 10-15+ cases across multiple variants of each trap type.
- **Scripts are read-only reference.** Judge doesn't execute the pipeline; it compares resulting table states. Agent can't verify by running; must reason from the code.
- **Fully synthetic domain.** Scenarios inspired by real production royalty pipelines but no proprietary code or data.
- **Sparse instructions.** The task README does not describe business rules (SKU convention, lookup semantics, etc). Agent must infer these from reading the scripts.

## Data source & license

All code, data, scenarios are **synthetic**, hand-authored for this task. See [LICENSE.md](LICENSE.md).

## Run

```bash
python3 build_cases.py                     # (re)generate inputs/ + expected/
python3 -m pytest tests/ -v                # unit tests
```
