# debug_royalty_pipeline — Multi-Source Data Debugging

An open-source evaluation task for **multi-file consistency debugging** — when a change to a data pipeline requires synchronised edits across multiple tables or columns, does the agent find ALL the places that need updating?

Useful for evaluating agents that maintain data pipelines, do schema migrations, or modify code + data together — the class of task where "I changed one thing and now half my reports are wrong."

## What this task tests

**Given a ticket asking for a change to a royalty accounting pipeline, does the agent produce the correct MINIMAL set of edits so BOTH downstream reports come out consistent?**

Real debugging failure modes exposed:

1. **Fixed the primary table, forgot the auxiliary** — a SKU exists in both `catalog.csv` and `enterprise_deals.csv`; if only one gets updated, reports mix old and new values for the same SKU.
2. **Fixed one column, forgot the paired column** — SKU codes follow a per-publisher naming convention; changing the publisher without also changing the SKU leaves the two reports mutually inconsistent.
3. **Modified an existing row when should have inserted new** — a dated change (effective from 2024-06-01) should ADD a new catalog row, not overwrite the old row.
4. **Modified only percentage, forgot to null-out fixed field** — royalty type transitions require BOTH clearing the old field AND setting the new one.

## Case structure: 4 cases × 4 trap types

| Case | Trap | Fix requires |
|---|---|---|
| **case_01** | Publisher swap (all-time) | Update **BOTH** `publisher_id` and `sku` in the same catalog row |
| **case_02** | Publisher swap effective-from date | **Insert** a new catalog row (historical transactions must stay attributed to old publisher) |
| **case_03** | Royalty pct → fixed, SKU only in catalog | Update catalog: null out pct, set fixed |
| **case_04** | Royalty pct → fixed, SKU also in enterprise_deals | Update **BOTH** catalog **AND** enterprise_deals |

## Input

Per case (`inputs/<case_id>/`):
- `README.md` — task instructions (data schema, business rules, output format)
- `ticket.md` — the change request
- `catalog.csv`, `enterprise_deals.csv`, `publishers.csv`, `transactions.csv` — data
- `publisher_statement.py`, `itemised_statement.py` — report scripts (agent reads to understand data flow)

## Expected output

A JSON array of edits (nothing else):

```json
[
  {"file": "catalog.csv", "op": "update", "match": {"product_id": "PID-042"}, "set": {"publisher_id": "MG", "sku": "MED-042-MG"}},
  {"file": "catalog.csv", "op": "insert", "row": {"product_id": "PID-107", "sku": "MED-107-MG", "publisher_id": "MG", "royalty_pct": 0.70, "royalty_fixed_usd": null, "effective_from": "2024-06-01"}}
]
```

## Scoring

Judge parses agent's stdout as a JSON list, canonicalises each edit, and compares to gold edit set:

**Score is 1.0 only if:**
- Every gold edit has a matching agent edit AND
- Agent has NO extra unnecessary edits (anti-shotgun)

**Match tolerance:** agent's `match` dict may include MORE fields than gold's (over-specification of the match is fine as long as agent's dict is a superset of gold's), but the `set` values must match exactly.

**Score is 0.0 if:** missing gold edit, or extra unnecessary edit, or output isn't valid JSON.

## Why extras count against the agent

An agent that "carpet bombs" the change across every plausible table/column would trivially pass "did you cover it." The real skill is **finding the MINIMAL correct edit set**. Bloating the change surface in a real pipeline creates its own bugs (schema churn, extra rows breaking assumptions, harder rollback).

## Business rules encoded in the scripts

Read `publisher_statement.py` and `itemised_statement.py` for exact logic. Key rules:

- **Enterprise deals precedence**: For `channel='enterprise'` transactions, if the product exists in `enterprise_deals.csv`, that row's terms take precedence over `catalog.csv`. (Makes case_04 a real trap.)
- **Effective-date routing**: `catalog.csv` can have multiple rows per `product_id` with different `effective_from` dates. Scripts pick the row with the largest `effective_from` <= transaction's `sale_date`. (Makes case_02 an insert, not an update.)
- **Royalty amount**: If `royalty_pct` populated, royalty = `revenue * pct`. If `royalty_fixed_usd` populated, royalty = fixed per transaction. Only ONE should be populated.
- **SKU per publisher**: SKUs follow `MED-nnn-XX` where `XX` is the publisher's 2-letter code. Publisher change → SKU updates.

## Measured baseline (2026-07-10)

| Model | Score | Cost |
|---|---|---|
| Haiku 4.5 | 3/4 = 75% | ~$0.03 |
| Sonnet 4.6 | 4/4 = 100% | ~$0.08 |
| Opus 4.8 | 4/4 = 100% | ~$0.60 |

Haiku's failure mode: on the dated-swap case (case_02), it used `update` instead of `insert`, which would retroactively re-attribute historical transactions. That's the exact real-world trap this task tests.

## Cost

4 small cases, ~2-4k input tokens per case. Full run: **$0.03-$0.60 depending on model**.

## Honest limitations

- **4 cases is a small sample.** Production version should have 10-15+ cases across multiple variants of each trap type.
- **Scripts are read-only reference.** Judge doesn't execute the pipeline — it compares edit lists structurally. Agent can't verify by running; must reason from the code.
- **Fully synthetic domain.** Scenarios inspired by real production royalty pipelines but no real-world credibility signal.
- **Anti-shotgun is strict.** 3 correct edits + 1 harmless extra = 0. No partial credit.
- **Match tolerance is limited.** Agent can over-specify match fields, but must include gold's required identifiers.

## Data source & license

All code, data, and scenarios are **synthetic**, hand-authored for this task. See [LICENSE.md](LICENSE.md).

## Run

```bash
python3 build_cases.py                     # (re)generate inputs/ + expected/
python3 -m pytest tests/ -v                # unit tests
```
