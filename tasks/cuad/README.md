# CUAD — legal contract clause extraction

Real commercial contracts (SEC EDGAR material agreements) go in; the model must
return the **exact clause span** for one of 41 clause types — or correctly say the
clause is **absent**. See [`ATTRIBUTION.md`](ATTRIBUTION.md) (CUAD, CC BY 4.0) for
provenance and license hygiene.

This revives the archived [`case12_legal_clause_extraction`](../../archive/case12_legal_clause_extraction/)
exploration as a runnable task.

## The two traps

| Kind | gold | matcher | failure it catches |
|---|---|---|---|
| **present** | real clause span(s) | `span_f1` | **laziness** — confidently saying "no clause found" when one is plainly there |
| **absent** | empty | `no_clause` | **hallucination** — inventing a span / citing a clause that isn't there |

Categories are paired: the same clause type appears both present (in a contract
that has it) and absent (in one that doesn't), so a model can't pattern-match
"this category is always there / never there."

- **Cases:** 20 present + 12 absent (default), priority-ordered toward the subtle,
  frequently-misread clauses (Anti-Assignment, Change of Control, Most Favored
  Nation, Cap on Liability, …).
- **Lane:** document-grounded extraction. Contracts run 10–80k chars — also a
  long-context test in disguise.
- **Contract:** read `INPUTS["question.txt"]` (full contract + question + format
  instruction); output the exact span(s) **or** `NO CLAUSE FOUND`. Nothing else.

## Grading

- `span_f1` — pass if `max(token-F1, containment)` against **any** gold span ≥ 0.5.
  Token-F1 uses SQuAD normalisation; containment lets a verbatim quote pass even
  with surrounding commentary.
- `no_clause` — pass if the answer asserts absence ("NO CLAUSE FOUND", "does not
  contain", "no such provision", "none", …).
- The grader reports overall accuracy plus two diagnostics:
  - `recall_present` — accuracy on present rows (low = lazy).
  - `precision_absent` — accuracy on absent rows (low = hallucinating).

## Why this is the Mike (mikeoss.com) wedge

CUAD maps almost 1:1 onto an open-source legal-AI tool's flagship feature:
contract in → tabular review with one column per clause type → each cell an
extracted span cited to the source. The `absent` rows directly stress-test the
"every cell cited, no hallucinated answers, no dead links" claim.

## Regenerate (fetches upstream `data.zip`, ~17 MB, cached in `.cache/`)

```bash
python3 build_cases.py                      # 20 present + 12 absent
python3 build_cases.py --present 25 --absent 16
```

## Test the judge

```bash
python3 -m pytest test_judge.py -q          # or: python3 test_judge.py via the repo runner
```
