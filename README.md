<p align="center">
  <a href="https://trapstreet.run"><img src="https://raw.githubusercontent.com/trapstreet/trapstreet-tasks/main/docs/logo.png" width="92" alt="Trapstreet"/></a>
</p>

<h1 align="center">TrapStreet Tasks</h1>

<p align="center">
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"/></a>
  <a href="https://trapstreet.run"><img src="https://img.shields.io/badge/trapstreet.run-live-60a5fa" alt="trapstreet.run"/></a>
  <a href="https://discord.gg/Ymm57FzYmF"><img src="https://img.shields.io/badge/Discord-Join-5865F2?style=flat&logo=discord&logoColor=white" alt="Discord"/></a>
  <a href="./RESULTS.md"><img src="https://img.shields.io/badge/results-measured-a78bfa" alt="Results"/></a>
</p>

<p align="center">
  <b>Open evaluation tasks — the hard half is the judge.</b><br/>
  <a href="https://trapstreet.run">trapstreet.run</a>
</p>

Anyone can write 20 test cases. What decides whether an evaluation is worth anything is whether
its **judge** survives contact with a real solution — and in this repo, every task that got a
first run turned out to have something wrong with that judge.

These are the ones that survived, plus the ones still being fixed. Read one before writing your
own.

A task declares its **inputs**, the **expected** answers it never shows the solution, and a
**judge** that scores one against the other. The solution runs as a subprocess, so anything
that reads files and writes an answer can be measured — no SDK, no instrumentation.

---

## Finished

