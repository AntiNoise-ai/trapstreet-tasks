# Handover Note (domain-jargon comprehension)

A trap-compatible task built from a **real operations handover note** at a
digital game-key storefront. The note is terse, uses undefined in-house
shorthand (`PO` / `No-PO` SKUs), and carries an implicit correction whose
conclusion contradicts the naive reading. It's the kind of note a colleague
leaves you — and that a model (Gemini, in the wild) got wrong.

The eval is **pure-rule-based** (no LLM-judge): short, committed answers graded
by `leading_word` / `leading_numeric` / `keywords` matchers (shared with
`pdf_reader`).

> **Lane: model-eval (no tools).** Plain text in, an answer out — this probes a
> model's own reading + reasoning, not a code-writing agent.

---

## The domain (what makes it a trap)

| term | meaning | royalty? |
|---|---|---|
| **PO SKU** | purchase order — already in *paid* stock | **No** royalty owed |
| **No-PO SKU** | not in paid stock | **Yes**, royalty owed |

The bundle wrongly shipped **No-PO** SKUs. The fix reclassifies the 517 sold
keys to **PO** (paid) stock, so they **must not** appear on the publisher's
royalty statement (the note says so explicitly).

**The single robust failure mode** — every model that fails does the same thing:
it reads *"the **correct/proper** pack is normal, so it bills royalty."* That's
inverted. PO = pre-paid = **no royalty**, so the *whole* bundle (correct and
corrected) stays off the statement. The questions never name this rule or hint
the answer; the model must infer it.

**Why the gold is fair with no glossary:** the note bothers to say the error
sales *"must not appear on the royalty statement."* That instruction is only
*necessary* if No-PO sales otherwise **would** appear — i.e. No-PO owes royalty,
so PO does not. The inverted reading makes that sentence redundant, so it's the
worse interpretation. (A human reading it cold gets it; three of four solver
runs did not.)

The note is kept **verbatim**, including its garbled "from PO stocks over to
Normal Stocks" line — no question depends on it.

---

## Cases (7) — 5 traps + 2 floor

All questions are yes/no or a single number, graded by `leading_word` /
`leading_numeric` (+ `no_hedge`). No multiple choice, no glossary, no priming.

| id | gold | what it tests | solver fails |
|---|---|---|---|
| `after_fix_royalty` | **no** | timing — do post-fix (PO) sales bill royalty? | 3/3 |
| `all_off_statement` | **yes** | scope — is the *whole* bundle off the statement? | 2/3 |
| `po_in_royalty` | **no** | rule — should PO SKUs appear on the report? | 1/1 |
| `nonpo_in_royalty` | **yes** | rule — should No-PO SKUs appear on the report? | 1/1 |
| `correct_also_off` | **yes** | does the exclusion extend to the corrected PO SKUs? | 1/1 |
| `the_517_owe` | no | floor — explicitly stated in the note | 0/3 |
| `count_on_statement` | 0 | floor — explicitly stated in the note | 0/3 |

The five trap cases all fail on the same PO-polarity inversion; the two floor
cases are stated outright in the note, so they separate "can read it" from
"actually reasoned it." (Solver-fail rates are from in-session model-eval runs.)

---

## Solution contract

1. Read `INPUTS` (JSON dict: `filename → absolute path`).
2. Read `INPUTS["note.txt"]` (the handover note) and `INPUTS["question.txt"]`.
3. Print the answer to **stdout** (plain text or `{"answer": "..."}`), committing
   to a single answer in the requested format.

≥80% of cases pass → run passes.

---

## Regenerating

```bash
python3 build_cases.py     # rewrites inputs/, expected/, traptask.yaml, gold.cases.json
```

The note text and gold answers both live in `build_cases.py`.
