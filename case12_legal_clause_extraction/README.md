# Case 12: Legal — Contract Clause Extraction

**Concept:** "There are 20+ legal AI tools claiming to review contracts. But can they actually find the termination clause? That's step 1."

A real commercial contract goes in, along with a question targeting one of 41 specific clause types (Anti-Assignment, Change of Control, Cap on Liability, etc.). The model must return the exact clause span — or correctly say none exists. Models have a known "laziness" problem on this task: they confidently say "no clause found" even when one is plainly there.

---

## Dataset

| Field | Value |
|-------|-------|
| Name | CUAD (Contract Understanding Atticus Dataset) |
| Curator | The Atticus Project |
| HuggingFace (eval-ready, SQuAD format) | https://huggingface.co/datasets/theatticusproject/cuad-qa |
| HuggingFace (raw PDFs + master CSV) | https://huggingface.co/datasets/theatticusproject/cuad |
| GitHub | https://github.com/TheAtticusProject/cuad |
| Paper | https://arxiv.org/abs/2103.06268 (NeurIPS 2021) |
| License | CC BY 4.0 ✅ |
| Size | 510 commercial contracts from SEC EDGAR, 41 clause categories, 13,000+ expert-labeled spans |

---

## Input / Output Schema

Use **`cuad-qa`** for the eval — it's pre-formatted as (question, context, answer) triples with character-level spans, matching SQuAD 2.0.

### Input

**1. `context`** — full contract text (often 30–80 pages of legal prose).

**2. `question`** — a templated prompt asking about one of the 41 clause categories.

```json
{
  "question": "Highlight the parts (if any) of this contract related to \"Anti-Assignment\" that should be reviewed by a lawyer. Details: Is consent or notice required of a party if the contract is assigned to a third party?"
}
```

### Output

**Field:** `answers.text[]` — list of expert-labeled clause spans. **Empty list means "no such clause in this contract"** — getting this case right is the laziness test.

**Field:** `answers.answer_start[]` — character offsets into `context`, parallel to `text[]`.

```json
{
  "answers": {
    "text": ["Neither party may assign this Agreement without the prior written consent of the other party..."],
    "answer_start": [14823]
  }
}
```

---

## Data Access

```python
from datasets import load_dataset

ds = load_dataset("theatticusproject/cuad-qa", split="test")
row = ds[0]

input_question = row["question"]
input_context  = row["context"]      # → send question + context to model
output_spans   = row["answers"]["text"]  # → grade against (empty list = "no clause")
```

| Split | Size |
|-------|------|
| `train` | 22,450 |
| `test` | 4,182 |

> **Use `test`** — `train` was used to fine-tune the models being evaluated.

---

## Dataset Stats

| Metric | Value |
|--------|-------|
| Contracts | 510 |
| Clause categories | 41 (Document Name, Parties, Agreement Date, Effective Date, Expiration Date, Renewal Term, Notice to Terminate Renewal, Governing Law, Most Favored Nation, Non-Compete, Exclusivity, No-Solicit Of Customers, No-Solicit Of Employees, Non-Disparagement, Termination For Convenience, Rofr/Rofo/Rofn, Change Of Control, Anti-Assignment, Revenue/Profit Sharing, Price Restrictions, Minimum Commitment, Volume Restriction, Ip Ownership Assignment, Joint Ip Ownership, License Grant, Non-Transferable License, Affiliate License-Licensor, Affiliate License-Licensee, Unlimited/All-You-Can-Eat License, Irrevocable Or Perpetual License, Source Code Escrow, Post-Termination Services, Audit Rights, Uncapped Liability, Cap On Liability, Liquidated Damages, Warranty Duration, Insurance, Covenant Not To Sue, Third Party Beneficiary) |
| Labeled spans | 13,000+ |
| Source | SEC EDGAR (publicly filed material contracts) |

---

## Eval Notes

- **Metric:** for non-empty gold spans, use token-level F1 or character-level IoU between predicted span and any gold span (a contract may have multiple correct spans for one clause). For empty gold spans, exact match on "no clause found"-equivalent answers.
- **The laziness test:** track precision separately on rows where the gold span is *non-empty*. Models that say "no clause found" when one exists are the silent failure mode this case is designed to catch.
- **Why span-level matters:** the value of a legal AI tool isn't just "yes there is an Anti-Assignment clause" — lawyers need to see the exact text to review. Grading on span overlap, not boolean presence, is what makes this an honest test.
- **Most demo-worthy clauses** (subtle, frequently misread): Anti-Assignment, Change Of Control, Most Favored Nation, Cap On Liability, Effective Date vs Agreement Date.
- **Document length:** contracts often exceed 50 pages — this is also a long-context test in disguise. Models without long-context support will need chunking + retrieval, which is part of what's being evaluated.
