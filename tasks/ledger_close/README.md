# Year-end receivables close

A solution is handed a year of accounts-receivable bookkeeping — monthly
ledger extracts, an allocation memo, a customer master, a document index —
and asked one figure about the year end. Getting it right means reading the
right files, working out an unstated allocation policy from worked examples,
noticing that the policy changed part-way through the year, and noticing that
one month's extract is short.

## Why this task

Ask an agent to compute something over a single sheet it can see all of, and
it will compute it. `ledger_audit`, the single-shot sibling of this task, was
put through eight rounds of escalating arithmetic difficulty — multi-rule
settlement, an induced rather than stated policy, a mid-period policy change,
out-of-order vouchers, aggregates with every closed-form shortcut blocked —
and a bare harness scored 8, 8, 10, 9, 8, 9, 10 out of 10. Repeated trials
showed most of that spread was run-to-run noise.

The difficulty is not in the arithmetic. It is in horizon and in depth: how
many things must be found, in what order, and how far an early wrong turn
propagates before anything looks wrong. This task moves those and holds the
arithmetic where it was.

## What the solution is given

```
inputs/case_NN/
  README.md                  the job and the output contract
  policy/allocation-memo.md  receipts worked through, then stopping
  masters/counterparties.csv the customer master
  index/documents.csv        resolves the ledgers' `Ref doc` to a voucher
  ledgers/2026-01 … 2026-MM.txt
  ledgers/2026-0K-supplement.txt
  ledgers/2025-12.txt
```

Four things have to go right, and each one changes the answer on its own:

| | |
|---|---|
| **The allocation policy** | Never stated. The memo works through the early receipts and stops. Before a changeover date a receipt settles the invoice its `Ref doc` cites and only then the oldest open one; after it, citations are ignored and everything goes oldest-first. Nothing announces the changeover — the memo simply behaves differently on either side of it. |
| **The short month** | One month's extract omits entries that were posted late and booked in a supplement. Nothing points at it. It shows up only when a month's closing balance fails to tie to the next month's opening. |
| **The re-coded customer** | One customer's code changes mid-year. The master records the succession. Read as two customers, its invoices form two settlement queues instead of one. |
| **The prior year** | `ledgers/2025-12.txt` is last year's account and does not belong in this close. |

## Output

The last `ANSWER:` line in stdout is read:

```
ANSWER: 12345.67
```

Anything else may be printed around it. Position-based extraction was tried
first — "the answer must be the last non-empty line" — and lost four correct
answers in a single calibration run to harnesses that printed the right figure
and then wrote a summary underneath, several of which stated they had
complied. Requiring a delimiter costs a solution one line and removes the
whole class of failure.

## Scoring

Binary and deterministic, no LLM judge (`judge.py`). Amounts are compared
numerically, so `12,345.67`, `$12345.67` and `12345.67` are the same answer.
`grader.py` is the standard aggregation in this repo; a run passes at mean
≥ 0.5.

## Ground truth

Computed, never authored. `gold.cases.json` carries each case's *shape* — a
question kind, a seed, a number of months, entries per month — and nothing
else. `build_cases.py` generates the year from the seed, replays the
settlement, and derives the answer. There is no answer for a human to get
wrong and nothing drawn from any corpus.

## Build invariants

`build_cases.py` refuses to emit a case unless all of these hold. Each one was
added after a calibration run produced a result it turned out not to deserve.

- **The policy can be induced.** The memo must contain at least two receipts
  where citation-first and oldest-first give different allocations, spanning
  at least two narration types, and at least three post-changeover receipts
  where a citation was *not* honoured. One post-changeover example is not
  enough: a harness saw its induced policy match 14 of 15 memo rows, reported
  the ratio honestly, and read the odd row as a keying error — which, on one
  example, is defensible.
- **Every mechanism changes the answer.** Missing the supplement, folding in
  the prior year, and splitting the re-coded customer are each replayed and
  compared to the truth *invoice by invoice*; each must move the allocation by
  more than a threshold. Comparing totals instead misses almost everything,
  because total open = debits − credits + unapplied, so any error that merely
  moves money between invoices leaves the total untouched.
- **No shortcut.** The answer must not sit within $25 of total debits, total
  credits, or their difference.
- **Not guessable.** Money answers carry at least four digits before the
  decimal.

## Calibration

`months`, `per_month`, the size of the supplement and the number of decoy
files are the knobs. Measured against a bare DeepSeek Harness — no plugins,
default profile, `deepseek-v4-flash`:

| build | score | mean wall-clock |
|---|---|---|
| single-shot (`ledger_audit`) | 9–10 / 10 | 9–399 s |
| 8–12 months × 18–28 entries | 1 / 10 | 1625 s |
| **this build** — 6–7 months × 12–14 entries | **5–7 / 10** | **~515 s** |

That range is not imprecision in the measurement. It is two runs of the same
solution against the same commit of this task, which scored 7/10 and then
5/10. Per-question success on the harder questions sits near 0.5–0.7, so a
ten-case total swings across several points between runs.

**Calibrate with repeated trials.** A single run cannot tell 5 from 7, and
this task's own history is the proof: eight rounds of design changes on the
single-shot sibling produced 8, 8, 10, 9, 8, 9, 10 — read one at a time, each
looked like evidence about the change just made, and repeated trials showed
the design changes had no measurable effect at all.

Per-question-kind accuracy from the ten-case run is a better signal than the
total, and `grader.py` reports it:

| question kind | accuracy |
|---|---|
| `open_total_cp` | 1.00 |
| `settled_total` | 0.33 |
| `aged_open_after` | 0.25 |

A tiered variant was built and reverted: three tiers of 3/3/2 cases scored
6/8 against the same harness, which at these sample sizes is the same number
as 7/10, ran slower per case, and made each case worth 12.5% instead of 10%.
Tiers are worth revisiting when a submitted configuration actually saturates
this board — with evidence by then rather than in advance of it.


## Run

```bash
python3 build_cases.py          # (re)generate inputs/, expected/, traptask.yaml
python3 -m pytest tests/ -v     # invariant tests
```
