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

**The conflicting signal:** a shallow read goes *"No-PO SKUs were sold → No-PO
owes royalty → put them on the statement."* That's backwards — the correction
makes them PO, so **no royalty**. A model that over-reasons from the default
rule fails the two `royalty` cases.

The note is kept **verbatim** (including its garbled "from PO stocks over to
Normal Stocks" migration line — the real mess). No question depends on that
line, so the ambiguity can't make a gold answer unfair.

---

## Cases (5)

| id | category | difficulty | gold | what it tests |
|---|---|---|---|---|
| `royalty_inclusion` | royalty | hard | **No** | core trap — question primes the default rule; correct answer inverts it |
| `royalty_count` | royalty | hard | **0** | false-premise / honesty — anchors a model on 517 |
| `affected_count` | extraction | easy | 517 | baseline extraction |
| `correction_time` | extraction | easy | 10:15 on 21/05/2026 | baseline extraction |
| `affected_titles` | extraction | easy | Coffee Talk, Coffee Talk Episode 2 | baseline extraction |

The two `royalty` cases are the trap; the three `extraction` cases set an easy
floor so the score separates "can read it" from "actually understood it".

A genuine "why is it excluded?" reasoning case was intentionally **left out** —
free-text justification can contain the right keywords while reaching the wrong
conclusion, so it needs an LLM-judge this matcher-based task doesn't use.

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
