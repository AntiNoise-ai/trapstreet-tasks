# Tenancy Agreement — PDF Reader v2

A hardened fork of [`../pdf_reader`](../pdf_reader). Same document, same judge
and grader, v1's 19 questions plus one new one. What changed is that the
questions no longer give away what the judge scores on, and the source PDF is
actually redacted.

`pdf_reader` is left untouched — its leaderboard history stays valid and
comparable against itself. This is a separate task, and results are **not**
comparable across the two: v2 is strictly harder.

## Why this fork exists

Four of v1's 19 cases could be scored without opening the PDF, because the
question text already contained every literal the judge required:

| v1 case | what the question said | gold answer |
|---|---|---|
| `governing_act` | `(e.g. 'Housing Act 1988')` | Housing Act 1988 |
| `late_rent_interest_rate` | `(e.g. '3% above Bank of England base rate')` | 3% above BoE base rate |
| `pets_allowed` | `Answer yes, no, or 'with landlord consent'` | with landlord consent |
| `rent_increase_scope` | `...the original fixed term, the automatic extension period, or both?` | the automatic extension period only |

In each, echoing the prompt satisfied every content matcher. A fifth case,
`scenario_leave_22mo_replacement_1mo_gap`, stated `13.2%`, `£144`, `£480` and
the 36-month term in the prompt — all four are in Section 6 / clause 1.8 of the
PDF, so the case tested arithmetic rather than document reading.

These survived four task revisions of prose review. So v2 checks it
mechanically instead: `build_cases.py` refuses to build a case where every
content matcher is already satisfied by the question text. Run it against v1
and it flags exactly those four (`tests/test_build.py::test_regression_v1_leaks_would_be_caught`
pins that).

## What changed, case by case

Everything is recorded in `gold.cases.json` under `_deleak` / `_leak_ack` keys
next to the case it applies to. Summary:

- **`case_14`** (was `late_rent_interest_rate`) — format example dropped;
  "exactly as written" carries the requirement.
- **`case_15`** (was `governing_act`) — example replaced with a different Act,
  **and** the case re-anchored to the section number cited in clause 1.13.
  *This is the one case whose gold answer changed* (`Housing Act 1988` →
  `Housing Act 1988, Section 19A`), because "Housing Act 1988" is the textbook
  answer for any AST and was passable closed-book. Revert the answer and the
  `19A` matcher together if you want v1 parity.
- **`case_12`** (was `pets_allowed`) — the option list, whose third entry was
  the answer, is gone; now asks for one short sentence.
- **`case_10`** (was `rent_increase_scope`) — question unchanged (a 3-way
  multiple choice has to name its options), matcher tightened to require an
  exclusivity marker (`only` / `solely` / `not the fixed term`), none of which
  appear in the prompt. Gold answer unchanged.
- **`case_18`** (was `scenario_leave_22mo…`) — the four constants removed. The
  components (a)–(d) are still named so the case stays gradeable against one
  total; the numbers must come from Section 6.
- **`case_02`**, **`case_13`** — incidental term-length and rent-structure
  hints removed.
- **`case_20`** — new, no v1 equivalent. `case_18` names its four cost
  components in the prompt, which buys gradeability against a single number but
  hands over the "which charges apply" step. Section 6 in fact lists **five**;
  `case_18` omits the rent-shortfall item because it is £0 in that scenario.
  `case_20` tests the step `case_18` gives away — enumerate all five and state
  the scaling basis for the two that are pro-rated. A list question grades
  naturally on keywords where a single-number question cannot.
  Anti-shotgun: the first five matchers are reachable by listing plausible
  charges from general UK tenancy knowledge, so the sixth — the scaling basis,
  "the number of months to be surrendered early as a percentage of the current
  fixed term" — is the guard. It is specific to this document.
  `tests/test_judge.py::test_case_20_generic_list_without_the_scaling_basis_fails`
  pins it.
- **All cases** — ids are now opaque (`case_01`…`case_20`). A solution can read
  its own `TRAP_MANIFEST["inputs_dir"]`, so ids like `pets_allowed` or
  `break_clause` handed over the topic for free. Real names live in `label`.

## Input

