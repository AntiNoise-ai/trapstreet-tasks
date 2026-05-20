# Tenancy Agreement — PDF Reader task

A trap-compatible task that asks an agent to extract facts from a real UK
Assured Shorthold Tenancy (AST) PDF and answer 19 questions across rent,
dates, clauses, scenarios, and reasoning. Designed to be **harsh**: agents
that hedge, skip parts of multi-part questions, or use the wrong format fail
the relevant case outright.

Compatible with [`trap`](https://github.com/AntiNoise-ai/trap) — the
trapstreet CLI. Drop a solution `trap.yaml` next to your agent code that
points `traptask:` at this directory and run `uv run tp run`.

---

## Layout

```
tenancy_agreement/
├── traptask.yaml             # case list (19 cases) + judge/grader cmds
├── judge.py                  # per-case scorer (harsh, type-aware matchers)
├── grader.py                 # aggregator (score, pass/fail, by-category breakdown)
├── gold.candidates.json      # source-of-truth for question wording + gold answers
├── AST_Issue_1_CanaryWharf.pdf  # the document under test (sanitised)
├── inputs/
│   └── {case_id}/
│       ├── question.txt      # the prompt for this case
│       └── document.pdf      # symlink → ../../AST_Issue_1_CanaryWharf.pdf
└── expected/
    └── {case_id}/
        └── answer.json       # gold answer + type + matchers
```

---

## What the solution must do

The trap runner injects two env vars:

- `INPUTS` — JSON mapping `filename → absolute path` for files in `inputs/{case_id}/`
- `OUTPUTS` — JSON for declared file outputs (this task uses **stdout**, not file outputs)

Per case the solution receives:
- `INPUTS["question.txt"]` → path to a single-line prompt
- `INPUTS["document.pdf"]` → path to the AST PDF (1.8 MB, identical across cases)

The solution must **print its answer to stdout**. Plain text or JSON
(`{"answer": "..."}`) — the judge accepts both.

### Minimal solution example

```python
# solution.py
import json, os, sys

inputs = json.loads(os.environ["INPUTS"])
question = open(inputs["question.txt"]).read().strip()
pdf_path = inputs["document.pdf"]

answer = my_agent(question, pdf_path)   # ← your agent here
print(answer)
```

Solution-side `trap.yaml`:

```yaml
tasks:
  test:
    cmd: uv run python solution.py
    traptask: /path/to/trapstreet-tasks/tasks/pdf_reader/tenancy_agreement
    timeout: 120
```

Run:

```bash
uv run tp run            # all cases
uv run tp run -t money   # only `money`-tagged cases
uv run tp run --fail-fast
```

---

## How the judge grades

For each case the judge reads `expected/{case_id}/answer.json`:

```json
{
  "id": "rent_year2",
  "answer": "2100",
  "type": "numeric",
  "matchers": [
    {"kind": "numeric", "value": 2100.0, "tolerance": 0.01}
  ],
  "category": "money",
  "difficulty": "medium"
}
```

A case scores **1.0 only if ALL matchers pass** — no partial credit. The
supported matcher kinds and why they're strict:

| Kind | Purpose |
|---|---|
| `numeric` | Passes if ANY number in the answer matches (within tolerance). Use for show-your-working cases where intermediate numbers appear. |
| `leading_numeric` | The FIRST number must match. Use for simple extraction where listing decoy numbers should not pass. |
| `regex_required` | Pattern must match. Used for dates (`05/09/2022`), postcodes (`E14 9LQ`). |
| `leading_word` | First alpha token must equal target (after stripping markdown noise + labels like `"Answer:"` / `"**Answer**:"`). Forces yes/no to commit, not hedge. |
| `keywords_all` | Every listed keyword must appear (case-insensitive substring). |
| `keywords_any` | At least one synonym must appear (case-insensitive substring). |
| `keywords_any_word` | At least one value must appear as a whole word (`\b…\b`). Use for short acronyms (`ICE`, `BOE`) that would false-match inside `"price"` or `"Boeing"`. |
| `no_hedge` | Rejects "I cannot determine", "as an AI", "unclear from the document", etc. |
| `min_words` | For multi-part questions: rejects one-word answers that skip the explanation. |

All 19 cases currently have curated gold and matchers. If a future case is
added without matchers (e.g. `"answer": null`), the judge returns
`score: null` so it's surfaced in the report as "not yet graded" rather
than penalising the agent.

---

## How the grader aggregates

`grader.py` consumes per-case metrics and emits one run-level JSON:

```json
{
  "passed": false,
  "score": 0.78,
  "n_total": 23,
  "n_scored": 18,
  "n_skipped_no_gold": 5,
  "threshold": 0.8,
  "by_category": {
    "money": 0.83,
    "dates":  1.0,
    "clauses": 0.71,
    "metadata": 0.0
  }
}
```

Pass threshold is **80 %** of *scored* cases (skipped cases don't count).
Edit `PASS_THRESHOLD` in `grader.py` to tighten — set to `1.0` for an
all-correct pass bar.

---

## Adding / changing cases

1. Edit `gold.candidates.json` (the source of truth) — add the question,
   answer, category, difficulty.
2. Add an entry to `traptask.yaml`'s `cases:` list with matching `id`.
3. Regenerate `inputs/{id}/` and `expected/{id}/answer.json` (the symlink
   to the PDF + the gold + matchers). Easiest is a one-shot Python script
   pulling from `gold.candidates.json`; see the generation block in
   `judge.py`'s commit history for a template.
4. (Optional) Add a matcher rule for the new case to make grading harsh.

---

## Status

- 19/19 cases have curated gold + matchers (scoring is fully automatic).
