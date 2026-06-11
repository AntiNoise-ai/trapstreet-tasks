# Spreadsheet Reader

A trap-compatible task that hands the agent a **real `.xlsx`** and asks one
simple aggregation question. Every sheet looks tidy but hides one piece of
real-world mess: the *naive* read returns a clean, confident, **wrong** number.

This mirrors the FinanceBench/`pdf_reader` philosophy (extract the right number
from a messy document) but for spreadsheets — where SOTA agents (Excel Agent
mode, ~57% on SpreadsheetBench) still routinely trip.

The eval is **pure-rule-based**: each answer is a single number, graded by a
`leading_numeric` matcher (shared with `pdf_reader`). No LLM-judge.

**Lane: agent-path.** A binary `.xlsx` requires tools/code to open, so this task
targets tool-using agents. Every case is verified to **trap a competent code
solve** (not just a careless human) — the laziest plausible `pandas`/`openpyxl`
read returns the decoy, not the gold. Run `build_sheets.py`'s comments + the
`_decoy_naive_answer` field to see each trap; the README's "naive" column is the
result of an actual `pd.read_excel(...).sum()`-style solve.

---

## Cases (6)

| id | category | difficulty | the trap | naive code → correct |
|---|---|---|---|---|
| `units_in_header` | units | easy | header says `Revenue ($ thousands)` | `.sum()` 551.75 → **551750** |
| `numbers_as_text` | types | medium | amounts stored as **text** with comma separators | `.sum()` concatenates/errors → **19484.74** |
| `parentheses_negatives` | signs | medium | accounting format — `(1,200)` means **−1200** | unparsed text → **5750** |
| `dedup_messy_customers` | dedup | medium | names differ only by **case / whitespace** | `nunique()` 7 → **3** |
| `total_row_double_count` | total_row | hard | a `TOTAL` row sits **inside** the Amount column | `.sum()` 3850 (doubles) → **1925** |
| `wrong_sheet` | multi_sheet | hard | real data is on a **non-default sheet** | first-sheet `read_excel` 6000 → **7500** |

Each `expected/<id>/answer.json` records the `_decoy_naive_answer` — the number
a careless read produces — so the failure mode is documented, not just the gold.

---

## Solution contract

1. Read `INPUTS` (JSON dict: `filename → absolute path`).
2. Read `INPUTS["question.txt"]` (the question) and `INPUTS["data.xlsx"]` (the sheet).
3. Print a single number to **stdout** (plain text or `{"answer": "..."}`).

The judge extracts the first number (handles `$`, commas) and compares to gold
with a 0.01 tolerance. Any mismatch → 0.0; ≥80% of cases pass → run passes.

---

## Regenerating

All sheets + gold are produced by `build_sheets.py` (uses `openpyxl`):

```bash
python3 build_sheets.py     # rewrites inputs/*.xlsx, question.txt, expected/, traptask.yaml
```

Edit case values there — never hand-edit the `.xlsx` — so the gold stays
derived from the same source numbers.
