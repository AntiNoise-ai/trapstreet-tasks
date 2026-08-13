# Doc Editing (content-retention)

A trap-compatible task built on the DELEGATE-52 finding — *"LLMs Corrupt Your
Documents When You Delegate"* (Microsoft, 2026): frontier models silently drop,
alter, or de-duplicate records when asked to restructure a document. Here that
corruption is made **deterministic and measurable**.

Each case ships a structured document and asks for a structure-changing edit
(reformat / sort / uniform edit) that **must preserve every record and value**.
The judge re-parses the output and reports an exact match **plus a content
retention %** — the headline "you silently lost X% of the document" metric.

The eval is **pure-rule-based** (no LLM-judge): records are compared as
normalized sets/lists/dicts, with numeric fields matched to 2 decimals.

> **Lane: model-eval (no tools).** A code-writing agent reformats CSV→JSON with
> perfect retention, so this task probes a model's *own* generation — the
> trapstreet model-eval lane, which matches the original DELEGATE-52 setup
> (the model emits the edited document directly).
>
> **Scope / honesty:** this is the *single-shot* content-preservation version.
> DELEGATE's headline corruption builds up over *many delegated edits*; a true
> replication needs a multi-turn harness (future work). To make single-shot
> meaningful, docs here are deliberately long (23–52 records) and seeded with
> drop/dedup/coercion bait — strength scales with length. Treat `retention_pct`
> as the signal to watch as you grow the record counts.

---

## Cases (4)

| id | category | difficulty | records | edit | the bait |
|---|---|---|---|---|---|
| `ledger_csv_to_json` | reformat | medium | 23 | CSV → JSON array | comma-in-field, unicode, em dash, empty field, near-duplicate pair |
| `transactions_sort` | sort | medium | 18 | sort by date, keep all | repeated amounts; a `0.00`; negatives (dedup/drop bait) |
| `apply_surcharge` | edit | hard | 16 | +5% to every price | multi-edit consistency — every row must be edited, none skipped |
| `config_long_retention` | retention | hard | 52 | `key=value` → JSON object | long list (truncation), value containing `=`/`:`, `"false"`, `"007"`, empty value |

---

## Scoring

`score` is strict — **1.0 only on an exact match** (no dropped, extra, or
altered records). On failure the metrics still carry:

- `retention_pct` — fraction of gold records correctly reproduced
- `n_dropped`, `n_extra`, `n_altered` (and `dropped_keys` for the dict case)

so the leaderboard can show *how* a model corrupted the doc, not just that it
did. Match modes per case: `multiset` (order-free), `ordered` (sort case),
`dict` (config case).

---

## Solution contract

1. Read `INPUTS` (JSON dict: `filename → absolute path`).
2. Read `INPUTS["question.txt"]` and the case's document
   (`data.csv` / `data.txt` / `config.txt`).
3. Print **only** the JSON (array or object) to **stdout** (markdown fences tolerated).

---

## Regenerating

```bash
python3 build_docs.py     # rewrites inputs/, expected/, traptask.yaml, gold.cases.json
```

Gold record sets are derived from the same source data the input files are
written from, so they cannot drift.
