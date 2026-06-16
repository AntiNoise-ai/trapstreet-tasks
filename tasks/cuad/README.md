# CUAD — legal contract clause extraction

## What this task tests

Can an AI do the most basic job of a legal-review tool: **read a contract and
find a specific clause — or correctly say it isn't there?**

Each case gives the model one real commercial contract (a material agreement
filed on SEC EDGAR) and asks about **one** of 41 clause types — Anti-Assignment,
Change of Control, Cap on Liability, Governing Law, and so on. The model must
return the **exact text of that clause**, or, if the contract has no such clause,
say so explicitly.

The data comes from **CUAD** (Contract Understanding Atticus Dataset), where every
answer is a lawyer-labeled span. See [`ATTRIBUTION.md`](ATTRIBUTION.md)
(CUAD, CC BY 4.0). This revives the archived
[`case12_legal_clause_extraction`](../../archive/case12_legal_clause_extraction/)
exploration as a runnable task.

---

## Input — what the model receives

**One file per case: `inputs/<case-id>/question.txt`.** It contains the **entire
contract** plus the question plus a format instruction, in this layout:

```
===== CONTRACT =====
<the full contract text — 10k to 175k characters, untruncated>

===== QUESTION =====
Highlight the parts (if any) of this contract related to "Agreement Date"
that should be reviewed by a lawyer. Details: The date of the contract

Instructions:
- If the contract above contains such a clause, quote the EXACT text of the
  relevant span(s), verbatim.
- If the contract contains NO such clause, respond with exactly: NO CLAUSE FOUND
- Do not explain your reasoning. Output only the quoted span(s) or "NO CLAUSE FOUND".
```

The model receives the whole contract and the question **together** — nothing is
split out or summarized. (Because contracts can run tens of thousands of
characters, this is also a long-context test in disguise.)

---

## Expected output — what counts as correct

The model should print **only** one of:

1. the exact clause text, quoted verbatim from the contract, **or**
2. `NO CLAUSE FOUND`

There are two kinds of case, and they catch opposite failures:

### Case type A — the clause IS present

The contract genuinely contains the clause. The correct answer is the quoted span.

> **Example** — case `cuad_p18_agreement_date`
> **Question:** the "Agreement Date" clause
> **Correct output:** `6th day of April, 1999`  ← (the actual date text in the contract)
> **Wrong output:** `NO CLAUSE FOUND`  ← **the laziness failure**: the clause is right there, but the model gave up

The gold answer lives in `expected/<case-id>/answer.json`:

```json
{
  "gold_present": true,
  "gold_spans": ["6th day of April, 1999"],
  "matchers": [{ "kind": "span_f1", "gold_spans": ["6th day of April, 1999"], "threshold": 0.5 }]
}
```

### Case type B — the clause is ABSENT

The contract has no such clause. The correct answer is to say so.

> **Example** — case `cuad_a02_change_of_control`
> **Question:** the "Change of Control" clause (this supply contract has none)
> **Correct output:** `NO CLAUSE FOUND`
> **Wrong output:** quoting some unrelated section as if it were the clause  ← **the hallucination failure**

```json
{
  "gold_present": false,
  "matchers": [{ "kind": "no_clause" }]
}
```

The categories are **paired**: the same clause type (e.g. Change of Control)
shows up both in a contract that has it and one that doesn't, so a model can't
score well by guessing "this clause is always / never present."

---

## How answers are graded

A small Python judge (`judge.py`) scores each case 1.0 or 0.0:

| Matcher | Used for | Passes when |
|---|---|---|
| `span_f1` | present cases | `max(token-F1, containment)` against **any** gold span ≥ 0.5. Token-F1 uses SQuAD-style normalization; containment lets a verbatim quote pass even if wrapped in commentary. A "no clause" answer scores ~0 here → **catches laziness**. |
| `no_clause` | absent cases | the answer asserts absence (`NO CLAUSE FOUND`, "does not contain", "no such provision", "none", …). A fabricated span has no absence language → **catches hallucination**. |

After all cases, `grader.py` aggregates and reports overall accuracy plus two
diagnostics that are the whole point of the task:

- **`recall_present`** — accuracy on present cases. Low = the model is **lazy**
  (missing clauses that are there).
- **`precision_absent`** — accuracy on absent cases. Low = the model is
  **hallucinating** (inventing clauses that aren't there).

---

## Cases

- **32 cases by default:** 20 present + 12 absent, drawn from the official CUAD
  `test` split (never `train` — that was used to fine-tune the models being
  evaluated).
- Priority-ordered toward the subtle, frequently-misread clauses (Anti-Assignment,
  Change of Control, Most Favored Nation, Cap on Liability, …).

```
tasks/cuad/
├── inputs/<case-id>/question.txt     # contract + question + instruction
├── expected/<case-id>/answer.json    # gold span(s) + matcher
├── judge.py                          # per-case scoring (span_f1 / no_clause)
├── grader.py                         # run-level aggregation + diagnostics
├── gold.cases.json                   # manifest of all cases
├── traptask.yaml                     # case list trap reads
└── build_cases.py                    # regenerates the slice from upstream CUAD
```

---

## Running it

The task is self-contained on GitHub — the contracts are embedded in the
`question.txt` files, so a fresh clone can run immediately.

Regenerate or resize the slice (downloads CUAD's `data.zip`, ~17 MB, on first run
and caches it in a gitignored `.cache/`):

```bash
python3 build_cases.py                      # 20 present + 12 absent
python3 build_cases.py --present 25 --absent 16
```

Test the judge:

```bash
python3 -m pytest test_judge.py -q
```
