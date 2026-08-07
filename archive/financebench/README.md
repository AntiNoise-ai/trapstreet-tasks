# financebench (archived)

> **Archived, not maintained.** Moved out of `tasks/` because its source data is
> **CC BY-NC 4.0** (NonCommercial), which `tasks/imported/README.md` explicitly
> excludes from this repo's import set. It was never registered on
> trapstreet.run and never will be. Kept for reference only.
>
> To build a leaderboard task on this material, author **original** questions
> over the same public SEC 10-K filings — the filings are public, the Q&A pairs
> are Patronus AI's. See [`ATTRIBUTION.md`](ATTRIBUTION.md).
>
> Earlier exploration of the same dataset: [`../case5_finance_qa`](../case5_finance_qa).

5 closed-book numeric questions on SEC 10-K filings — Netflix 2017, AES 2022,
3M 2018, Walmart 2018, Block 2016. Each case ships the question **plus the
relevant 10-K excerpt inline** as `doc.txt`, so solvers don't need to fetch
PDFs or hit external services.

Consolidated into this monorepo from the standalone `trapstreet/financebench`
repo. There is no `grader.py`, so it produces per-case scores but no run-level
aggregate.

A trapstreet task you'd submit answers to via the standard `tp run` + `tp submit`
flow, or via the [`/trapstreet-eval` Claude Code skill](https://github.com/AntiNoise-ai/trapstreet-mvp/issues/42).

## Layout

```
financebench/
├── README.md
├── ATTRIBUTION.md            # source + CC BY-NC 4.0 license notice
├── traptask.yaml             # 5 cases
├── judge.py                  # per-case scorer (numeric ≤1% tol / string match)
├── inputs/<case_id>/
│   ├── question.txt          # the question — what the solver must answer
│   └── doc.txt               # the relevant 10-K excerpt (closed-book context)
└── expected/<case_id>/
    └── answer.json           # {financebench_id, company, doc, gold}
```

## The 5 cases

| id | company | year | type |
|---|---|---|---|
| `netflix_2017_current_liab` | Netflix | 2017 | single-statement extraction (current liabilities) |
| `aes_2022_roa` | AES | 2022 | derived (ROA = net income / avg assets) |
| `threem_2018_net_ppne` | 3M | 2018 | single-statement + unit conversion (M → B) |
| `walmart_2018_dpo` | Walmart | 2018 | derived (DPO formula) |
| `block_2016_working_capital` | Block (Square) | 2016 | ratio (TCA / TCL) |

## Solution contract

Solver reads:

- `inputs/<case_id>/question.txt` — the question
- `inputs/<case_id>/doc.txt` — the 10-K excerpt (your "closed book")

Solver writes its answer to **stdout**. That's it. No file output required.

Format for the stdout answer: **just the number / string itself**, no
prose. Numeric tolerances handle units / scale / accounting parentheses /
% / commas / `$`. Example acceptable formats for Walmart DPO:

- `42.69`
- `42.69 days`
- `$42.69`
- `(42.69)` — accounting negative

But **not** a paragraph that contains the number after a wall of reasoning
— the judge still just picks up the first *qualifying* number in the
response (see below). Keep it terse.

## Scoring

`judge.py` runs once per case and emits:

```json
{
  "score": 1.0 or 0.0,
  "correct": true | false,
  "agent_answer": "<truncated to 500 chars>",
  "expected_answer": "<gold>",
  "reason": "numeric match (pred=42.69 gold=42.69)",
  "company": "Walmart",
  "doc": "WALMART_2018_10K",
  "financebench_id": "financebench_id_06247"
}
```

Numeric comparison uses 1% relative tolerance (`REL_TOL = 0.01`). Strings
fall back to case-insensitive exact / substring match.

**"First qualifying number" (fixed 2026-07):** the original matcher took
literally the first number-like token in the response, which broke on two
common, correct answer shapes:

1. Restating a number that's already in the question — every case's
   `question.txt` names the fiscal year (e.g. "FY2018"), and `3M`'s ticker
   itself parses as the digit `3`. An answer like *"For FY2018, 3M's net
   PP&E was $8.70 billion"* got graded against `2018` or `3`, not `8.70`.
   The judge now excludes any number that already appears in the question
   before picking the answer's first qualifying number.
2. Restating the unit the question asked for. Gold values are stored
   pre-scaled to the requested unit (e.g. Netflix's gold is the bare number
   `5466`, for a question asking "in USD millions"). An answer that spells
   the unit out — *"$5,466 million"* — was getting re-multiplied by 1e6 and
   compared against the un-scaled gold. The judge now accepts either the
   literal value or the magnitude-scaled value, whichever matches gold.

Both are demonstrated + regression-tested in the case history; no case's
correctness behavior for a genuinely wrong answer changed.

No `grader.py` — trap auto-aggregates (pass if avg ≥ 0.8, etc.).

## Submit

Either path works:

### Via `tp` CLI (any solver)

```bash
# in your solver's directory, with trap.yaml pointing at this task:
tp run
tp submit financebench
```

### Via Claude Code skill (closed-book in-session model)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/trapstreet/trapstreet/main/skill/install.sh)
# then in any Claude Code session:
/trapstreet-eval
```

See https://trapstreet.run/tasks/financebench for the leaderboard.

## Provenance

Questions + evidence + gold answers are from
[PatronusAI's FinanceBench](https://huggingface.co/datasets/PatronusAI/financebench)
via [Ruqii/trapstreet-cases](https://huggingface.co/datasets/Ruqii/trapstreet-cases).
This task packages 5 representative questions into the trap task format.

The matching logic in `judge.py` is adapted from the original
[`grade.py`](https://github.com/AntiNoise-ai/trapstreet-eval-demo/blob/main/skill/trapstreet-eval/grade.py)
in the trapstreet-eval-demo skill.
