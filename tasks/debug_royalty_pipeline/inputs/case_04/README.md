# Task

A colleague filed a ticket asking for a fix to the royalty pipeline.

**Your goal:** ensure both reports (`publisher_statement.py` and `itemised_statement.py`) come out CORRECT after the fix is applied.

You will not be graded on your intermediate reasoning or on the structure of your edits. You will be graded on **whether the reports the two scripts produce match the reports they would produce after a correct fix**. Judge applies your edits + runs both scripts + compares stdout to the gold reports.

## How to approach this

In a real production system:
- The data tables are LARGE — you cannot solve this by scanning every row.
- No one documents the business rules explicitly — you have to reverse-engineer them by reading the pipeline code (`publisher_statement.py` and `itemised_statement.py`) and understanding what each script does with the data.

To decide what edits are needed, read the scripts carefully:
- Where does each report get its values from? Which table? Which column? Lookup or baked?
- If you change X in the source data, which report changes and how?
- Multiple valid fix approaches may exist — pick the one that produces reports consistent with the business intent of the ticket.

## Files in this directory

- `ticket.md` — the change request
- `catalog.csv`, `suppliers.csv` — product/supplier master
- `transactions.csv` — retail sales
- `b2b_details.csv` — B2B/wholesale sales (high volume: many units per order)
- `promotions.csv`, `product_discounts.csv`, `currency_rates.csv` — auxiliary tables
- `publisher_statement.py`, `itemised_statement.py` — the two report scripts (Python + SQL)

## Output format

Emit a JSON array of edits to stdout. Nothing else — no explanation, no markdown fences.

Each edit is one of:

```
{"file": "<name>.csv", "op": "update", "match": {"<col>": "<value>"}, "set": {"<col>": <value>, ...}}
{"file": "<name>.csv", "op": "insert", "row": {"<col>": <value>, ...}}
```

For updates: `match` specifies which rows to change; `set` specifies which columns to update to which values.
For inserts: `row` is the new row to add (include all columns for that table).
Use `null` (JSON literal) for empty values.

Output ONLY the JSON array.
