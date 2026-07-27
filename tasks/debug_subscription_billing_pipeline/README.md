# debug_subscription_billing_pipeline — Multi-Report Consistency Debugging

An open-source evaluation task for **cross-file, cross-report consistency debugging** — when a ticket asks for a change to a SaaS billing pipeline, does the agent identify ALL the places that need updating so that FOUR reports (each resolving the same underlying facts through a different baked/live/mixed lookup path) all come out correct — and nothing more than that?

Useful for evaluating any agent/framework/skill (regardless of which model powers it) on agentic coding tasks that require reading multiple scripts to reverse-engineer business rules, tracing multi-hop lookup chains, and editing precisely — not shotgunning changes across every file that might be related.

## Domain

Synthetic SaaS company. Customers subscribe to plans (which belong to tiers), can add optional add-ons, and may have a discount code applied. Each billing period an invoice is generated and its financial fields are BAKED into `invoices.csv` at that point in time — a historical record, not something silently recomputed later.

## What this task tests

**Given a ticket asking for a change to the billing pipeline, does the agent produce the correct MINIMAL edit set so ALL FOUR reports come out consistent?**

The four reports resolve the same underlying facts through different paths:

| Report | Base price | Add-ons | Discount | Tax |
|---|---|---|---|---|
| `billing_summary.py` | LIVE (current plan) | LIVE | LIVE | LIVE |
| `invoice_detail.py` | BAKED | BAKED | BAKED | BAKED |
| `finance_ledger.py` | BAKED | BAKED | BAKED | baked, else LIVE fallback |
| `customer_statement.py` | BAKED (grandfathered) | LIVE | LIVE (best-of pct/fixed) | LIVE |

Because each report resolves differently, the SAME underlying change can require touching different combinations of files — a change to a current-state table (plans/addons/discount_codes/customers) flows automatically into the LIVE reports, while a change that must also correct a specific HISTORICAL invoice requires directly editing that row (and only that row) in `invoices.csv`.

## Case structure

| Case | Trap | Fix requires |
|---|---|---|
| **case_01** | Region migration effective a specific date; Feb invoice already baked at the wrong (old) tax rate | update customer's live region + recompute baked tax/total on the one affected invoice; Jan invoice untouched |
| **case_02** | Plan price increase effective from a date; a pct-based discount recalculates off the new subtotal, a fixed discount does not | update plan price + recompute baked base/discount/tax/total on invoices from the effective date onward only |
| **case_03** | Add-on rename + reprice with explicitly NO backfill required | update the add-on's current-state row only — touching any historical invoice is penalized (restraint / anti-shotgun) |
| **case_04** | Discount code pct correction + one specific historical invoice needs its baked discount fixed; a distractor invoice on a different code must be left alone | update the code definition + recompute baked discount/tax/total on exactly the one affected invoice |
| **case_05** | Subscription transfers to a NEW customer entity registered in a DIFFERENT region | insert new customer row + reassign subscription + recompute baked customer name/tax/total on the one invoice after the transfer date |
| **case_06** | Compound ticket: tier upgrade AND a discount code applied simultaneously, on one invoice | update subscription's plan + discount code + recompute all baked financial fields on exactly the affected invoice, without touching the prior period |

## Data schema

- `customers.csv` — `customer_id, customer_name, region_id, signup_date`
- `subscriptions.csv` — `subscription_id, customer_id, plan_id, addon_ids (semicolon-separated), discount_code, status, start_date`
- `plans.csv` — `plan_id, plan_name, tier_id, base_price_usd`
- `tiers.csv` — `tier_id, tier_name, seat_limit`
- `addons.csv` — `addon_id, addon_name, addon_price_usd`
- `discount_codes.csv` — `code, discount_pct, discount_fixed_usd, expires_on`
- `regions.csv` — `region_id, region_name, tax_rate_pct`
- `invoices.csv` — BAKED per-period record: `invoice_id, subscription_id, period, baked_customer_name, baked_plan_name, baked_addon_names, baked_base_price_usd, baked_addon_total_usd, baked_discount_applied_usd, baked_tax_usd, baked_total_usd, status`
- `support_tickets.csv`, `marketing_campaigns.csv` — auxiliary noise tables, unused by any report

## Scoring — report-output equivalence

Judge applies BOTH the agent's edits AND the gold edits to separate copies of the input, RUNS all four report scripts, compares stdout. Score is 1.0 only if ALL FOUR reports produce identical output.

This means:
- Multiple valid fix paths pass (any edit set producing the correct reports)
- Judge doesn't care about edit structure or intermediate reasoning
- An agent that carpet-bombs edits still fails if it changes any report incorrectly (verified directly: case_03's restraint test asserts an unwarranted invoice edit is penalized even when the rest of the fix is correct)
- Edits beyond `MAX_EDITS_SCORED` (30) are dropped before applying, capping how far a shotgun list of guesses can go

## Files per case

`inputs/<case_id>/`:
- `README.md` — task instructions + output format
- `ticket.md` — the change request
- all 10 `*.csv` tables listed above
- `billing_summary.py`, `invoice_detail.py`, `finance_ledger.py`, `customer_statement.py` — the four report scripts

## Expected output

A JSON array of edits:

```json
[
  {"file": "customers.csv", "op": "update", "match": {"customer_id": "CUST-001"}, "set": {"region_id": "REG-TX"}},
  {"file": "invoices.csv", "op": "update", "match": {"invoice_id": "INV-1002"}, "set": {"baked_tax_usd": 0.0, "baked_total_usd": 148.0}}
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
