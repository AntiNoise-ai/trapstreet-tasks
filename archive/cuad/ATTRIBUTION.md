# Attribution — CUAD

This task vendors a subset of **CUAD** (Contract Understanding Atticus Dataset).

- **Source (data):** https://huggingface.co/datasets/theatticusproject/cuad
- **Eval-ready (SQuAD format):** https://huggingface.co/datasets/theatticusproject/cuad-qa
- **Source (original):** https://github.com/TheAtticusProject/cuad
- **Paper:** Hendrycks, Burns, Chen, Ball, "CUAD: An Expert-Annotated NLP Dataset
  for Legal Contract Review", NeurIPS 2021 (arXiv:2103.06268)
- **Curator:** The Atticus Project
- **License:** Creative Commons Attribution 4.0 International (**CC BY 4.0**)
- **What we use:** a fixed, balanced slice of the official `test` split —
  20 *present* + 12 *absent* (question, contract context, gold span) triples,
  fetched at build time by `build_cases.py` from the CUAD GitHub release
  (`data.zip` → `test.json`). Contract text, questions, and gold spans are
  reproduced **unmodified**; we only append an output-format instruction to each
  question and select the slice.

## License notice (CC BY 4.0 — reproduced as required)

CUAD is licensed under the Creative Commons Attribution 4.0 International License.
To view a copy of this license, visit http://creativecommons.org/licenses/by/4.0/.

> CUAD © The Atticus Project, licensed under CC BY 4.0.
> Underlying contracts are public material agreements filed on SEC EDGAR.

CC BY 4.0 permits sharing and adaptation (including commercial use and
redistribution on a public leaderboard) provided attribution is given, a link to
the license is provided, and changes are indicated. The only change made here is
the selection of a subset and the addition of an output-format instruction to the
prompt; the source data is otherwise unmodified.
