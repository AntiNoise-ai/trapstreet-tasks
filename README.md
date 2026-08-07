# TrapStreet Tasks

Evaluation tasks for [trapstreet.run](https://trapstreet.run). Each task defines an
**input** (what the solution sees), an **expected** answer (which it never sees), and a
**judge** that scores one against the other. Any solution — an agent, a skill, a raw model
call — can be run against a task without hooks or instrumentation.

This repo holds **37 tasks**. **14 are registered on trapstreet.run** and accept
submissions. The other 23 run locally but will not submit yet — see
[Not yet on the platform](#not-yet-on-the-platform).

---

## The one rule for submitting

**A task's identity on the platform is `(repo_url, commit_sha, repo_path)`.** When you
`tp submit`, the server matches the provenance recorded by `tp run` against published task
versions. No match → `404`.

That means **cloning this repo at `main` and submitting will not work.** `main` moves; the
published task versions are pinned to specific commits. Your `trap.yaml` must point at the
**exact commit** the task was registered with:

```yaml
tasks:
  pdf-tables:
    source: git+https://github.com/trapstreet/trapstreet-tasks@f17b9b41456031b187bd57d8234047bd92e65b84#subdirectory=tasks/pdf_tables
```

The [Live tasks](#live-tasks) block below is copy-pasteable — take the entries you want.

Running against a local checkout is fine for iterating; just expect `tp submit` to fail
unless the checkout is at the pinned commit. `tp submit --allow-unanchored` uploads a run
with no git provenance — it is stored and viewable, but never ranked.

---

## Live tasks

Registered, public, submittable. Case counts are from the pinned commit.

| Alias | What it tests | Cases | Path |
|---|---|---|---|
| `core-calibrated-answer` | Does the model know what it doesn't know? | 30 | [`tasks/core_calibrated_answer`](./tasks/core_calibrated_answer) |
| `core-date-arithmetic` | Date + time math | 21 | [`tasks/core_date_arithmetic`](./tasks/core_date_arithmetic) |
| `core-json-schema-output` | Following a function-call schema | 20 | [`tasks/core_json_schema_output`](./tasks/core_json_schema_output) |
| `core-needle-in-haystack` | Finding one fact in a long document | 15 | [`tasks/core_needle_in_haystack`](./tasks/core_needle_in_haystack) |
| `core-pdf-ocr` | Reading a scanned PDF | 20 | [`tasks/core_pdf_ocr`](./tasks/core_pdf_ocr) |
| `debug-subscription-billing-pipeline` | Multi-report consistency debugging | 6 | [`tasks/debug_subscription_billing_pipeline`](./tasks/debug_subscription_billing_pipeline) |
| `debug-vendor-payout-pipeline` | Debugging a vendor payout pipeline — few cases, hard | 4 | [`tasks/debug_vendor_payout_pipeline`](./tasks/debug_vendor_payout_pipeline) |
| `influencer-marketing-disclosure` | Spotting undisclosed paid promotion | 11 | [`tasks/influencer_marketing_disclosure`](./tasks/influencer_marketing_disclosure) |
| `pdf-mixed-scan` | PDF parsing when half the document has no text layer | 20 | [`tasks/pdf_mixed_scan`](./tasks/pdf_mixed_scan) |
| `mbti-profile` | 32-question Likert questionnaire, self-reported | 1 | [`tasks/personality/mbti_profile`](./tasks/personality/mbti_profile) |
| `pdf-reader` | Legal contract review — superseded by `pdf-reader-v2` | 19 | [`tasks/pdf_reader`](./tasks/pdf_reader) |
| `pdf-reader-v2` | UK tenancy agreement — rent, dates, clauses | 20 | [`tasks/pdf_reader_v2`](./tasks/pdf_reader_v2) |
| `pdf-tables` | Reading values out of wide, repetitive tables | 20 | [`tasks/pdf_tables`](./tasks/pdf_tables) |
| `python-bugfix-diff` | Which code-review skill actually finds the bug? | 10 | [`tasks/code_review_skill/python_bugfix_diff`](./tasks/code_review_skill/python_bugfix_diff) |

<details>
<summary><b>Paste this into your <code>trap.yaml</code></b> — pinned sources for all 14</summary>

```yaml
tasks:
  core-calibrated-answer:
    source: git+https://github.com/trapstreet/trapstreet-tasks@00d0632172c69e6f31c9ce26799ea34865e67930#subdirectory=tasks/core_calibrated_answer
  core-date-arithmetic:
    source: git+https://github.com/trapstreet/trapstreet-tasks@00d0632172c69e6f31c9ce26799ea34865e67930#subdirectory=tasks/core_date_arithmetic
  core-json-schema-output:
    source: git+https://github.com/trapstreet/trapstreet-tasks@00d0632172c69e6f31c9ce26799ea34865e67930#subdirectory=tasks/core_json_schema_output
  core-needle-in-haystack:
    source: git+https://github.com/trapstreet/trapstreet-tasks@00d0632172c69e6f31c9ce26799ea34865e67930#subdirectory=tasks/core_needle_in_haystack
  core-pdf-ocr:
    source: git+https://github.com/trapstreet/trapstreet-tasks@8bee00aaf0dfad72979aca8b39c87183b01cd5c7#subdirectory=tasks/core_pdf_ocr
  debug-subscription-billing-pipeline:
    source: git+https://github.com/trapstreet/trapstreet-tasks@4d7400a7e5c9ace5b4db3f9d6c89b73777419dbc#subdirectory=tasks/debug_subscription_billing_pipeline
  debug-vendor-payout-pipeline:
    source: git+https://github.com/trapstreet/trapstreet-tasks@e4084a9c3b892ccd855ca15b6ed4e4cc5473a7cf#subdirectory=tasks/debug_vendor_payout_pipeline
  influencer-marketing-disclosure:
    source: git+https://github.com/trapstreet/trapstreet-tasks@e4084a9c3b892ccd855ca15b6ed4e4cc5473a7cf#subdirectory=tasks/influencer_marketing_disclosure
  pdf-mixed-scan:
    source: git+https://github.com/trapstreet/trapstreet-tasks@6afe24b4173db4ffb4c83da81c7cc93ce8a50943#subdirectory=tasks/pdf_mixed_scan
  mbti-profile:
    source: git+https://github.com/trapstreet/trapstreet-tasks@dd39d74f2401a4b690229ab1031d00618abc9e38#subdirectory=tasks/personality/mbti_profile
  pdf-reader:
    source: git+https://github.com/trapstreet/trapstreet-tasks@dd39d74f2401a4b690229ab1031d00618abc9e38#subdirectory=tasks/pdf_reader
  pdf-reader-v2:
    source: git+https://github.com/trapstreet/trapstreet-tasks@ae4bf6f84276a8a461f9dd44a70086f680ba9729#subdirectory=tasks/pdf_reader_v2
  pdf-tables:
    source: git+https://github.com/trapstreet/trapstreet-tasks@f17b9b41456031b187bd57d8234047bd92e65b84#subdirectory=tasks/pdf_tables
  python-bugfix-diff:
    source: git+https://github.com/trapstreet/trapstreet-tasks@93d6ef239e640d3faaf92fafa4c6b0c251ad00cb#subdirectory=tasks/code_review_skill/python_bugfix_diff
```

</details>

### Where `main` differs from what runs

For these three the directory at `main` has changed since the registered commit, so what you
read here is **not** what a submitted run executes — read the pinned commit for the exact
contract:

`pdf-reader` · `mbti-profile` · `python-bugfix-diff`

---

## Community tasks in other repos

Registered on trapstreet.run, but the task lives elsewhere. Listed here for discovery only.

| Alias | Repo |
|---|---|
| `karpathys-jagged-questions` | [xiaotianhan91/karpathys-jagged-questions](https://github.com/xiaotianhan91/karpathys-jagged-questions) |
| `minecraft-obtain-diamond` | [Ruqii/minecraft-obtain-diamond](https://github.com/Ruqii/minecraft-obtain-diamond) |
| `mineral-species-id` | [Zhuaiz/elastic-mineral-hackson](https://github.com/Zhuaiz/elastic-mineral-hackson) (`trap/task`) |

---

## Not yet on the platform

Complete tasks — `traptask.yaml`, `judge.py`, generated `inputs/` and `expected/` — that
have **not been registered** as task versions. `tp run` works against a local checkout.
`tp submit` returns `404`, because there is no published version to match. Registering one
is a `POST /api/tasks` away; nothing in the task itself needs to change.

| Path | What it tests | Cases |
|---|---|---|
| [`tasks/ai_text_detector`](./tasks/ai_text_detector) | Human-written vs AI-generated text | 20 |
| [`tasks/bloodstain_reader`](./tasks/bloodstain_reader) | Forensic vision — evidence vs suspect statement | 20 |
| [`tasks/codebase_graph_qa`](./tasks/codebase_graph_qa) | Cross-file Q&A over a small multi-language repo | 15 |
| [`tasks/connections/word_groups`](./tasks/connections/word_groups) | Partition 16 words into 4 groups of 4 | 10 |
| [`tasks/core_code_syntax_generation`](./tasks/core_code_syntax_generation) | Basic code generation from signature + docstring | 20 |
| [`tasks/core_follow_instructions`](./tasks/core_follow_instructions) | Obeying explicit prompt constraints | 25 |
| [`tasks/core_multi_turn_memory`](./tasks/core_multi_turn_memory) | Recall across a multi-session conversation | 20 |
| [`tasks/core_parallel_tool_calls`](./tasks/core_parallel_tool_calls) | Planning several tool calls at once | 20 |
| [`tasks/core_tool_selection_at_scale`](./tasks/core_tool_selection_at_scale) | Tool choice as the catalog grows to 300 | 64 |
| [`tasks/cuad`](./tasks/cuad) | Legal contract clause extraction — exact span, or correctly "absent" | 32 |
| [`tasks/doc_editing`](./tasks/doc_editing) | Content retention when editing a document | 4 |
| [`tasks/imported/gsm8k`](./tasks/imported/gsm8k) | Grade-school math word problems | 25 |
| [`tasks/imported/mmlu`](./tasks/imported/mmlu) | Multiple-choice knowledge across subjects | 25 |
| [`tasks/invoice_reconciliation`](./tasks/invoice_reconciliation) | Locating the source of a reconciliation discrepancy | 14 |
| [`tasks/plant_disease_id`](./tasks/plant_disease_id) | Plant pathology from PlantVillage leaf photos | 20 |
| [`tasks/product_matching/sku_disambiguation`](./tasks/product_matching/sku_disambiguation) | Are two product names the same SKU? | 12 |
| [`tasks/receipt_extraction`](./tasks/receipt_extraction) | Receipt parsing from real-world photos | 20 |
| [`tasks/scheduler/cross_timezone`](./tasks/scheduler/cross_timezone) | Scheduling across timezones | 11 |
| [`tasks/spreadsheet_reader`](./tasks/spreadsheet_reader) | One aggregation question over a real `.xlsx` | 6 |
| [`tasks/web_scraping/game_store_navigation`](./tasks/web_scraping/game_store_navigation) | Navigating a mock game storefront | 10 |
| [`tasks/wildlife_camera_trap`](./tasks/wildlife_camera_trap) | Species ID from Serengeti camera-trap photos | 20 |
| [`tasks/agents-in-situationship`](./tasks/agents-in-situationship) | 20 multiple-choice dating scenarios, self-reported | 1 |

### Special cases

**[`tasks/core_tool_selection_under_load`](./tasks/core_tool_selection_under_load) — frozen, do not edit.**
Superseded by `core_tool_selection_at_scale`. Kept byte-identical on purpose: it returned
`1.0` on all 270 case-scores it ever produced, and those scores stay interpretable only if
the task doesn't move. That null result is also cited in a write-up, so the directory is
what makes the account checkable. Not a candidate for deletion.

**[`tasks/pdf_reader`](./tasks/pdf_reader) — superseded but still live.**
`pdf-reader-v2` replaces it. Removing the directory would **not** take it off the
leaderboard — task versions are pinned to a commit that stays in git history. Retiring it
is a platform-side change (task visibility), not a repo change.

---

## Archive

[`archive/`](./archive) is kept for reference and not maintained.

Six early explorations, documentation only — no runnable cases: article summarization
(CNN/DailyMail), everyday Q&A (TriviaQA), finance Q&A (FinanceBench), legal clause
extraction (CUAD), agent tool use (BFCL v4), PDF pricing extraction.

Plus [`archive/financebench`](./archive/financebench) — a complete 5-case task, archived
because FinanceBench is **CC BY-NC 4.0** (NonCommercial), which
[`tasks/imported/README.md`](./tasks/imported/README.md) excludes by policy. Never
registered on trapstreet.run. To use this material, author original questions over the same
public SEC 10-K filings instead.

---

## Writing a task

Every task follows the same layout and I/O contract:

```
tasks/<name>/
├── gold.cases.json    single source of truth, hand-edited
├── build_cases.py     validates gold.cases.json, generates inputs/ + expected/
├── judge.py           scores ONE case — must return {"score": 0.0-1.0}
├── grader.py          aggregates all cases into a run verdict
├── traptask.yaml      case list + tags + judge/grader commands
├── inputs/<case_id>/  generated — what the solution sees
├── expected/<case_id>/ generated — judge-only
└── README.md          I/O contract, scoring, sources and licensing
```

Not every task here uses `gold.cases.json` + `build_cases.py`; several of the `core_*` tasks
generate cases inline and are live on the platform regardless. The parts that are load-bearing
are `traptask.yaml`, `judge.py`, and the generated `inputs/` / `expected/` pair.

**One security rule:** case IDs must never leak the answer. A solution can read its own
`inputs_dir` path, so `leopard_01` gives the game away — use `case_01`, and keep the real
label in `expected/<id>/answer.json`.

Full reference: [`trap` docs](https://github.com/trapstreet/trap/tree/main/docs) ·
[writing a task](https://github.com/trapstreet/trap/blob/main/docs/guides/writing-task.md)