Per case:
- `inputs/<case_id>/question.txt` — one-line question
- `inputs/<case_id>/document.pdf` — the AST PDF (~470 KB, identical across all 20)

## Expected output

Plain text on **stdout**, or `{"answer": "..."}` JSON. The judge is unchanged
from v1 and still harsh: commit to one answer, match any stated format, answer
every part of a multi-part question, show working where asked. 1.0 or 0.0 per
case, no partial credit. A run passes at ≥80%.

## Build

```bash
python3 build_cases.py && uv run --with pytest python -m pytest tests/ -q
```

`inputs/` and `expected/` are generated — edit `gold.cases.json`, never them.
`build_cases.py` prints one acknowledged partial overlap (`case_10`); a *fatal*
leak fails the build.

## Known limitations (inherited from v1, not fixed here)

- **One document across all 20 cases.** Parse cost amortises to near-zero after
  the first case, so the cost figure on the leaderboard understates what a
  20-distinct-document run would cost. The task measures "can you read *this*
  contract", not "can you read contracts".
- **Five cases are yes/no** (3 gold `yes`, 2 gold `no`). Answering `yes` to
  everything scores 3/20 = 15%, far below the 80% threshold, so guessing is not
  a route to passing — but treat the `clauses` category score as weaker
  evidence than `money` or `scenario`.
- **`case_10`'s "extension" overlap** is acknowledged, not eliminated — see
  `_leak_ack` in the gold.
- **`expected/` is reachable from the solution's own `inputs_dir`.** trap hands
  the solution an absolute `inputs_dir`, and `../../expected/<case_id>/answer.json`
  resolves and is readable — and this repo is public besides. Nothing in the
  task can prevent that; it's a property of the harness, shared by every task
  here. Noted so scores are read with it in mind rather than mistaken for a
  v2-specific hole.
- **`case_18` uses the `numeric` matcher** ("any number in the answer counts"),
  which show-your-working requires but which is weak against a solution that
  enumerates candidate totals. No anti-shotgun cap is applied.
- **`case_18` names its four cost components**, so it does not test which of
  Section 6's five charges apply — that scope was traded away for a gradeable
  single number. `case_20` covers the gap; neither case covers it alone.
- **Never run end to end.** `build_cases.py`, the test suite and
  `validate_task.py` all pass, but no solution has executed against v2 and it
  is not registered on trapstreet.run, so nothing can submit against it yet.
  Difficulty and discrimination are untested empirically.

## Source document

A real UK Assured Shorthold Tenancy. **The copy shipped here is redacted; v1's
is not.**

v1's PDF has 15 black rectangles *painted over* names, addresses, emails, phone
numbers and signatures. Painting hides pixels — the text stays in the content
stream and comes straight back out of `extract_text()`. It reads as safe
because the DocuSign font subset is shifted by −29 codepoints, so raw
extraction looks like mojibake; the shift auto-detects in a few lines. Two
further pages had no box at all: page 11 clause 5.4c (both tenant emails) and
page 15 (the premises address) were plainly visible on screen.

`tools/apply_redactions.py` fixes both: it removes the text under every box via
`apply_redactions()` and repaints the box, and covers the two missed regions.
Redaction is whole-line — word-level was tried and leaked twice: an email's
domain fragment stops matching any email pattern once the local part is gone,
and a postcode's two halves are separate word boxes. The cost is one cosmetic over-redaction on page 11,
where clause 5.4c loses some trailing prose. No case asks about 5.4c.

```bash
python3 tools/apply_redactions.py <unredacted>.pdf AST_tenancy_redacted.pdf
```

`tests/test_pdf_redaction.py` is the standing guard: it deshifts the text layer
and asserts no personal token, mobile number, residential postcode or personal
email survives, **and** that the redaction didn't eat any gold-answer evidence.
Point it at v1's PDF and 18 of its assertions fail. It also asserts the deshift
still yields readable English first, so the PII checks can't pass vacuously
against mojibake.

Business contact details (letting agent, TDS, OVO, the banks) are deliberately
kept — they aren't personal data, and "The Dispute Service" is the gold answer
to `case_11`.

Applying the same fix to v1 does **not** undo its exposure: the unredacted file
is in the public repo's git history across five commits since 2026-05-11. That
needs history rewriting, which is a separate decision.
