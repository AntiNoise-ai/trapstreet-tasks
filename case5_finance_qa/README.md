# Case 5: Finance Q&A — Document-Grounded

> Live demo flow for this case: see [DEMO.md](./DEMO.md).

**Concept:** "Read this SEC filing and answer my question."

A financial question about a real public company goes in, along with the full SEC filing PDF. A precise, human-verified answer comes out. Errors are immediately obvious — getting revenue wrong by $1B is not a gray area.

---

## Dataset

| Field | Value |
|-------|-------|
| Name | FinanceBench |
| GitHub | https://github.com/patronus-ai/financebench |
| HuggingFace | https://huggingface.co/datasets/PatronusAI/financebench |
| Size | 150 open-source Q&A pairs (full dataset: 10,231 — contact Patronus AI) |
| License | CC BY-NC 4.0 (non-commercial) |
| Paper | https://arxiv.org/abs/2311.11944 |
| Coverage | 32 companies, SEC filings (10-K, 10-Q, 8-K, Earnings) |

---

## Input / Output Schema

This is a **document-grounded** task: the model receives the full SEC filing PDF and must locate the relevant information itself.

### Input

Two components:

**1. `question`** — A specific financial question about a named company and fiscal period.

```json
{
  "question": "What is the FY2018 capital expenditure amount (in USD millions) for 3M? Give a response to the question by relying on the details shown in the cash flow statement."
}
```

**2. `doc_link`** (from `financebench_document_information.jsonl`) — Direct URL to the SEC filing PDF. The model reads this document to find the answer.

```json
{
  "doc_link": "https://investors.3m.com/financials/sec-filings/content/0001558370-19-002345/0001558370-19-002345.pdf"
}
```

Join on `doc_name` to get the PDF link for each question.

### Output

**Field:** `answer` — Human-annotated gold answer. Precise and unambiguous.

```json
{
  "answer": "$1577.00"
}
```

**Field:** `justification` — Explains where in the document the answer was found.

```json
{
  "justification": "The metric capital expenditures was directly extracted from the company 10K. The line item name, as seen in the 10K, was: Purchases of property, plant and equipment (PP&E)."
}
```

---

## Data Sources

No data is stored in this repo. Get it directly from:

| File | URL |
|------|-----|
| Questions + answers | https://raw.githubusercontent.com/patronus-ai/financebench/main/data/financebench_open_source.jsonl |
| Document metadata (PDF links) | https://raw.githubusercontent.com/patronus-ai/financebench/main/data/financebench_document_information.jsonl |

Each PDF is linked directly in `financebench_document_information.jsonl` via the `doc_link` field — no login or scraping needed.

---

## Dataset Stats

| Metric | Value |
|--------|-------|
| Total questions | 150 |
| Unique companies | 32 (3M, Adobe, Amazon, AMD, American Express, ...) |
| Question types | `metrics-generated`, `domain-relevant`, `novel-generated` |
| Reasoning required | Information extraction, Numerical reasoning, Logical reasoning |
| Document types | 10-K, 10-Q, 8-K, Earnings releases |

---

## Eval Notes

- **Why PDF-grounded matters:** the model must retrieve and reason over the right section of a dense financial document. General knowledge is insufficient — the numbers change every quarter.
- **Errors are unambiguous:** wrong by even 1% is clearly wrong. No gray area.
- **Metric:** Exact match or token-level F1 against `answer`. Numeric normalization recommended (e.g. `"$1,577"` == `"$1577.00"`).
- **Use all 150 examples** — the dataset is small and every question is human-verified.
- **Full dataset:** 10,231 questions available by contacting contact@patronus.ai.
