# Invoice Reconciliation — Find the Discrepancy

A trap-compatible task that tests whether a model can **find the source of a real reconciliation discrepancy** between a customer's invoice and our internal records. 14 cases that step through the diagnosis the way a real finance team would.

## The real-world puzzle

A customer's sales report (Excel, ~6,174 rows) should reconcile against our internal transaction records (CSV, ~6,124 rows). They don't reconcile cleanly. **The model has to figure out where the discrepancy comes from.**

The task gives the model both files in their entirety on every case (no row sampling) — same data per case, different question. The 14 questions walk the model through what a real reconciliation looks like:

| Stage | Cases | What it asks |
|---|---|---|
| **Step 1: Headline totals** | 2 | Sum the two files independently |
| **Step 2: Join cardinality** | 2 | How many rows in one file but not the other? |
| **Step 3: Breakdown** | 2 | Of the orphan rows, how many are Returns vs Sales? |
| **Step 4: Monetary impact** | 2 | Sum the orphan rows' values |
| **Step 5: Returns handling** | 4 | How are Returns / Refunds / Chargebacks represented in each file? |
| **Step 6: Diagnostic multiple choice** | 1 | Identify the PRIMARY structural cause (A/B/C/D) |
| **Step 7: Confirmation** | 1 | Numerical confirmation of the chosen cause |

A model that gets all 14 right has effectively walked through the diagnosis a junior accountant would do. A model that gets only the easy aggregations is doing surface-level OCR + arithmetic without the reconciliation insight.

## The actual data

After investigation (see `expected/*/answer.json` for the verified gold values):

- **Excel total** `cost_in_billing_ccy`: **$84,413.41 USD** (all 6,174 rows are billed in USD)
- **CSV total** `internal_revenue`: **£61,120.05 GBP**
- Currency split is real — Excel is USD because that's the customer's billing currency; CSV is GBP because that's our reporting currency
- The two totals are not directly comparable without FX conversion. **Even after FX, there's a residual structural gap.**

### Where the gap really comes from

| Source | Count | Net impact |
|---|---|---|
| **Excel-only transactions** (no CSV match) | **33 refs** | Mostly cancelled returns (27) + a few completed sales (11) — the LARGEST structural cause |
| **CSV-only transactions** (no Excel match) | 3 refs | Small (£19.26) |
| **Returns/Refunds tracked in both** but with different codings | 15 returns in Excel match 16 REFUNDED + 2 CHARGEBACK in CSV | Coding mismatch, not magnitude |
| **`-1` retry suffixes** | 6 refs | Tiny ($62 total) — not the cause but worth knowing about |

**The Step 6 multiple choice answer is `A`**: most of the discrepancy comes from Excel-only transactions that aren't on our internal side.

## Join key

`customer_invoice.external_ref` ↔ `internal_transactions.txn_ref`

In the full data:
- 6,136 transactions overlap
- 33 in Excel only
- 3 in CSV only
- 6 of the Excel rows have `external_ref` ending in `-1` (retry/correction marker)

## Currency split (important)

- **Excel** monetary values (`cost_per_unit`, `revenue_gross`, `tax_amount`, `cost_in_billing_ccy`) are in `billing_ccy` which is **USD** for every row in this dataset.
- **CSV** `internal_revenue` is in **GBP** — NOT USD.

Every question states which currency the answer should be in. **Don't mix USD totals from the Excel with GBP values from the CSV without explicit conversion.** No question in this v1 requires FX conversion; each is scoped to one file or already specifies the target currency.

## Input

Per case the agent receives:
- `INPUTS["customer_invoice.xlsx"]` — **FULL** 6,174-row Excel (~1 MB)
- `INPUTS["internal_transactions.csv"]` — **FULL** 6,124-row CSV
- `INPUTS["question.txt"]` — the task framing + the specific question

## Expected output

A single value on stdout — number or single letter. The judge enforces:

- Numeric cases: `numeric` matcher with ±$1 tolerance (rounding slack)
- Count cases: `leading_numeric` exact match
- Multiple-choice case: `leading_word` exact (A, B, C, or D)
- Plus `no_hedge` everywhere

Each case scores 1.0 / 0.0. Run passes if ≥80% correct.

## Why this is a meaningful TrapStreet task

1. **Tests real B2B reconciliation, not just OCR or single-file arithmetic** — every case requires correlating two files
2. **Forces models to actually compute over 6K+ rows** — no shortcut via title/header scanning
3. **The diagnostic case (Step 6) tests whether the model can synthesize** — by the time it reaches Step 6, it should have computed enough to know the answer; a model that guesses without doing the steps is exposed
4. **Real per-case cost trade-off** — Excel + CSV together are ~250K tokens of text representation. Models without long context can't even attempt; mid-tier models attempt and fail at arithmetic at scale; frontier models cost real money to run. THE TrapStreet question.

## Cost warning

This is a **heavy task** — full-file input per case × 14 cases. On Claude Opus or GPT-4 class models, a single run could cost **$5-20 in API charges**. Use `claude-sonnet`, `gemini-flash`, or similar mid-tier models for cost-effective comparison runs. Smaller models (< 200K context) will fail outright because the files don't fit.

## Honest limitations

- **Single customer's data.** All 6K transactions are from one anonymized customer relationship. A v2 should span multiple customer profiles for genuine generalization.
- **Real values, just identity-scrambled.** Numbers are real (no perturbation in this version). For public release, would need re-anonymization with consistent multipliers applied to both sides.
- **No FX rate provided.** The task explicitly avoids FX conversion questions because the contributor's real FX policy isn't represented in the dataset. A v2 could add an explicit FX rate constant.
- **`internal_revenue` is GBP** even though Excel is USD — this currency split is what real B2B reconciliation looks like, but a model unfamiliar with this convention may answer in the wrong units.

## License + attribution

See [LICENSE.md](LICENSE.md) for the full anonymization process. Source data was contributed by the project owner from her own work; identity-scrambled via the two-step pipeline before public release.
