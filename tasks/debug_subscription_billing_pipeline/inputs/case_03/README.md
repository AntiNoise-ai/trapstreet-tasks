# Task

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
