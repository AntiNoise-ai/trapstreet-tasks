# Connections Task — Design

**Date:** 2026-07-02
**Status:** Design (awaiting user review)
**Author:** brainstormed with Ruqi

## Summary

A new TrapStreet task in the family of light/fun, cross-model-comparison evals
(sibling to `personality/mbti_profile`). The model is given 16 shuffled words
and must partition them into **4 groups of 4**, the NYT *Connections* format.

Unlike MBTI (format-only, no correct answer), Connections has an **objective
ground truth**, so it discriminates model skill: semantic reasoning plus the
ability to resist deliberate **trap words** (a word that surface-fits the wrong
group). The trap mechanic is thematically on-brand for "trapstreet".

Puzzles are **original, hand-authored** — never scraped from NYT — to avoid
copyright/ToS issues and, critically, to avoid **leakage** (strong models have
memorised published NYT answers). Original puzzles also let us control
difficulty and trap density.

## Why this fits TrapStreet

- **Single-shot I/O** — 16 words in, 4 groups out, one turn. No live loop, no tracing.
- **Objective, auto-gradeable** — deterministic set comparison against the gold partition.
- **Fun / relatable to non-tech users** — millions play Connections; "which AI groups best" is instantly graspable.
- **Discriminating** — genuinely hard; rewards semantic reasoning and trap resistance.
- **Not a saturated academic benchmark** — original content, novel framing.

## Task location & files

Nested under a `connections/` group so difficulty variants can be added later,
matching the `personality/mbti_profile` pattern:

```
tasks/connections/word_groups/
  traptask.yaml                    # case list + judge/grader cmd
  gold.cases.json                  # all puzzles + doc block
  judge.py                         # per-case scoring
  grader.py                        # run-level aggregation (standard shape)
  README.md                        # schema + how-to
  inputs/<case_id>/question.txt    # what the model receives
  expected/<case_id>/answer.json   # gold partition
```

## Input contract (`inputs/<case_id>/question.txt`)

Plain-text prompt containing:

1. The rules (partition 16 words into exactly 4 groups of 4; every word used once).
2. The 16 words in a **fixed shuffled order** (deterministic per case — no runtime randomness).
3. A strict output-format instruction.

**Required model output** — a single JSON object, fences tolerated:

```json
{
  "groups": [
    {"theme": "short label", "words": ["W1", "W2", "W3", "W4"]},
    {"theme": "...",          "words": ["...", "...", "...", "..."]},
    {"theme": "...",          "words": ["...", "...", "...", "..."]},
    {"theme": "...",          "words": ["...", "...", "...", "..."]}
  ]
}
```

The `theme` label is **collected but not graded** (models phrase categories
differently). Grading is purely on the partition of words. The theme is
surfaced in metrics for qualitative comparison.

## Gold contract (`expected/<case_id>/answer.json`)

```json
{
  "id": "<case_id>",
  "category": "<difficulty tier: easy | medium | hard>",
  "groups": [
    {"theme": "canonical label", "tier": "yellow|green|blue|purple", "words": ["...", "...", "...", "..."]},
    ...4 total...
  ],
  "traps": ["<word>", ...]   // words that surface-fit a wrong group; metadata for analysis
}
```

## Grading (`judge.py`, per case)

1. **Parse** the model output (strip ``` fences, tolerate minor whitespace). If
   it is not valid JSON with a `groups` list → `score = 0.0`, set a
   `format_ok: false` flag in metrics.
2. **Normalise** each group's `words` to a case-insensitive, trimmed set.
3. **Score = (number of gold groups exactly reproduced) / 4.** A gold group
   counts iff **some** model group's word-set equals that gold group's word-set
   exactly (all 4, no extras, no misses). Set-equality means word order and
   which model-group-slot it landed in do not matter.
4. **Headline metric** `solved = (score == 1.0)` — did the model crack the whole
   puzzle. Surfaced in metrics alongside `groups_correct` (0–4).

**Robustness:** if the model emits duplicate words, wrong counts, or 3/5-word
groups, those simply fail to set-match any gold group and score 0 for that
group — no crashes, no special-casing.

### Metrics surfaced per case
- `score` (0.0–1.0), `groups_correct` (0–4), `solved` (bool)
- `format_ok` (bool)
- `category` (difficulty tier, for by-category breakdown)
- model `themes` (list, ungraded metadata)

## Aggregation (`grader.py`, run-level)

Reuse the standard shape from `personality/mbti_profile/grader.py` and
`pdf_reader`:

- `score` = mean per-case score across scored cases
- `n_passed` = count of fully-solved cases (`score == 1.0`)
- `by_category` = mean score per difficulty tier
- latency / cost passthrough from trap-captured per-case duration & usd_cost
- `PASS_THRESHOLD = 0.75` on the mean (tunable; this is only the run pass/fail line)

## Puzzle authoring — quality invariants

Each seed puzzle MUST satisfy, and this is checked by a small validation script:

- Exactly 16 distinct words, partitioned into exactly 4 groups of exactly 4.
- **Every word belongs to exactly one gold group** — the "correct" home. Lures
  are *surface* pulls, never true dual-membership.
- **At least one trap word** per puzzle: a word whose obvious/surface reading
  fits a *different* group than its true home (recorded in `traps`).
- Difficulty tiers within a puzzle follow the Connections convention
  (yellow = straightforward → purple = wordplay/tricky).

### Seed set (initial)

**10 original puzzles** across three difficulty tiers:
- `easy` ×3 — clean categories, one mild lure
- `medium` ×4 — 2–3 lures, some wordplay
- `hard` ×3 — dense cross-category traps / wordplay-heavy (e.g. the all-cards
  soup sample: card games vs suits vs court cards vs `BLACK ___`)

Count is a starting point; more can be appended without schema change.

## Anti-leakage & fairness

- 100% original puzzles; gold answers never published to a scrapeable surface.
- Word order fixed per case (no runtime randomness → reproducible scoring).

## Testing plan

**Puzzle validation** (authoring-time script):
- every puzzle: 16 distinct words, 4×4 partition, ≥1 declared trap, traps
  actually appear in the word list.

**Judge unit tests** (`judge.py`):
- perfect answer → `1.0`, `solved=true`
- 2 of 4 groups correct → `0.5`
- fully scrambled → `0.0`
- malformed / non-JSON → `0.0`, `format_ok=false`
- ```json-fenced valid answer → parsed, correct score
- different theme labels but correct word-sets → full credit (themes ungraded)
- word case/whitespace variants (`"Jack"` vs `"JACK"`) → still match

## Out of scope (YAGNI)

- The real multi-turn "4 mistakes allowed" mechanic (needs a live loop; we grade the one-shot partition instead).
- Auto-generation of puzzles by an LLM (hand-authored for quality; can revisit if we need volume).
- Grading the theme labels.

## Open items for review

- Seed count (10) and tier split — adjust to taste.
- `PASS_THRESHOLD` (0.75) — tune once we see real model scores.
- Task path `tasks/connections/word_groups/` — confirm naming.
