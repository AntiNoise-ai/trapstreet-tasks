# Code Review Skill Task — Design

**Date:** 2026-07-10
**Status:** Design approved, not yet built
**Context:** Ruqi wants a TrapStreet task on a topic where many people have
independently built overlapping Claude Skills (SKILL.md), so a comparison is
actually meaningful — "everyone built the same thing, nobody knows which is good."
Researched candidate topics by duplication/discussion volume (web search,
2026-07-10): **document processing** (pdf/docx/xlsx/pptx) is the single most
commonly cited duplicated-skill category across every awesome-claude-skills list,
but TrapStreet already has tasks in that space (`pdf_reader`, `core_pdf_ocr`,
`spreadsheet_reader`, `doc_editing`) that compare a different thing (raw model
capability, not skill implementations). Ruqi chose **code review skills** instead —
also a heavily duplicated category (this very toolset ships `code-review` and
`security-review`), with the tradeoff that its audience skews technical rather
than TrapStreet's usual non-technical-industry-worker persona. This is one of two
task ideas brainstormed together (see also
[2026-07-10-dynamic-browser-agent-task-design.md](2026-07-10-dynamic-browser-agent-task-design.md)).

## 1. Purpose

Compare community "AI code reviewer" Claude Skills on whether they actually catch
a real bug in a real diff — not whether they can produce plausible-sounding review
comments.

## 2. Ground truth: real historical bugfix commits

- Each case is built from a real open-source bugfix commit: the **pre-fix**
  version of the diff/file is what the skill under test reviews; the commit's
  actual fix (bug type, location, description) is the ground truth.
- Ruqi chose real commits over synthetic bug injection, trading some leakage risk
  for realism. Mitigations (partial, not a full fix — documented as a known
  limitation):
  - Prefer smaller/lower-star repos and more recent commits, to reduce the chance
    a case is already memorized.
  - Apply cosmetic transforms to the diff before use (rename identifiers,
    reformat) to reduce verbatim-recall hits while preserving the bug's semantics.

## 3. I/O contract

- Solution = a Claude Skill (SKILL.md) that, given the pre-fix diff, is invoked
  (via Claude Code or another skill-compatible host) to produce a review: a list
  of findings, each with a file/line reference and a description.
- Runner loads the skill, runs it against the case's diff, and submits a
  `report.json` per the `TRAPTASK_MANIFEST` contract containing the raw findings
  list.

## 4. Grading

- Grader compares the skill's findings against the case's ground-truth bug
  (file/line + description match, likely via an LLM-judge step since "does this
  finding describe the same bug" isn't purely mechanical — unlike Task 1's
  deterministic sandbox-state check).
- **Anti-shotgun rule** (same pattern as `connections`): only the first *K*
  findings are scored, so a skill can't game the score by flagging every line in
  the diff. Score is hit/miss (or graded partial credit) on whether the true bug
  appears within those first K findings.

## 5. V1 scope

- Single language for v1 — **Python** (broadest coverage among community
  code-review skills).
- **5–10 hand-picked real bugfix-commit cases**, spanning different bug categories
  (logic error, security vulnerability, off-by-one/boundary condition, race
  condition, etc.) so the task discriminates rather than saturates.

## 6. Known risks / open items

- **Leakage is only mitigated, not eliminated.** A skill's underlying model may
  have seen the exact commit during pretraining; this is an explicit, accepted
  limitation of choosing real commits over synthetic injection.
- **Audience mismatch**: TrapStreet's stated persona is non-technical industry
  workers (NO-43), but "code review skill" is inherently a developer-facing topic.
  Accepted tradeoff for this task, per Ruqi's choice.
- **Judge subjectivity**: unlike Task 1's deterministic state check, matching a
  finding to the ground-truth bug likely needs an LLM judge, which is softer to
  game and harder to fully trust than mechanical grading — needs careful judge
  prompt design and probably a held-out check that the judge doesn't over/under
  credit near-miss findings.
