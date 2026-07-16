# Task

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
