# Case 5: Finance Q&A — Document-Grounded

**Concept:** "Read this earnings report and answer my question."

A financial question about a real public company goes in, along with the relevant excerpt from their SEC filing. A precise, human-verified answer comes out. Errors are immediately obvious — getting the revenue wrong by $1B is not a gray area.

---

## Dataset

| Field | Value |
|-------|-------|
| Name | FinanceBench |
| GitHub | https://github.com/patronus-ai/financebench |
| HuggingFace ID | `PatronusAI/financebench` |
| Size | 150 open-source Q&A pairs (full dataset: 10,231 — contact Patronus AI) |
| License | CC BY-NC 4.0 (non-commercial) |
| Paper | https://arxiv.org/abs/2311.11944 |
| Coverage | 32 companies, SEC filings (10-K, 10-Q, 8-K, Earnings) |

---

## Input / Output Schema

This is a **document-grounded** task: the model must read the provided financial document excerpt to answer the question. It cannot rely on general knowledge alone — the answer is in the document.

### Input

Two components make up the input:

**1. `question`** — A specific financial question about a named company and fiscal period.

```json
{
  "question": "What is the FY2018 capital expenditure amount (in USD millions) for 3M? Give a response to the question by relying on the details shown in the cash flow statement."
}
```

**2. `evidence[].evidence_text`** — The relevant excerpt extracted from the SEC filing. This is the context the model should read to answer the question.

```json
{
  "evidence_text": "Purchases of property, plant and equipment (PP&E)   (1,577)   (1,373)   (1,420)\n..."
}
```

Each record may have one or more evidence excerpts. `evidence_page_num` gives the zero-indexed page number in the source PDF.

### Output

**Field:** `answer` — The human-annotated gold answer. Precise and unambiguous.

```json
{
  "answer": "$1577.00"
}
```

**Field:** `justification` — Explains where in the document the answer was found and how.

```json
{
  "justification": "The metric capital expenditures was directly extracted from the company 10K. The line item name, as seen in the 10K, was: Purchases of property, plant and equipment (PP&E)."
}
```

### Full example record

```json
{
  "financebench_id": "financebench_id_03029",
  "company": "3M",
  "doc_name": "3M_2018_10K",
  "question": "What is the FY2018 capital expenditure amount (in USD millions) for 3M? Give a response to the question by relying on the details shown in the cash flow statement.",
  "answer": "$1577.00",
  "justification": "The metric capital expenditures was directly extracted from the company 10K. The line item name, as seen in the 10K, was: Purchases of property, plant and equipment (PP&E).",
  "question_type": "metrics-generated",
  "question_reasoning": "Information extraction",
  "evidence": [
    {
      "evidence_text": "Purchases of property, plant and equipment (PP&E)   (1,577)   ...",
      "doc_name": "3M_2018_10K",
      "evidence_page_num": 59,
      "evidence_text_full_page": "..."
    }
  ]
}
```

---

## Data Files

The data is committed directly in this repo (150 examples, small enough to store):

| File | Description |
|------|-------------|
| [`data/financebench_open_source.jsonl`](./data/financebench_open_source.jsonl) | 150 Q&A pairs with questions, answers, justifications, and evidence excerpts |
| [`data/financebench_document_information.jsonl`](./data/financebench_document_information.jsonl) | Metadata for each source document: company, doc type, fiscal period, and a direct PDF link |

---

## How to Use the Data

### Python — load and join

```python
import json
import pandas as pd

with open("data/financebench_open_source.jsonl") as f:
    questions = [json.loads(line) for line in f]

with open("data/financebench_document_information.jsonl") as f:
    doc_info = {json.loads(line)["doc_name"]: json.loads(line) for line in f}

# Enrich each question with document metadata (including PDF link)
for q in questions:
    q["doc_meta"] = doc_info.get(q["doc_name"], {})

# Access a question
example = questions[0]
input_question  = example["question"]
input_evidence  = example["evidence"][0]["evidence_text"]   # feed this as context
output_answer   = example["answer"]
source_pdf      = example["doc_meta"].get("doc_link")       # URL to the actual SEC filing
```

### Python — HuggingFace datasets

```python
from datasets import load_dataset

ds = load_dataset("PatronusAI/financebench")
example = ds["train"][0]
```

### Accessing source PDFs

Each document in `financebench_document_information.jsonl` has a `doc_link` field pointing to the original SEC filing PDF. Use `evidence_page_num` (zero-indexed) to navigate to the exact page.

```python
pdf_url  = doc_info["3M_2018_10K"]["doc_link"]
page_num = questions[0]["evidence"][0]["evidence_page_num"]  # 59
```

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

- **Why document-grounded matters:** the model must locate and reason over a specific table or paragraph in a dense financial document. General knowledge is insufficient — the numbers change every quarter.
- **Errors are high-stakes and unambiguous:** getting revenue or capex wrong by even 1% is clearly wrong. No gray area.
- **Metric:** Exact match or token-level F1 against `answer`. Numeric normalization recommended (e.g. "$1,577" == "$1577.00").
- **Use all 150 examples** — the dataset is already small and every question is human-verified.
- **Full dataset:** 10,231 questions available by contacting contact@patronus.ai.
