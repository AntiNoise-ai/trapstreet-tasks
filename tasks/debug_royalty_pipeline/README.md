# debug_royalty_pipeline — Multi-Source Consistency Debugging

An open-source evaluation task for **cross-file consistency debugging** — when a ticket asks for a change to a data pipeline, does the agent identify ALL the places that need updating so that TWO reports (with DIFFERENT lookup paths) both come out correct?

Useful for evaluating agents that maintain data pipelines, do schema migrations, or fix data + code together — the class of task where "I changed one thing and now half my reports are wrong."

## Domain

Synthetic supermarket vendor-consignment accounting. The store carries products stocked by outside vendors; each period Finance owes each vendor a share of what sold. Two reports drive that payout run.

## What this task tests

**Given a ticket asking for a change to the vendor-payout pipeline, does the agent produce the correct MINIMAL edit set so BOTH reports come out consistent?**

The two reports use DIFFERENT lookup paths for the same conceptual data:
- **`vendor_statement.py`** — uses LOOKUP: `catalog[product_id] → suppliers[supplier_id] → supplier_name`. Aggregates revenue and payout by vendor.
- **`itemised_statement.py`** — uses BAKED text: reads `transactions.supplier_name` and `transactions.sku` DIRECTLY (recorded at time of sale, no lookup).

Because the two reports read supplier from different sources, a supplier change requires TWO edits (one for each lookup path). And because retail `vendor_payout_usd` is BAKED at sale time (not recomputed), any change that affects the payout amount (attribution → different vendor terms, SRP change, terms renegotiation) requires updating baked values too.

## Case structure

| Case | Trap | Fix requires |
|---|---|---|
| **case_01** | Misattributed sales — re-book to correct vendor (all-time) | route transactions.product_id + baked supplier_name/sku + recompute baked vendor_payout at new vendor's terms |
| **case_02** | Same as case_01 but partial re-book (from a date onwards) | same edits, only for post-date transactions |
| **case_03** | SRP renegotiated to 2× current price | update revenue + recompute baked vendor_payout on new net |
| **case_04** | Vendor payout terms change (pct → fixed $ per unit) | update baked retail payout + b2b_details terms; catalog for future sales |

## Data schema

- `catalog.csv` — product master. Columns: `product_id, sku, product_name, supplier_id, vendor_share_pct, vendor_share_fixed_usd, effective_from`. Can have multiple rows per product for different suppliers.
- `suppliers.csv` — vendor registry: `supplier_id, supplier_name, supplier_currency`.
- `transactions.csv` — retail (checkout) sales with BAKED fields: `transaction_id, product_id, sku, supplier_name, sale_date, revenue_gross_usd, vendor_payout_usd, transaction_fee_usd, affiliate_commission_usd, status, ...`. `vendor_payout_usd` is BAKED at sale time = `vendor_share_pct × (revenue - fees)`.
- `b2b_details.csv` — wholesale/bulk orders with BAKED terms: `b2b_txn_id, product_id, sku, supplier_name, sale_date, unit_count, unit_price_usd, revenue_gross_usd, vendor_share_pct, vendor_share_fixed_usd, status`.
- `promotions.csv`, `product_discounts.csv`, `currency_rates.csv` — auxiliary tables (currently unused noise).

## Script behavior

### `vendor_statement.py`
Per-vendor summary. For each transaction:
- supplier via LOOKUP: `catalog[product_id].supplier_id → suppliers[supplier_id].supplier_name`
- payout: retail reads baked `vendor_payout_usd` (fallback to `pct × net` from catalog); b2b computes from baked terms × units
- Aggregate by supplier_name

### `itemised_statement.py`
Per-transaction breakdown. For each transaction:
- SKU and supplier_name from transaction DIRECTLY (BAKED text)
- payout: same source as vendor_statement (baked + fallback)

## Scoring — report-output equivalence

Judge applies BOTH agent's edits AND gold's edits to a copy of the input, RUNS both report scripts, compares stdout. Score is 1.0 only if BOTH reports produce identical output.

This means:
- Multiple valid fix paths pass (any edit set producing the correct reports)
- Judge doesn't care about edit structure or intermediate reasoning
- Agent that carpet-bombs edits still fails if it changes the reports incorrectly

## Files per case

`inputs/<case_id>/`:
- `README.md` — task instructions + output format
- `ticket.md` — the change request
- `catalog.csv`, `suppliers.csv`, `transactions.csv`, `b2b_details.csv`, `promotions.csv`, `product_discounts.csv`, `currency_rates.csv`
- `vendor_statement.py`, `itemised_statement.py` — report scripts

## Expected output

A JSON array of edits:

```json
[
  {"file": "transactions.csv", "op": "update", "match": {"transaction_id": "TXN-001"},
   "set": {"product_id": "PID-070", "sku": "SKU-070-MG",
           "supplier_name": "MerchantGate Distributors", "vendor_payout_usd": 69.75}}
]
```

Supported ops: `update` (with `match` + `set`), `insert` (with `row`).

## Data source & license

All code, data, scenarios are **synthetic**, hand-authored for this task. See [LICENSE.md](LICENSE.md).

## Run

```bash
python3 build_cases.py                     # (re)generate inputs/ + expected/
python3 -m pytest tests/ -v                # unit tests
```
