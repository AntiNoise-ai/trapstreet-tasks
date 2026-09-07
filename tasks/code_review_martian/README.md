# code_review_martian

Martian's Code Review Bench, run as a trapstreet task: 50 real merged pull
requests from five open-source projects, 173 human-verified golden comments, and
Martian's judging pipeline vendored unmodified.

**We rank submitted pipelines. Martian ranks deployed products.** Their board
measures review bots already installed on public repos, so its entry bar is
600–1,000 reviewed public PRs from an attributable bot account — a bar no
individual clears, and one that by their own account cannot measure "a tool that
hasn't been publicly deployed, or a new model that hasn't been integrated into a
product yet." That population is what this task is for. See `NOTICE` for
provenance and licensing.

## Why the judging code is vendored byte-for-byte

`judge/` holds Martian's `step2` / `step2_5` / `step3` and `score_profiles.py`
unchanged. Only `judge/adapter.py` (traplite report ↔ their input shape) and
`build/` are ours.

The judge model is pinned to `claude-opus-4-5-20251101`. This is not a taste
call: across the three judges Martian published, the same tool's core-profile F1
moves a median of **5.3** points and up to **9.5** — while adjacent tools on
their leaderboard are often 1–2 points apart. Change the judge and the numbers
stop being comparable with the 21 tools they publish, which is the whole reason
to run their benchmark rather than write our own.

## Where the answers live

Golden comments, the judge config and the case manifest are in
`trapstreet-tasks-private/tasks/code_review_martian/`. This directory holds no
answers; `expected.sha256` binds the two halves without revealing either.

**But the gold is public anyway** — it is MIT-licensed on Martian's GitHub. A
submitted pipeline can read it, and no judging location prevents that. This
track is therefore **self-reported**, in the sense SWE-bench and SWE-PRBench use
the word, and must be labelled as such wherever it is shown. Only a case set we
mine ourselves and never publish can carry a verified score.

## Scoring

Per-PR precision, recall and F-beta against the golden comments, under Martian's
three profiles:

| Profile | Categories | Golden comments |
|---|---|---|
| strict | bug, security, concurrency, data, api | 139 |
| **core** (default) | strict + perf, test_gap, doc_defect | 158 |
| all | core + style, speculative | 173 |

A match on a golden comment outside the active profile is **matched-excluded** —
neither rewarded nor penalised. That is the mechanism worth borrowing on its own:
it stops a tool being punished for finding a real issue the profile does not
score, which is the same failure our own `unadjudicated` channel exists to avoid.

## Build

```
build/fetch_prs.py         fetch the 50 diffs into _cache/ (regeneratable)
build/render_questions.py  _cache/ -> questions.yaml
```

`questions.yaml` is what traplite's `{{QUESTIONS_YAML_URL}}` points at, pinned to
a commit. The orchestrating agent loads the **whole** file before launching one
subagent per case, so total size is capped by that agent's context rather than by
anything in git — the cap lives in the renderer, and any PR excluded by it is
recorded in the manifest with the reason.
