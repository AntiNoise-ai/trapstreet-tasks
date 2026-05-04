# Case 2: Article Summarization

**Concept:** "Too long, didn't read — give me the key points."

A full news article goes in. A concise, human-written bullet summary comes out. The quality gap between a good and bad summary is immediately obvious to any reader.

---

## Dataset

| Field | Value |
|-------|-------|
| Name | CNN/DailyMail |
| HuggingFace ID | `abisee/cnn_dailymail` |
| Version | `3.0.0` |
| Size | ~300k articles (train + val + test) |
| License | Apache 2.0 |
| HuggingFace URL | https://huggingface.co/datasets/abisee/cnn_dailymail |

---

## Input / Output Schema

### Input

**Field:** `article`

The full text of a news article, as published by CNN or the Daily Mail. Typically 300–800 words. No preprocessing needed.

```json
{
  "article": "LONDON, England (Reuters) -- Harry Potter star Daniel Radcliffe gains access to a reported £20 million ($41.1 million) fortune as he turns 18 on Monday, but he insists the money won't change him. Daniel Radcliffe as he appears in \"Harry Potter.\" © 2007 Warner Bros. Ent. Harry Potter Publishing Rights © J.K.R. Note the use of ™ on the Warner Bros. ... (full article text)"
}
```

### Output

**Field:** `highlights`

Journalist-written bullet highlights for the article, separated by `\n`. Each bullet is a standalone key fact. These are the ground-truth labels.

```json
{
  "highlights": "Harry Potter star Daniel Radcliffe is turning 18 on Monday.\nHe has access to a reported £20 million ($41.1 million) fortune.\nHis manager says he intends to donate much of his money to charity."
}
```

### Full example record

```json
{
  "id": "42c027e4ff9730fbb3de84c1af0d2c506e41c3e4",
  "article": "LONDON, England (Reuters) -- Harry Potter star Daniel Radcliffe...",
  "highlights": "Harry Potter star Daniel Radcliffe is turning 18 on Monday.\nHe has access to a reported £20 million ($41.1 million) fortune.\nHis manager says he intends to donate much of his money to charity."
}
```

---

## How to Access the Data

### Python (HuggingFace `datasets` library)

```python
from datasets import load_dataset

ds = load_dataset("abisee/cnn_dailymail", "3.0.0")

# Splits: train (287,113), validation (13,368), test (11,490)
example = ds["test"][0]

input_text  = example["article"]
output_text = example["highlights"]
```

### Direct file download (Parquet)

Download individual Parquet files directly — no library needed. Use `pandas.read_parquet()` or any Parquet reader.

**Test split** (11,490 rows, recommended for demos — 1 file):
```
https://huggingface.co/api/datasets/abisee/cnn_dailymail/parquet/3.0.0/test/0.parquet
```

**Validation split** (13,368 rows — 1 file):
```
https://huggingface.co/api/datasets/abisee/cnn_dailymail/parquet/3.0.0/validation/0.parquet
```

**Train split** (287,113 rows — 3 files):
```
https://huggingface.co/api/datasets/abisee/cnn_dailymail/parquet/3.0.0/train/0.parquet
https://huggingface.co/api/datasets/abisee/cnn_dailymail/parquet/3.0.0/train/1.parquet
https://huggingface.co/api/datasets/abisee/cnn_dailymail/parquet/3.0.0/train/2.parquet
```

```python
import pandas as pd

url = "https://huggingface.co/api/datasets/abisee/cnn_dailymail/parquet/3.0.0/test/0.parquet"
df = pd.read_parquet(url)

input_text  = df["article"][0]
output_text = df["highlights"][0]
```

---

## Eval Notes

- **Metric:** ROUGE-1/2/L scores are the standard benchmark. Human preference scoring works well here too.
- **Easy to eyeball:** a bad summary is immediately obvious — wrong facts, missing the main point, too verbose.
- **Recommended split for demos:** use `test` split (11,490 examples), which has no overlap with typical LLM training data.
- **Suggested sample size:** 50–100 examples is enough to see meaningful signal.
