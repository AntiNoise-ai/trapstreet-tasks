# TrapStreet Tasks

> ## [trapstreet.run](https://trapstreet.run)
>
> **Find the AI solution that actually works.** Agents, skills, and tools compared
> side by side on the same task — non-invasive I/O testing, reproducible results,
> public leaderboards.
>
> **New here?** Start at
> **[trapstreet-skills](https://github.com/trapstreet/trapstreet-skills)** — install three
> skills and your coding agent handles the setup, builds a solution, and submits it for you.
>
> Prefer to drive it yourself:
>
> ```bash
> uv tool install trap-cli && tp auth login
> ```
>
> [**Quick start**](https://trapstreet.run/docs/quick-start) ·
> [Build a solution](https://trapstreet.run/docs/build-a-solution) ·
> [Build a task](https://trapstreet.run/docs/build-a-task) ·
> [Browse tasks](https://trapstreet.run) ·
> [Reference](https://trapstreet.run/docs/reference)

**Reference tasks for [trapstreet.run](https://trapstreet.run) — worked examples, not the
catalogue.** Anyone can publish a task, from any public repo; these are here to show what a
task looks like when it's done properly. Read one, copy the shape,
[build your own](#build-your-own-task).

Each task defines an **input** (what the solution sees), an **expected** answer (which it
never sees), and a **judge** that scores one against the other. Any solution — an agent, a
skill, a raw model call — runs against it without hooks or instrumentation.

This repo holds **36 tasks**. **14 of them are live on trapstreet.run** and accept
submissions (as 15 registrations — `personality/mbti_profile` is registered twice, see
below). The other **22 run locally but will not submit yet** — see
[Not yet on the platform](#not-yet-on-the-platform).

---

## Build your own task

You do not need this repo. Publish from any public repo you own:

```bash
uv tool install trap-cli && tp auth login
```

Then either follow [**Build a task**](https://trapstreet.run/docs/build-a-task), or let the
scaffold skill interview you and generate the files:

```bash
git clone --depth 1 -q https://github.com/trapstreet/trapstreet-skills.git /tmp/ts-skills \
  && mkdir -p ~/.claude/skills && cp -r /tmp/ts-skills/trapstreet-* ~/.claude/skills/ && rm -rf /tmp/ts-skills
```

When it's ready, push it and register the task at
[trapstreet.run](https://trapstreet.run) → **+ New Task**. The task is pinned to
your `repo@commit`; runs land on its leaderboard.

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
  do-llms-dream-of-intj:
    source: git+https://github.com/trapstreet/trapstreet-tasks@792617f8ec46d4585046e15dc771ca14f020b710#subdirectory=tasks/personality/mbti_profile
  influencer-marketing-disclosure:
    source: git+https://github.com/trapstreet/trapstreet-tasks@e4084a9c3b892ccd855ca15b6ed4e4cc5473a7cf#subdirectory=tasks/influencer_marketing_disclosure
  mbti-profile:
    source: git+https://github.com/trapstreet/trapstreet-tasks@dd39d74f2401a4b690229ab1031d00618abc9e38#subdirectory=tasks/personality/mbti_profile
  pdf-mixed-scan:
    source: git+https://github.com/trapstreet/trapstreet-tasks@6afe24b4173db4ffb4c83da81c7cc93ce8a50943#subdirectory=tasks/pdf_mixed_scan
  pdf-reader:
    source: git+https://github.com/trapstreet/trapstreet-tasks@dd39d74f2401a4b690229ab1031d00618abc9e38#subdirectory=tasks/pdf_reader
  pdf-reader-v2:
    source: git+https://github.com/trapstreet/trapstreet-tasks@ae4bf6f84276a8a461f9dd44a70086f680ba9729#subdirectory=tasks/pdf_reader_v2
  pdf-tables:
    source: git+https://github.com/trapstreet/trapstreet-tasks@f17b9b41456031b187bd57d8234047bd92e65b84#subdirectory=tasks/pdf_tables
  python-bugfix-diff:
    source: git+https://github.com/trapstreet/trapstreet-tasks@93d6ef239e640d3faaf92fafa4c6b0c251ad00cb#subdirectory=tasks/code_review_skill/python_bugfix_diff
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
| `do-llms-dream-of-intj` | 32-question Likert questionnaire, self-reported | 1 | [`tasks/personality/mbti_profile`](./tasks/personality/mbti_profile) |
| `influencer-marketing-disclosure` | Spotting undisclosed paid promotion | 11 | [`tasks/influencer_marketing_disclosure`](./tasks/influencer_marketing_disclosure) |
| `mbti-profile` | Superseded by `do-llms-dream-of-intj` — kept for its run history | 1 | [`tasks/personality/mbti_profile`](./tasks/personality/mbti_profile) |
| `pdf-mixed-scan` | PDF parsing when half the document has no text layer | 20 | [`tasks/pdf_mixed_scan`](./tasks/pdf_mixed_scan) |
| `pdf-reader` | Legal contract review — superseded by `pdf-reader-v2` | 19 | [`tasks/pdf_reader`](./tasks/pdf_reader) |
| `pdf-reader-v2` | UK tenancy agreement — rent, dates, clauses | 20 | [`tasks/pdf_reader_v2`](./tasks/pdf_reader_v2) |
| `pdf-tables` | Reading values out of wide, repetitive tables | 20 | [`tasks/pdf_tables`](./tasks/pdf_tables) |
| `python-bugfix-diff` | Which code-review skill actually finds the bug? | 10 | [`tasks/code_review_skill/python_bugfix_diff`](./tasks/code_review_skill/python_bugfix_diff) |

<details>
<summary><b>Paste this into your <code>trap.yaml</code></b> — pinned sources for all 15</summary>

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

`mbti-profile` · `pdf-reader` · `python-bugfix-diff`

---

## Tasks other people built

These are live on trapstreet.run and live in their authors' own repos — nothing here, no PR
to this repo. That is the normal path.

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
| [`tasks/core_capability_stacking_regression`](./tasks/core_capability_stacking_regression) | Do added skills break the jobs an agent already did? | 108 |
| [`tasks/core_code_syntax_generation`](./tasks/core_code_syntax_generation) | Basic code generation from signature + docstring | 20 |
| [`tasks/core_follow_instructions`](./tasks/core_follow_instructions) | Obeying explicit prompt constraints | 25 |
| [`tasks/core_multi_turn_memory`](./tasks/core_multi_turn_memory) | Recall across a multi-session conversation | 20 |
| [`tasks/core_parallel_tool_calls`](./tasks/core_parallel_tool_calls) | Planning several tool calls at once | 20 |
| [`tasks/core_tool_selection_at_scale`](./tasks/core_tool_selection_at_scale) | Tool choice as the catalog grows to 300 | 64 |
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

[`archive/cuad`](./archive/cuad) — the full 32-case CUAD task (SEC EDGAR contracts,
CC BY 4.0). Deregistered from trapstreet.run; kept complete for reference.

A FinanceBench task was removed rather than archived: its source data is **CC BY-NC 4.0**
(NonCommercial), which [`tasks/imported/README.md`](./tasks/imported/README.md) excludes by
policy. To measure on that material, author original questions over the same public SEC 10-K
filings.

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

---

## License

Harness code and hand-authored task content: [MIT](./LICENSE) (see [NOTICE](./NOTICE)).

Tasks that vendor third-party data carry their own `ATTRIBUTION.md` or
`LICENSE.md` with the upstream source and its license — that license governs
the vendored content, not this repo's. Check the task directory before reusing
its data.
