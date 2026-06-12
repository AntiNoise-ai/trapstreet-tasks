# GSM8K (imported)

Grade-school math word problems — a deterministic numeric-answer import. See
[`ATTRIBUTION.md`](ATTRIBUTION.md) (GSM8K, MIT, © 2021 OpenAI) and
[`../README.md`](../README.md) for provenance and license hygiene.

- **Cases:** 25 (first 25 of the GSM8K `test` split).
- **Lane:** model-eval (reasoning, no tools).
- **Contract:** read `INPUTS["question.txt"]`, solve, print **only the final
  number** to stdout. Graded by a `leading_numeric` matcher (reused from
  `pdf_reader`).
- **Note:** commodity/calibration benchmark — near-saturated for frontier
  models. It's a baseline floor, not a trap.

Regenerate (fetches upstream):

```bash
python3 build_cases.py --n 25
```
