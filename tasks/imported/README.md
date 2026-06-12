# Imported benchmarks

Third-party open benchmarks adapted into the trapstreet task format. These are
**not** original trapstreet traps — they're commodity/calibration imports that
add breadth and a baseline floor. Each subdir vendors a small, fixed slice of an
upstream dataset under a permissive (commercial-OK) license, with an
`ATTRIBUTION.md` reproducing the required notice.

Every import is regenerated from its `build_cases.py` (fetches upstream at build
time, then vendors files so the task is self-contained afterward).

## Available now (static Q&A → deterministic judge)

| task | source | license | cases | grading |
|---|---|---|---|---|
| `gsm8k` | openai/grade-school-math | MIT | 25 | `leading_numeric` (final number) |
| `mmlu` | cais/mmlu · hendrycks/test | MIT | 25 (23 subjects) | `leading_word` (letter A–D) |

Both reuse the matcher-based `judge.py`/`grader.py` from `pdf_reader`.

## Why only these two (feasibility, not licensing)

The other 🟢 permissive benchmarks are **execution-environment agent
benchmarks** — they can't be vendored as `question.txt` / `answer.json`; they
need Docker images, live browsers, OS VMs, or gated downloads, and integrating
them means your harness shells out to *their* harness. That's a separate,
larger engineering effort (a "harness adapter"), not a file drop-in:

| benchmark | license | why it needs a harness adapter |
|---|---|---|
| SWE-bench | MIT | per-task Docker repo build + test execution |
| WebArena | Apache-2.0 | live web app sandboxes |
| OSWorld | Apache-2.0 (code) | full OS virtual machines |
| TheAgentCompany | MIT | self-hosted company services (GitLab/Plane/etc.) |
| GAIA / Gaia2 | ODC-By / CC-BY-4.0 | tool use + **gated** HF download (auth) |
| DELEGATE-52 | MIT | multi-step reversible edits — design already adapted in `../doc_editing` |

To add one of these, the pattern is: a task dir whose `judge.py` is a thin
**adapter** that invokes the upstream evaluator (fetched at runtime, never
re-hosted) and maps its verdict to a trapstreet score, plus an `ATTRIBUTION.md`.

## License hygiene

- Permissive ≠ no obligations: MIT/Apache/CC-BY/ODC-By all require keeping the
  notice — see each `ATTRIBUTION.md`.
- We vendor **subsets**, unmodified question/answer content, with the source and
  license recorded per task and per `answer.json` (`_source`).
- Anything **NonCommercial** (XSCT, FinanceBench open subset) or
  **unlicensed** (SpreadsheetBench) is deliberately **not** here — mine those
  for ideas and author originals instead.
