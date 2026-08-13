# TrapStreet Tasks

Reference tasks for [trapstreet.run](https://trapstreet.run) — worked examples, not a
catalogue. Anyone can publish a task from their own public repository; these exist to show
what one looks like when it's done properly.

A task declares its **inputs**, the **expected** answers it never shows the solution, and a
**judge** that scores one against the other. The solution runs as a subprocess, so anything
that reads files and writes an answer can be measured — no SDK, no instrumentation.

---

## Validated

Registered on trapstreet.run and run by at least one solution, so we know they produce a
spread rather than scoring everything the same.

| Task | What it measures | Cases | Runs |
|---|---|---|---|
| [`personality/mbti_profile`](./tasks/personality/mbti_profile)<br/>[mbti-profile](https://trapstreet.run/tasks/mbti-profile) | A 32-question Likert questionnaire, self-reported | 1 | **10** |
| [`code_review_skill/python_bugfix_diff`](./tasks/code_review_skill/python_bugfix_diff)<br/>[python-bugfix-diff](https://trapstreet.run/tasks/python-bugfix-diff) | One real file frozen before a real bug was fixed — find it | 10 | **9** |
| [`pdf_mixed_scan`](./tasks/pdf_mixed_scan)<br/>[pdf-mixed-scan](https://trapstreet.run/tasks/pdf-mixed-scan) | A PDF where half the pages have no text layer | 20 | **6** |
| [`influencer_marketing_disclosure`](./tasks/influencer_marketing_disclosure)<br/>[influencer-marketing-disclosure](https://trapstreet.run/tasks/influencer-marketing-disclosure) | Spotting undisclosed paid promotion | 11 | **6** |
| [`pdf_reader_v2`](./tasks/pdf_reader_v2)<br/>[pdf-reader-v2](https://trapstreet.run/tasks/pdf-reader-v2) | A UK tenancy agreement — rent, dates, clauses | 20 | **3** |
| [`debug_vendor_payout_pipeline`](./tasks/debug_vendor_payout_pipeline)<br/>[debug-vendor-payout-pipeline](https://trapstreet.run/tasks/debug-vendor-payout-pipeline) | Reports from a vendor-payout pipeline disagree; produce correct ones | 4 | **3** |
| [`core_capability_stacking_regression`](./tasks/core_capability_stacking_regression)<br/>[core-capability-stacking-regression](https://trapstreet.run/tasks/core-capability-stacking-regression) | Does stacking capabilities degrade any one of them? | 108 | **1** |

<details>
<summary><b>Point your <code>trap.yaml</code> at one</b></summary>

A task's identity on the platform is `(repo_url, commit_sha, repo_path)`. Cloning `main` and
submitting matches no published version, so pin the registered commit:

```yaml
tasks:
python-bugfix-diff:
    source: git+https://github.com/trapstreet/trapstreet-tasks@93d6ef239e640d3faaf92fafa4c6b0c251ad00cb#subdirectory=tasks/code_review_skill/python_bugfix_diff
  core-calibrated-answer:
    source: git+https://github.com/trapstreet/trapstreet-tasks@00d0632172c69e6f31c9ce26799ea34865e67930#subdirectory=tasks/core_calibrated_answer
  core-capability-stacking-regression:
    source: git+https://github.com/trapstreet/trapstreet-tasks@8abf610e57d298f2fafa232c522a3b2afd0ce620#subdirectory=tasks/core_capability_stacking_regression
  core-date-arithmetic:
    source: git+https://github.com/trapstreet/trapstreet-tasks@00d0632172c69e6f31c9ce26799ea34865e67930#subdirectory=tasks/core_date_arithmetic
  core-json-schema-output:
    source: git+https://github.com/trapstreet/trapstreet-tasks@00d0632172c69e6f31c9ce26799ea34865e67930#subdirectory=tasks/core_json_schema_output
  core-needle-in-haystack:
    source: git+https://github.com/trapstreet/trapstreet-tasks@00d0632172c69e6f31c9ce26799ea34865e67930#subdirectory=tasks/core_needle_in_haystack
  core-pdf-ocr:
    source: git+https://github.com/trapstreet/trapstreet-tasks@8bee00aaf0dfad72979aca8b39c87183b01cd5c7#subdirectory=tasks/core_pdf_ocr
  debug-vendor-payout-pipeline:
    source: git+https://github.com/trapstreet/trapstreet-tasks@e4084a9c3b892ccd855ca15b6ed4e4cc5473a7cf#subdirectory=tasks/debug_vendor_payout_pipeline
  influencer-marketing-disclosure:
    source: git+https://github.com/trapstreet/trapstreet-tasks@e4084a9c3b892ccd855ca15b6ed4e4cc5473a7cf#subdirectory=tasks/influencer_marketing_disclosure
  pdf-mixed-scan:
    source: git+https://github.com/trapstreet/trapstreet-tasks@6afe24b4173db4ffb4c83da81c7cc93ce8a50943#subdirectory=tasks/pdf_mixed_scan
  pdf-reader:
    source: git+https://github.com/trapstreet/trapstreet-tasks@dd39d74f2401a4b690229ab1031d00618abc9e38#subdirectory=tasks/pdf_reader
  pdf-reader-v2:
    source: git+https://github.com/trapstreet/trapstreet-tasks@ae4bf6f84276a8a461f9dd44a70086f680ba9729#subdirectory=tasks/pdf_reader_v2
  mbti-profile:
    source: git+https://github.com/trapstreet/trapstreet-tasks@dd39d74f2401a4b690229ab1031d00618abc9e38#subdirectory=tasks/personality/mbti_profile
  do-llms-dream-of-intj:
    source: git+https://github.com/trapstreet/trapstreet-tasks@cf92b6690b7c8b3430602dd3b72a8528c96e636b#subdirectory=tasks/personality/mbti_profile
```

Then `tp run && tp submit`. Running against a local checkout is fine for iterating; only
submission needs the pin.

</details>

---

## Unvalidated

Complete and runnable — `traptask.yaml`, a judge, generated cases — but **nobody has submitted
a run yet**, so nobody knows whether they separate a good solution from a bad one. That is the
bar for moving into `tasks/`.

Being first on one of these is the cheapest way to find out. Point a `trap.yaml` at the
directory, `tp run`, and see whether the scores spread.

> Six of these are still registered on trapstreet.run from before they moved here
> (`core-calibrated-answer`, `core-date-arithmetic`, `core-json-schema-output`,
> `core-needle-in-haystack`, `core-pdf-ocr`, `pdf-reader`). They still run — a task version is
> pinned to a commit, not to a path — but their listed source path no longer resolves against
> `main`.

| Task | Cases |
|---|---|
| [`ai_text_detector`](./unvalidated/ai_text_detector) | 20 |
| [`bloodstain_reader`](./unvalidated/bloodstain_reader) | 20 |
| [`codebase_graph_qa`](./unvalidated/codebase_graph_qa) | 15 |
| [`connections/word_groups`](./unvalidated/connections/word_groups) | 10 |
| [`core_calibrated_answer`](./unvalidated/core_calibrated_answer) | 30 |
| [`core_code_syntax_generation`](./unvalidated/core_code_syntax_generation) | 20 |
| [`core_date_arithmetic`](./unvalidated/core_date_arithmetic) | 21 |
| [`core_follow_instructions`](./unvalidated/core_follow_instructions) | 25 |
| [`core_json_schema_output`](./unvalidated/core_json_schema_output) | 20 |
| [`core_multi_turn_memory`](./unvalidated/core_multi_turn_memory) | 20 |
| [`core_needle_in_haystack`](./unvalidated/core_needle_in_haystack) | 15 |
| [`core_parallel_tool_calls`](./unvalidated/core_parallel_tool_calls) | 20 |
| [`core_pdf_ocr`](./unvalidated/core_pdf_ocr) | 20 |
| [`core_tool_selection_at_scale`](./unvalidated/core_tool_selection_at_scale) | 64 |
| [`core_tool_selection_under_load`](./unvalidated/core_tool_selection_under_load) | 27 |
| [`doc_editing`](./unvalidated/doc_editing) | 4 |
| [`invoice_reconciliation`](./unvalidated/invoice_reconciliation) | 14 |
| [`product_matching/sku_disambiguation`](./unvalidated/product_matching/sku_disambiguation) | 12 |
| [`receipt_extraction`](./unvalidated/receipt_extraction) | 20 |
| [`scheduler/cross_timezone`](./unvalidated/scheduler/cross_timezone) | 11 |
| [`spreadsheet_reader`](./unvalidated/spreadsheet_reader) | 6 |
| [`web_scraping/game_store_navigation`](./unvalidated/web_scraping/game_store_navigation) | 10 |
| [`wildlife_camera_trap`](./unvalidated/wildlife_camera_trap) | 20 |

---

## Build your own

You do not need this repo. Publish from any public repository you own and register it at
[trapstreet.run](https://trapstreet.run) → **+ New Task**; the platform pins it to your
`repo@commit`.

```bash
npx skills add trapstreet/trapstreet-skills
```

Then tell your coding agent: *"make a task that evaluates &lt;the thing you want measured&gt;"*.
[`trapstreet-task-scaffold`](https://github.com/trapstreet/trapstreet-skills) interviews you on
what counts as correct, where ground truth comes from, and how to keep the scoring ungameable,
then writes `traptask.yaml`, `judge.py` and `grader.py`.

[`mineral-species-id`](https://trapstreet.run/tasks/mineral-species-id) and
[`karpathys-jagged-questions`](https://trapstreet.run/tasks/karpathys-jagged-questions) were
built exactly that way, by people who are not us.

## Results

[**RESULTS.md**](./RESULTS.md) — what the boards have measured, generated from the API.

## Licensing

MIT for the harness and hand-authored content; see [NOTICE](./NOTICE). Tasks that vendor
third-party data carry their own `ATTRIBUTION.md` or `LICENSE.md`, and that license governs the
vendored content. Importing a public benchmark? See [IMPORTING.md](./IMPORTING.md).
