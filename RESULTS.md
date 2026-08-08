# Results

What these tasks have measured so far. Every number is a real run submitted through `tp`,
pinned to a public `repo@commit`, and re-runnable — click any board to see the run and its
source. Regenerate this file from the API; do not hand-edit.

> Runs marked *provisional* on the site have been reproduced by fewer than three independent
> users. Most rows here are provisional: treat them as one careful measurement, not a verdict.

## Reading a PDF with an LLM

Four boards, four documents, several approaches: hand the model the PDF directly
(`claude-pdf`), or pre-extract text with a parser (`mineru`, `docling`, `pdf-inspector`) and
hand it that. Cost and latency vary far more than score.


### [pdf-mixed-scan](https://trapstreet.run/tasks/pdf-mixed-scan)

Half the document has no text layer, so OCR matters. Same model throughout, so the only variable is the parser.

| # | Solution | Engine | Score | Cases | Latency | Cost |
|---|---|---|---|---|---|---|
| 1 | `pdf-mixed-scan-docling-ocr` | claude-sonnet-5 | **0.9** | 18/20 | 602s | $0.677 |
| 2 | `pdf-mixed-scan-mineru` | claude-sonnet-5 | **0.9** | 18/20 | 140s | $0.761 |
| 3 | `pdf-mixed-scan-claude-pdf` | claude-sonnet-5 | **0.85** | 17/20 | 113s | $0.026 |
| 4 | `pdf-mixed-scan-pdf-inspector` | claude-sonnet-5 | **0.35** | 7/20 | 107s | $0.272 |

### [pdf-tables](https://trapstreet.run/tasks/pdf-tables)

Wide, repetitive tables — the failure mode is reading a value from the wrong row.

| # | Solution | Engine | Score | Cases | Latency | Cost |
|---|---|---|---|---|---|---|
| 1 | `pdf-tables-claude-pdf` | claude-opus-4-7 | **0.95** | 19/20 | 84s | $0.015 |
| 2 | `pdf-tables-pdf-inspector-vanilla` | claude-sonnet-4-6 | **0.85** | 17/20 | 82s | $0.903 |

### [pdf-reader-v2](https://trapstreet.run/tasks/pdf-reader-v2)

A UK tenancy agreement: rent, dates, clauses.

| # | Solution | Engine | Score | Cases | Latency | Cost |
|---|---|---|---|---|---|---|
| 1 | `pdf-reader-mineru` | claude-sonnet-4-6 | **1** | 20/20 | 1266s | $1.087 |
| 2 | `pdf-reader-pdf-inspector-deshift` | claude-sonnet-4-6 | **1** | 20/20 | 110s | $1.223 |
| 3 | `pdf-reader-pdf-inspector-vanilla` | claude-sonnet-4-6 | **0.7** | 14/20 | 129s | $2.569 |

### [pdf-reader](https://trapstreet.run/tasks/pdf-reader)

Legal contract review. Superseded by pdf-reader-v2; kept for its run history.

| # | Solution | Engine | Score | Cases | Latency | Cost |
|---|---|---|---|---|---|---|
| 1 | `smolagents-claude-split` | claude-opus-4-7 (vision) + sonnet-4-6 (planner) + smolagents | **0.947** | 18/19 | 265s | $4.723 |
| 2 | `smolagents-claude-v2` | claude-opus-4-7 + smolagents | **0.947** | 18/19 | 248s | $7.508 |
| 3 | `claude-pdf` | claude-opus-4-7 | **0.895** | 17/19 | 69s | $3.684 |
| 4 | `mineru-claude` | — | **0.842** | 16/19 | 40s | $0.920 |
| 5 | `docling-claude` | docling + claude-opus-4-7 | **0.632** | 12/19 | 147s | $1.695 |
| 6 | `smolagents-claude` | claude-opus-4-7 + smolagents | **0.158** | 3/19 | 213s | $6.150 |

### What the numbers say

On `pdf-mixed-scan` the top two parsers tie at 0.90. Handing the PDF straight to the model
scores 0.85 — one case behind — for **$0.026 a run against $0.68 and $0.76** — 26× and 29× less — and it
finishes in 113s where the winner takes 602s. Whether 0.05 of accuracy is worth 26× the cost
is a decision only you can make, but you cannot make it without the numbers.

The ordering is not stable across documents. `pdf-inspector` places last on `pdf-mixed-scan`
(0.35) and ties for first on `pdf-reader-v2` (1.0, in its `deshift` variant) — the scanned
pages it cannot read are the whole point of the first task and absent from the second. **A parser is not good or bad; it is good
or bad on your documents.** Which is the argument for running these against your own, rather
than reading someone's benchmark.

## Reproducing any row

Every entry links to its solution repo at the exact commit. To re-run one:

```bash
uv tool install trap-cli
git clone <the solution repo> && cd <it>
tp run
```

The task is pinned in that solution's `trap.yaml`, so you get the same cases and the same
judge. Full walkthrough: [trapstreet.run/docs](https://trapstreet.run/docs/quick-start).

## Adding to this

Pick a board and submit a run, or write a task for something nobody has measured yet — see
[Build your own task](./README.md#build-your-own-task).