Registered on [trapstreet.run](https://trapstreet.run) and accepting submissions.

| Task | What it measures | Cases | Board | Runs |
|---|---|---|---|---|
| [`personality/mbti_profile`](./tasks/personality/mbti_profile) | A 32-question Likert questionnaire, self-reported | 1 | [mbti-profile](https://trapstreet.run/tasks/mbti-profile) · [do-llms-dream-of-intj](https://trapstreet.run/tasks/do-llms-dream-of-intj) | 10 |
| [`code_review_skill/python_bugfix_diff`](./tasks/code_review_skill/python_bugfix_diff) | One real file frozen just before a real bug was fixed — find it | 10 | [python-bugfix-diff](https://trapstreet.run/tasks/python-bugfix-diff) | 9 |
| [`pdf_mixed_scan`](./tasks/pdf_mixed_scan) | A PDF where half the pages have no text layer | 20 | [pdf-mixed-scan](https://trapstreet.run/tasks/pdf-mixed-scan) | 6 |
| [`influencer_marketing_disclosure`](./tasks/influencer_marketing_disclosure) | Spotting undisclosed paid promotion | 11 | [influencer-marketing-disclosure](https://trapstreet.run/tasks/influencer-marketing-disclosure) | 6 |
| [`pdf_reader_v2`](./tasks/pdf_reader_v2) | A UK tenancy agreement — rent, dates, clauses | 20 | [pdf-reader-v2](https://trapstreet.run/tasks/pdf-reader-v2) | 3 |
| [`debug_vendor_payout_pipeline`](./tasks/debug_vendor_payout_pipeline) | Vendor-payout reports disagree; produce correct ones | 4 | [debug-vendor-payout-pipeline](https://trapstreet.run/tasks/debug-vendor-payout-pipeline) | 3 |
| [`core_capability_stacking_regression`](./tasks/core_capability_stacking_regression) | Does stacking capabilities degrade any one of them? | 108 | [core-capability-stacking-regression](https://trapstreet.run/tasks/core-capability-stacking-regression) | 1 |
| [`session_memory_recall`](./tasks/session_memory_recall) | Does any value survive between two sessions? | 8 | [session-memory-recall](https://trapstreet.run/tasks/session-memory-recall) | — |
| [`core_pdf_ocr`](./tasks/core_pdf_ocr) | Reading a rendered PDF page | 20 | [core-pdf-ocr](https://trapstreet.run/tasks/core-pdf-ocr) | — |
| [`core_needle_in_haystack`](./tasks/core_needle_in_haystack) | Finding one fact in a long document | 15 | [core-needle-in-haystack](https://trapstreet.run/tasks/core-needle-in-haystack) | — |
| [`core_json_schema_output`](./tasks/core_json_schema_output) | Schema-conforming function calls (BFCL v4) | 20 | [core-json-schema-output](https://trapstreet.run/tasks/core-json-schema-output) | — |
| [`core_date_arithmetic`](./tasks/core_date_arithmetic) | Date and time arithmetic | 21 | [core-date-arithmetic](https://trapstreet.run/tasks/core-date-arithmetic) | — |
| [`core_calibrated_answer`](./tasks/core_calibrated_answer) | Does it decline what it cannot answer, or invent? (SimpleQA) | 30 | [core-calibrated-answer](https://trapstreet.run/tasks/core-calibrated-answer) | — |

<details>
<summary><b>Point your <code>trap.yaml</code> at one</b></summary>

A task's identity is `(repo_url, commit_sha, repo_path)`, matched exactly. Cloning `main` and
submitting matches no published version — pin the registered commit:

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
  pdf-reader-v2:
    source: git+https://github.com/trapstreet/trapstreet-tasks@ae4bf6f84276a8a461f9dd44a70086f680ba9729#subdirectory=tasks/pdf_reader_v2
  session-memory-recall:
    source: git+https://github.com/trapstreet/trapstreet-tasks@e7d5a56f92b97b25f5539e3cd9bdcbdeee476183#subdirectory=tasks/session_memory_recall
    clone_to: task   # this one ships a runner your `cmd` has to reach -- see its README
  mbti-profile:
    source: git+https://github.com/trapstreet/trapstreet-tasks@dd39d74f2401a4b690229ab1031d00618abc9e38#subdirectory=tasks/personality/mbti_profile
  do-llms-dream-of-intj:
    source: git+https://github.com/trapstreet/trapstreet-tasks@cf92b6690b7c8b3430602dd3b72a8528c96e636b#subdirectory=tasks/personality/mbti_profile
```

Then `tp run && tp submit`. Iterating against a local checkout is fine; only submission needs
the pin.

</details>

---

## Still being built

[`unvalidated/`](./unvalidated) is work in progress, and the name is literal: **nothing here
has been run yet, which means it isn't finished.**

That sounds like a technicality. It isn't. Every task in this repo that got its first real run
had something badly wrong with the judge — a matcher that accepted a wrong answer, a gold value
that was itself incorrect, a scoring rule that gave every solution the same number. Writing the
cases is the easy half. A judge only becomes trustworthy after a real solution has attacked it.

So these are drafts. They will move up once a run has been through them and the judge has
survived it.

| Task | Cases |
|---|---|
| [`ai_text_detector`](./unvalidated/ai_text_detector) | 20 |
| [`bloodstain_reader`](./unvalidated/bloodstain_reader) | 20 |
| [`codebase_graph_qa`](./unvalidated/codebase_graph_qa) | 15 |
| [`connections/word_groups`](./unvalidated/connections/word_groups) | 10 |
| [`core_code_syntax_generation`](./unvalidated/core_code_syntax_generation) | 20 |
| [`core_follow_instructions`](./unvalidated/core_follow_instructions) | 25 |
| [`core_multi_turn_memory`](./unvalidated/core_multi_turn_memory) | 20 |
| [`core_parallel_tool_calls`](./unvalidated/core_parallel_tool_calls) | 20 |
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
what counts as correct, where ground truth comes from, and how to keep scoring ungameable, then
writes `traptask.yaml`, `judge.py` and `grader.py`.

[`mineral-species-id`](https://trapstreet.run/tasks/mineral-species-id) and
[`karpathys-jagged-questions`](https://trapstreet.run/tasks/karpathys-jagged-questions) were
built exactly that way, by people who are not us.

## Results

[**RESULTS.md**](./RESULTS.md) — what the boards have measured, generated from the API.

## Licensing

MIT for the harness and hand-authored content; see [NOTICE](./NOTICE). Tasks that vendor
third-party data carry their own `ATTRIBUTION.md` or `LICENSE.md`, and that license governs the
vendored content. Importing a public benchmark? See [IMPORTING.md](./IMPORTING.md).
