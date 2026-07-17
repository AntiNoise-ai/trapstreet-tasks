# Task

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
