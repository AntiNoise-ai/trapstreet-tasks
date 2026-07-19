# Task

A colleague filed a ticket asking for a fix to the vendor-payout pipeline.

**Your goal:** ensure both reports (`vendor_statement.py` and `itemised_statement.py`) come out CORRECT after the fix is applied.

You will not be graded on your intermediate reasoning or on the structure of your edits. You will be graded on **whether the reports the two scripts produce match the reports they would produce after a correct fix**. Judge applies your edits + runs both scripts + compares stdout to the gold reports.

## Business context

This supermarket runs a consignment model: vendors stock the shelves, and every period the store owes each vendor a share of what sold. These two reports are the source of truth for that monthly payout run:
- `vendor_statement` — the per-vendor summary Finance uses to cut monthly payout checks. The `total_payout_usd` column IS the amount each vendor gets paid.
- `itemised_statement` — the per-transaction breakdown vendors audit against their sales.

Getting `vendor_payout_usd` right on every affected line is the whole point. An inconsistency here is a real over/under-payment to a vendor. So when a ticket changes something upstream — attribution, pricing, terms — think through: does the change move payout money around, or change how much payout is owed? Both flow through these reports and both must land right.

## How to approach this

In a real production system:
- The data tables are LARGE — you cannot solve this by scanning every row.
- No one documents the business rules explicitly — you have to reverse-engineer them by reading the pipeline code (`vendor_statement.py` and `itemised_statement.py`) and understanding what each script does with the data.

To decide what edits are needed, read the scripts carefully:
- Where does each report get its values from? Which table? Which column? Lookup or baked?
- If you change X in the source data, which report changes and how?
- Multiple valid fix approaches may exist — pick the one that produces reports consistent with the business intent of the ticket.

## Files in this directory

- `ticket.md` — the change request
- `catalog.csv`, `suppliers.csv` — product/vendor master
- `transactions.csv` — retail (checkout) sales
- `b2b_details.csv` — wholesale/bulk orders (high volume: many units per order, e.g. restaurant supply)
- `promotions.csv`, `product_discounts.csv`, `currency_rates.csv` — auxiliary tables
- `vendor_statement.py`, `itemised_statement.py` — the two report scripts (Python + SQL)

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
