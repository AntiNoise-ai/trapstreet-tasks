# TrapStreet Tasks

Standardized eval cases for the TrapStreet platform. Each case defines a clear **input** (what gets sent to the model) and **output** (what the correct answer looks like), sourced from public, human-labeled datasets.

---

## Cases

| # | Name | Dataset | Input | Output |
|---|------|---------|-------|--------|
| 2 | [Article Summarization](#case-2-article-summarization) | CNN/DailyMail | News article | Bullet-point summary |
| 4 | [Everyday Q&A](#case-4-everyday-qa) | TriviaQA | Trivia question | Short factual answer |
| 5 | [Finance Q&A](#case-5-finance-qa--document-grounded) | FinanceBench | Financial question + SEC filing PDF | Exact dollar/number answer |

---

## How to use

Each case folder has its own README with the full schema. The pattern is the same for all cases:

1. **Download the data** using the links in each case folder.
2. **Pick the right split** — always use `test` (or `validation` where noted). Never use `train`.
3. **Feed each row to your model:** the `input` field goes in, the model's response comes out.
4. **Compare the model's response** against the `output` field to score it.

> **Why test/validation and not train?**
> The train split was used to build the models being evaluated — they've already seen it. Test and validation are held-out data the models were never supposed to optimize for, making them the only fair basis for comparison.

---

## Case 2: Article Summarization

**"Too long, didn't read — give me the key points."**

| | |
|---|---|
| Dataset | CNN/DailyMail |
| Full case doc | [case2_article_summarization/](./case2_article_summarization/) |
| Data (test split, 1 file) | https://huggingface.co/api/datasets/abisee/cnn_dailymail/parquet/3.0.0/test/0.parquet |

| Role | Field | Description |
|------|-------|-------------|
| Input | `article` | Full news article text |
| Output | `highlights` | Journalist-written bullet summary (newline-separated) |

**Quick start:**
```python
import pandas as pd

df = pd.read_parquet("https://huggingface.co/api/datasets/abisee/cnn_dailymail/parquet/3.0.0/test/0.parquet")

input_text  = df["article"][0]      # → send to model
output_text = df["highlights"][0]   # → compare against model response
```

---

## Case 4: Everyday Q&A

**"Using AI as a smarter Google."**

| | |
|---|---|
| Dataset | TriviaQA |
| Full case doc | [case4_everyday_qa/](./case4_everyday_qa/) |
| Data (validation split, file 0 of 5) | https://huggingface.co/api/datasets/mandarjoshi/trivia_qa/parquet/unfiltered/validation/0.parquet |

> Use `validation` here, not `test` — TriviaQA's test split has no public gold answers.

| Role | Field | Description |
|------|-------|-------------|
| Input | `question` | Plain-language trivia question |
| Output | `answer.value` | Primary correct answer |
| Output (flexible) | `answer.aliases` | All accepted phrasings (e.g. "Paris", "City of Paris") |

**Quick start:**
```python
import pandas as pd

df = pd.read_parquet("https://huggingface.co/api/datasets/mandarjoshi/trivia_qa/parquet/unfiltered/validation/0.parquet")

input_text     = df["question"][0]             # → send to model
output_value   = df["answer"][0]["value"]      # → primary answer
output_aliases = df["answer"][0]["aliases"]    # → all valid answers
```

---

## Case 5: Finance Q&A — Document-Grounded

**"Read this earnings report and answer my question."**

| | |
|---|---|
| Dataset | FinanceBench |
| Full case doc | [case5_finance_qa/](./case5_finance_qa/) |
| Questions + answers | https://raw.githubusercontent.com/patronus-ai/financebench/main/data/financebench_open_source.jsonl |
| Document metadata (PDF links) | https://raw.githubusercontent.com/patronus-ai/financebench/main/data/financebench_document_information.jsonl |

This case is **document-grounded**: the model must read an actual SEC filing PDF (10-K, 10-Q, etc.) to find the answer. It can't rely on general knowledge — the numbers change every quarter.

| Role | Field | Source file |
|------|-------|-------------|
| Input | `question` | `financebench_open_source.jsonl` |
| Input | `doc_link` (the SEC filing PDF) | `financebench_document_information.jsonl`, joined on `doc_name` |
| Output | `answer` | `financebench_open_source.jsonl` |

**Quick start:**
```python
import json, urllib.request

def load_jsonl(url):
    with urllib.request.urlopen(url) as f:
        return [json.loads(line) for line in f]

questions = load_jsonl("https://raw.githubusercontent.com/patronus-ai/financebench/main/data/financebench_open_source.jsonl")
doc_info  = {d["doc_name"]: d for d in load_jsonl("https://raw.githubusercontent.com/patronus-ai/financebench/main/data/financebench_document_information.jsonl")}

example = questions[0]

input_question = example["question"]
input_pdf_url  = doc_info[example["doc_name"]]["doc_link"]  # → send question + this PDF to model
output_answer  = example["answer"]                          # → compare against model response
```

---

## Criteria

All cases are selected to meet the following bar:

- **No-tech friendly** — the concept is immediately obvious to any user
- **Universal** — no special setup, domain knowledge, or environment needed
- **Fast** — each example runs in seconds
- **Standardized** — public datasets with existing human-labeled input/output pairs, no custom annotation needed
