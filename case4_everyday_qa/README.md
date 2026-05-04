# Case 4: Everyday Q&A

**Concept:** "Using AI as a smarter Google."

A plain-language question goes in. A short, verified factual answer comes out. Questions reflect genuine everyday curiosity — the kind of things people actually search for.

---

## Dataset

| Field | Value |
|-------|-------|
| Name | TriviaQA |
| HuggingFace ID | `mandarjoshi/trivia_qa` |
| Config | `rc` (reading comprehension) or `unfiltered` (open-domain) |
| Size | ~650k Q&A pairs across splits |
| License | Apache 2.0 |
| HuggingFace URL | https://huggingface.co/datasets/mandarjoshi/trivia_qa |
| Original paper | https://nlp.cs.washington.edu/triviaqa/ |

---

## Input / Output Schema

### Input

**Field:** `question`

A natural language trivia question reflecting real everyday curiosity. Written by trivia enthusiasts — not artificially constructed.

```json
{
  "question": "The Eiffel Tower is located in which European city?"
}
```

### Output

**Field:** `answer.value` (canonical answer) + `answer.aliases` (all accepted variants)

`value` is the normalized primary answer. `aliases` is the full list of acceptable phrasings — use this for flexible matching (e.g. "Paris" and "City of Paris" are both correct).

```json
{
  "answer": {
    "value": "Paris",
    "aliases": ["Paris", "City of Paris", "Lutecia", "Lutetia Parisiorum"]
  }
}
```

### Full example record

```json
{
  "question_id": "tc_2",
  "question": "The Eiffel Tower is located in which European city?",
  "answer": {
    "value": "Paris",
    "aliases": ["Paris", "City of Paris", "Lutecia", "Lutetia Parisiorum"],
    "normalized_value": "paris",
    "normalized_aliases": ["paris", "city of paris", "lutecia", "lutetia parisiorum"]
  }
}
```

---

## How to Access the Data

### Python (HuggingFace `datasets` library)

```python
from datasets import load_dataset

# 'rc' config: questions paired with supporting Wikipedia/web documents
# 'unfiltered' config: open-domain, question only (simpler for LLM eval)
ds = load_dataset("mandarjoshi/trivia_qa", "unfiltered")

# Splits: train, validation, test
example = ds["validation"][0]

input_text   = example["question"]
output_value = example["answer"]["value"]       # primary answer
output_aliases = example["answer"]["aliases"]   # all valid answers
```

### Direct file download (Parquet)

```
https://huggingface.co/datasets/mandarjoshi/trivia_qa/resolve/main/data/unfiltered/
```

Or browse the file tree at:
https://huggingface.co/datasets/mandarjoshi/trivia_qa/tree/main/data

### Original download (JSON)

The original dataset authors also provide direct JSON downloads:
https://nlp.cs.washington.edu/triviaqa/

---

## Eval Notes

- **Metric:** Exact match (EM) against `answer.normalized_aliases` is the standard. This handles capitalization and minor phrasing differences.
- **Config choice:** Use `unfiltered` for pure Q&A evals (no supporting document context needed). Use `rc` if you want to also test retrieval or document comprehension.
- **Easy to eyeball:** wrong answers are immediately obvious — no domain knowledge needed to spot "Tokyo" vs "Paris."
- **Recommended split for demos:** use `validation` split (~7,993 examples), which is a clean held-out set.
- **Suggested sample size:** 50–100 examples is enough to show clear signal between strong and weak models.
