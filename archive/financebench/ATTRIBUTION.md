# Attribution — FinanceBench

This task vendors 5 questions from **FinanceBench**.

- **Source (data):** https://huggingface.co/datasets/PatronusAI/financebench
- **Intermediate:** https://huggingface.co/datasets/Ruqii/trapstreet-cases
- **Curator:** Patronus AI
- **License:** Creative Commons Attribution-NonCommercial 4.0 International (**CC BY-NC 4.0**)
- **What we use:** 5 questions + their supporting 10-K excerpt + gold answer,
  reproduced unmodified — Netflix 2017, AES 2022, 3M 2018, Walmart 2018,
  Block 2016.

## Why this isn't in `tasks/imported/`

[`../imported/README.md`](../imported/README.md) deliberately excludes
FinanceBench from the permissive-license import set ("mine those for ideas
and author originals instead") because CC BY-NC 4.0 forbids commercial use,
and `imported/` is scoped to benchmarks cleared for unrestricted use on the
public trapstreet.run leaderboard.

This copy is kept here anyway, at the project owner's direction, purely to
consolidate what used to be a separate standalone repo
(`trapstreet/financebench`) into this monorepo — **not** to publish it as an
official trapstreet.run task. If that changes, this needs a fresh look at
the NC restriction first.

## License notice (CC BY-NC 4.0 — reproduced as required)

FinanceBench is licensed under the Creative Commons
Attribution-NonCommercial 4.0 International License. To view a copy of this
license, visit http://creativecommons.org/licenses/by-nc/4.0/.

> FinanceBench © Patronus AI, licensed under CC BY-NC 4.0.
> Underlying documents are public SEC 10-K filings.
