# Connections — word grouping

The model receives 16 shuffled words and must partition them into **4 groups of 4**
that each share a hidden connection (NYT *Connections* format). Objectively graded.

## Why this task

Unlike the MBTI self-profile (format-only, no right answer), Connections has an
objective ground truth, so it discriminates model skill: semantic reasoning plus
resistance to **trap words** — a word whose surface reading lures toward the wrong
group. Puzzles are 100% original (never scraped from NYT) to avoid leakage and
copyright.

## Files

| File | Role |
|------|------|
| `gold.cases.json` | Source of truth — 10 puzzles. **Edit here.** |
| `build_cases.py`  | Generates `inputs/` + `expected/` and validates invariants. |
| `judge.py`        | Per-case scoring. |
| `grader.py`       | Run-level aggregation. |
| `inputs/<id>/question.txt`  | GENERATED — the model prompt. |
| `expected/<id>/answer.json` | GENERATED — the gold partition. |

Regenerate after editing puzzles: `python3 build_cases.py`

## Input / output contract

The model receives `inputs/<id>/question.txt` and must reply with a single JSON object:

```json
{"groups": [{"theme": "short label", "words": ["W1","W2","W3","W4"]}, ...4 total...]}
```

The `theme` label is collected but **not graded**.

## Scoring

- **Per case** (`judge.py`): only the **first 4 groups** emitted are scored
  (anti-shotgun — extra or duplicate groups past the fourth are ignored, so a
  model can't pad its output with guesses). `score = (gold groups exactly
  reproduced among the first 4) / 4`, by set-equality of the four words
  (case/whitespace-insensitive; group order and theme labels don't matter).
  `solved` requires `well_formed` (exactly 4 groups of 4 words forming a valid
  partition of the 16-word universe) **and** all 4 groups correct. Surfaced
  metrics: `score`, `groups_correct`, `well_formed`, `solved`, `format_ok`,
  `themes` (ungraded). Non-JSON or missing `groups` → `score 0.0`,
  `format_ok: false`, `well_formed: false`.
- **Per run** (`grader.py`): mean score across cases; `n_passed` counts fully
  solved puzzles; `by_category` breaks score down by difficulty tier. Run passes
  at mean ≥ `0.75`.

## Puzzle authoring invariants (enforced by `build_cases.py`)

- Exactly 16 distinct words, partitioned into 4 groups of 4.
- Every word has exactly one correct group (lures are surface-only).
- At least one declared `trap` word, and every trap is one of the 16 words.

## Run

```bash
python3 build_cases.py                 # (re)generate cases
python3 -m pytest tests/ -v            # unit tests
```
