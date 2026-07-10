# Code review skill — real bugfix-commit detection

A code-review Claude Skill (SKILL.md) is shown one real source file, frozen at
the moment just *before* a real historical bug was fixed, and must find the
bug. Ground truth is the actual fix commit — not a synthetic injected bug.

## Why this task

Community "AI code reviewer" skills are one of the most duplicated categories
in the Claude Skills ecosystem — everyone has built one, nobody knows which
is actually good at catching real bugs versus producing plausible-sounding
comments. This task is a shootout: same 8 real diffs, same scoring, whichever
skill catches the most real bugs wins.

## Files

| File | Role |
|------|------|
| `gold.cases.json` | Source of truth — 8 real bugfix-commit cases. **Edit here.** |
| `build_cases.py`  | Generates `inputs/` + `expected/` and validates invariants. |
| `judge.py`        | Per-case scoring. |
| `grader.py`       | Run-level aggregation. |
| `inputs/<id>/question.txt`  | GENERATED — the prompt shown to the skill. |
| `expected/<id>/answer.json` | GENERATED — the gold bug location + keywords. |

Regenerate after editing cases: `python3 build_cases.py`

## Input / output contract

The skill receives `inputs/<id>/question.txt`: one file's contents shown at
its real absolute line numbers, plus instructions to reply with a single JSON
object:

```json
{"findings": [{"file": "<path>", "line": <int>, "description": "<1-2 sentences>"}, ...]}
```

Findings should be ordered most-confident-first. **Only the first 5 findings
are scored** (anti-shotgun) — flagging every line in the file does not help.

## Scoring

- **Per case** (`judge.py`, deterministic, no LLM judge): a finding "hits"
  the gold bug only if ALL THREE hold — (1) `file` matches the case's file by
  basename, (2) `line` is within `line_tolerance` (default 2, tightened to 1
  for case_07) of the real bug line, (3) `description` contains at least one
  of the case's pre-curated `keywords` as a whole word (word-boundary match,
  case-insensitive). Score is `1.0` if any of the first 5 findings hits, else
  `0.0`. Non-hitting runs still surface `best_match_signals` (which of the 3
  signals came closest) as an ungraded diagnostic.
- **Per run** (`grader.py`): mean score across cases; `n_passed` counts full
  hits; `by_category` breaks score down by bug category. Run passes at mean
  ≥ `0.5` (deliberately lower than `connections`' 0.75 — these are real bugs
  in real unfamiliar code, not a closed-form puzzle).

## Sources & licensing

Every case's snippet is a verbatim excerpt of a real pre-fix file, reproduced
under the source repo's own permissive license (attribution below satisfies
the license notice requirement for the small excerpts used here):

| case | bug category | source | license |
|---|---|---|---|
| case_01 | off-by-one | [pallets-eco/croniter@3ddcd13](https://github.com/pallets-eco/croniter/commit/3ddcd1385b53adabcce42bd14c6b8dfb83899fa6) | MIT |
| case_02 | null/None deref | [googlefonts/gftools@f28317c](https://github.com/googlefonts/gftools/commit/f28317cab96bda1d8e07f5b044f645e6e4c07cab) | Apache-2.0 |
| case_03 | logic error | [sgl-project/SpecForge@361f5a1](https://github.com/sgl-project/SpecForge/commit/361f5a11921264ae5c329bfa4968008ce4d2f231) | MIT |
| case_04 | race condition | [google/bumble@55d8171](https://github.com/google/bumble/commit/55d8171ad89a668a04aaab905efa320ac0e8b9b1) | Apache-2.0 |
| case_05 | resource leak | [miketheman/pytest-socket@2aaaee1](https://github.com/miketheman/pytest-socket/commit/2aaaee1bc226ddb996dd5498f3f64e9387f91db5) | MIT |
| case_06 | missing auth check | [homeassistant-ai/ha-mcp@9f5b085](https://github.com/homeassistant-ai/ha-mcp/commit/9f5b085ad4a7b38b067c9da0dc5b45462c4d796e) | MIT |
| case_07 | mutable default arg | [xarray-contrib/xarray-spatial@5103dc1](https://github.com/xarray-contrib/xarray-spatial/commit/5103dc15c84f19c1c373a7b453634c28fbd75f15) | MIT |
| case_08 | broad except | [xarray-contrib/xarray-spatial@c6daae5](https://github.com/xarray-contrib/xarray-spatial/commit/c6daae54b8776b7c6ac67c77fcb9f9531cb56069) | MIT |

**Known limitation — leakage risk:** because these are real commits (not
synthetic bug injection), a skill's underlying model may have seen the exact
commit during pretraining. Mitigated, not eliminated, by preferring smaller
repos (roughly 277–3,897 stars at time of writing, not framework-scale
mega-repos) and recent commits.
The design doc also floated renaming identifiers as an additional mitigation;
v1 ships the snippets **verbatim** instead (see "Out of scope" in the
implementation plan for why). See
`docs/superpowers/specs/2026-07-10-code-review-skill-task-design.md` in the
`trapstreet-tasks` repo for the full design writeup and tradeoffs.

## Run

```bash
python3 build_cases.py                 # (re)generate cases
python3 -m pytest tests/ -v            # unit tests
```
