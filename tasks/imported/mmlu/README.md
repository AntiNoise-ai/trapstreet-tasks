# MMLU (imported)

Multiple-choice knowledge questions across diverse subjects — a deterministic
letter-answer import. See [`ATTRIBUTION.md`](ATTRIBUTION.md) (MMLU, MIT) and
[`../README.md`](../README.md) for provenance and license hygiene.

- **Cases:** 25, sampled at even offsets across the `test` split (≈23 subjects).
- **Lane:** model-eval (knowledge recall, no tools).
- **Contract:** read `INPUTS["question.txt"]` (question + options A–D), print
  **only the letter** (A/B/C/D) to stdout. Graded by a `leading_word` matcher
  (reused from `pdf_reader`).
- **Note:** commodity/calibration benchmark — near-saturated for frontier
  models. It's a baseline floor, not a trap.

Regenerate (fetches upstream):

```bash
python3 build_cases.py --n 25
```
