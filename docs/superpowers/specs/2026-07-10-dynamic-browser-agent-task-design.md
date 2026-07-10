# Dynamic Browser Agent Task — Design

**Date:** 2026-07-10
**Status:** Design approved, not yet built
**Context:** Ruqi wants a TrapStreet task that discriminates *dynamic, multi-step*
agents from static workflows — the agent must replan mid-task in response to
changing state, not just execute a fixed script. This is one of two task ideas
brainstormed together (see also
[2026-07-10-code-review-skill-task-design.md](2026-07-10-code-review-skill-task-design.md)).

## 1. Purpose

Compare community **browser automation** agents/repos (browser-use, Skyvern, and
similar open-source projects — one of the "hot 2026 categories" identified in the
NO-43 positioning doc) on their ability to detect a mid-task state change and adapt,
rather than follow a pre-scripted action sequence. A static workflow fails outright
when the world changes under it; a genuinely agentic system notices and recovers.

## 2. Scenario

A single scenario type for v1: **sandbox e-commerce checkout**.

- The task repo ships a small, self-hosted mock e-commerce site (the "sandbox") —
  enough of a storefront + cart + checkout flow to be navigable by a browser agent,
  backed by a simple state store (e.g. SQLite or in-memory) that the grader can
  inspect after the run.
- Each case defines a goal (e.g. "buy product X, apply coupon Y, ship to address Z")
  and a **mid-flow disruption**: partway through checkout, one of the following
  fires — the target item goes out of stock, its price changes, or the coupon code
  becomes invalid.
- To succeed, the agent must notice the disruption (via the page's own feedback —
  no out-of-band signal) and adapt: pick a valid substitute meeting the original
  constraints, or otherwise recover to a valid completed order. A hardcoded script
  that assumes the original item/price/coupon stays valid fails by construction.

## 3. I/O contract

- Solution = a browser-automation agent (the community repo/tool under test),
  configured to run against the sandbox site (task ships instructions/compose file
  to start it locally) and pursue the case's goal.
- Runner executes the agent locally (per TrapStreet's client-executed model — the
  platform records, it doesn't run anything), then submits a `report.json` per the
  `TRAPTASK_MANIFEST` contract, including whatever final-state summary the agent
  can self-report (e.g. order confirmation ID).

## 4. Grading

Deterministic, no LLM judge:

- The task's own grader inspects the sandbox's backend state directly (not the
  agent's self-report) to check: (a) an order was actually completed, (b) the order
  reflects a valid response to the disruption (correct substitute item and/or
  correct final price — not stuck on the now-invalid original), (c) optionally,
  steps/time as a tiebreaker between otherwise-equal solutions.
- Because grading reads sandbox-side state rather than trusting the agent's report,
  the agent can't game the score by just claiming success.

## 5. V1 scope

- Single scenario type (checkout), **5–10 hand-authored case variants** — different
  product/disruption combinations — matching the v1 scale already used for
  `connections` (10 hand-authored puzzles).
- Fixed, non-randomized disruptions per case file, for reproducibility (same
  pattern as Connections' fixed puzzles).

## 6. Known risks / open items

- **Hosting cost**: the sandbox site has to be built and kept runnable locally by
  each runner (heavier than a pure I/O task, though still zero platform-side
  change, consistent with the Minecraft feasibility finding that TrapStreet
  executes nothing server-side).
- **Gaming vector**: disruption logic must not be trivially bypassable by a
  "detect any state change, immediately retry the same action" heuristic — the
  substitute/recovery must require genuine constraint-aware decision-making, not
  just retry-until-success.
- **Contestant pool**: like the Minecraft task, the pool of real browser-automation
  agents that can be dropped in and run is currently small; seeding the board with
  1–2 reference runs may be needed at launch.
