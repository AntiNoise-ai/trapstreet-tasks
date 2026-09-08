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

## Layout

```
traplite-question.yaml   49 cases; each names its diff by pinned raw URL + sha256
prs/*.diff               the diffs, byte-identical to GitHub's .diff endpoint
prs/index.json           size and hash per case
judge/                   Martian's pipeline, unmodified, plus our adapter
NOTICE                   per-project licences, repeated in every question
```

The questions reference their material rather than carrying it, following what
`pdf_chart_reasoning` settled. Inlined, the 49 diffs made a 1.39 MB spec that an
orchestrating agent must hold whole before launching anything; referenced, the
spec is 86 KB and each subagent fetches only its own diff. Both halves live in
this repository at one commit, so there is one pin to keep straight rather than
two.

**A pinned commit decides what else its URL can reach.** Nothing in this task's
public tree has ever held a golden comment — checked, not assumed. But Martian
publishes them, so no pin makes this hold-out: every question asks the solver not
to open the upstream pull request, where the reviewer's own comments may sit, and
that request is unenforceable. Self-reported, as above.

Build scripts are in the private half's `tools/`, beside the gold they read:
`fetch_prs.py` pulls the diffs, `build_traplite_questions.py --sha <40-hex>`
renders the spec against the commit that serves them.
