# Raising a task's difficulty — what the 2026 work actually does

Written the day `frontend_silent_defects` returned 18/18 across three frontier
arms. The question it is answering: when every arm passes everything, what do
you change?

## The correction this research forced

I told the task owner the axis was **length** — METR measures task duration as
the dominant predictor of agent success (R²=0.83), our brief was a ten-minute
job, therefore no number of extra constraints would close the gap, therefore the
only fix was to rebuild it as a multi-step repo task.

That was too narrow. The sharper statement, and the one our own data supports:

> **We graded the saturated dimension.**

Behaviour, robustness, responsive, constraint-compliance — *does it work* — is
exactly what three frontier models already do at 100%. Cognition's
[FrontierCode](https://cognition.com/blog/frontier-code) is the direct
counterexample to "bigger is harder": it uses **smaller patches than DeepSWE and
is harder for agents**, because difficulty comes from what is graded, not from
size. Its Diamond split spreads Claude Opus 4.8 at **13.4%**, GPT-5.5 at
**6.3%**, Gemini 3.1 Pro at **4.7%** — unsaturated *and* separating.

Be careful how far that generalises: FrontierCode's tasks are still real-repo
work, far longer than a one-shot page. It licenses "what you grade is an
independent difficulty lever *within* a family", not "length does not matter".

## Four mechanisms, in the order they are worth trying

### 1. Grade the unsaturated dimension (FrontierCode)

Six graded dimensions, not one: behavioural correctness, **regression safety**,
mechanical cleanliness, **test correctness**, **scope discipline**, code quality.
The three in bold are the ones nobody's frontend task grades, and all three are
deterministic.

Two structural devices worth stealing outright:

- **Blockers vs non-blockers.** Correctness criteria are blockers: fail one and
  the whole task scores zero, no partial credit. Style criteria are
  non-blockers and only move the remainder. This is how you keep a quality
  dimension in the score without letting a broken submission buy its way up.
- **Reverse-classical testing.** Where the agent writes tests, those tests
  **must fail against the original broken code**. It is a cheap, mechanical way
  to kill tests that assert nothing — the single most common way a
  test-writing task saturates.

Applied here: `case_04` looked like a scope check and is not. It tests three
*named* prohibitions — no CSS grid, nothing external, no emoji. Scope
discipline is "did it build things nobody asked for", and it is **unbuilt**, not
weak. `inspect.mjs` already reads the source, so it is also the cheapest of
these to add.

### 2. Dense scoring — a precondition, not a refinement

[Long-Horizon-Terminal-Bench](https://arxiv.org/abs/2607.08964) decomposes each
task into weighted subtasks, `R = Σ(w_k·r_k) / Σ(w_k)`, and the reason is
measured: **62.8% of runs make partial progress that binary grading throws
away.** It separates timeouts from "false finishes" (stopping early at R≥0.75)
from near-misses (0.75≤R<0.95) — distinctions pass/fail cannot see.

Our `grade()` returns 1.0 only if every check in the deciding family passes. At
18/18 that cost nothing. **The moment difficulty goes up it becomes the dominant
failure mode**: every arm lands on 0.0 and we learn nothing about which one got
closer. Any harder version needs dense scoring first, or it produces a different
kind of uninformative board.

### 3. Calibrate empirically, before authoring the set

Long-Horizon-Terminal-Bench generated **120 candidate tasks and kept 46**,
calibrating by "repeatedly running an agent under 1.5-hour time budgets and
adjusting task design until the tasks are challenging but still solvable in
principle."

That is the loop we did not run. We authored nine cases and then discovered the
difficulty. The order is: build one case, run it against a real arm, adjust
until it is challenging-but-solvable, *then* author the set. Same lesson as
[cheap measurements before authoring](making-a-task-discriminate.md), now with a
published procedure attached.

### 4. Generate the stress, do not enumerate it

PushBench-style hidden stress cases are produced dynamically — nested
structures, gzip-plus-base64 wrappers, renamed fields, missing values, injected
noise, alternative conventions — rather than written out.

Our `case_06` is thirteen hand-written `__DATA__` payloads. All three arms took
13/13. A hand-written list has a ceiling the author can see; a generator does
not, and it cannot be memorised or targeted.

### 5. BenchEvolver — noted, poor fit here

[BenchEvolver](https://arxiv.org/abs/2606.01286) evolves reference *solutions*
through structured transformations and derives statements and tests from the
evolved solution, keeping everything grounded in executable semantics. It moved
LiveCodeBench frontier Pass@1 from **over 90% to 27.5–62.6%**, and the evolved
tasks stay hard for the model that generated them.

It needs a reference solution with an executable correctness oracle. Our open
briefs have neither, and evolving `fixtures/good.html` yields harder *pages*,
not harder *briefs*. Worth knowing, not worth leading with.

## One idea to check before it goes on any shortlist

Reverse-classical testing adapted to a build task — *the solution must also
supply checks, and those checks must fail against a broken version we hand it* —
is genuinely hard and genuinely unsaturated.

But **`expected/` is readable by solutions**: trap-cli runs them unsandboxed
with an absolute inputs path. A solution that can read the gold can read
whatever defines "the broken version". Whether that closes the exploit or widens
it has to be settled *before* the idea is costed, not after.

## Which of these a one-shot generation task can actually use

Applied to `frontend_silent_defects` — a task where the tool is handed a brief
and prints one self-contained page. Of eight mechanisms, **two add difficulty**:

| mechanism | usable here | why |
|---|---|---|
| dynamic stress generation | **yes, directly** | a hand-written payload list has a ceiling the author can see |
| budget / over-build limits | **yes, adapted** | see below — it is not the same thing as scope discipline |
| dense scoring | yes, but adds none | it makes difficulty *readable*, it does not create it |
| blockers / non-blockers | yes, but adds none | an aggregation rule |
| empirical calibration | yes, but adds none | a process, not a knob |
| regression safety | **no** | needs an existing codebase to not break |
| test correctness / reverse-classical | **no**, not without changing the task's shape | needs the tool to write tests, and collides with a readable `expected/` |
| BenchEvolver | **no** | needs a reference solution with an executable oracle |

**Scope discipline does not port, and the reason matters.** FrontierCode
measures it against a reference patch — "changes touch only necessary files and
lines". A page generated from a brief has no *before*. If the tool adds an FAQ
section nobody asked for, there is no baseline that says whether that is
overreach or judgement. Written as an explicit list of forbidden things it
collapses back into `case_04`, which all three arms passed. What survives the
translation is a **budget** — a cap on DOM nodes, CSS rules, source bytes,
stated in the brief — which is measurable, and whose numbers must be calibrated
from real submissions rather than guessed.

## Why most of them do not port: relational vs absolute

Sorting the dimensions by whether they are still unsaturated turns up a pattern
the papers do not state, and it is the most useful thing in this document:

> **Every unsaturated dimension is relational — defined against something that
> already exists.** Regression safety, against a codebase you must not break.
> Scope discipline, against a reference patch. Test correctness, against a
> broken version your tests have to catch.
>
> **Every saturated dimension is absolute** — does it work, does it survive bad
> input, does it hold at 375px, did it obey the stated constraints.

FrontierCode's own blocker / non-blocker split falls the same way: its blockers
are the relational criteria; its non-blockers are the absolute ones (style,
mechanical cleanliness) that it explicitly declines to let decide a score.

If that holds, our 18/18 is not "the brief was too short" and not quite "we
graded the wrong dimension" either. It is structural:

> **A one-shot generation task has no baseline, and every dimension that still
> separates frontier models is measured against a baseline.**

This is an inference, not a result. It is also cheap to test, because it makes a
falsifiable prediction about the one absolute knob left: **if dynamically
generated hostile data also fails to separate the arms, the absolute dimensions
are saturated across the board and the shape is the problem.** If it does
separate, the inference is wrong and the task is repairable in place.

That test is the next thing built.

## Numbers worth keeping

| | |
|---|---|
| FrontierCode Diamond | Opus 4.8 **13.4%** · GPT-5.5 **6.3%** · Gemini 3.1 Pro **4.7%** |
| BenchEvolver on LiveCodeBench | >90% → **27.5–62.6%** Pass@1 |
| Partial progress lost to binary grading | **62.8%** of runs |
| METR Time Horizon 1.1 (Jan 2026) | 31 tasks, each ≥8 human hours; horizons doubling every **123 days** |
| Chained reliability | a 95%-reliable step, twenty deep, is **36%** end-to-end |

## Sources

- [FrontierCode](https://cognition.com/blog/frontier-code) — Cognition
- [BenchEvolver: Frontier Task Synthesis via Solution-Centric Evolution](https://arxiv.org/abs/2606.01286) (arXiv 2606.01286)
- [Long-Horizon-Terminal-Bench](https://arxiv.org/abs/2607.08964) (arXiv 2607.08964)
- [Task-Completion Time Horizons of Frontier AI Models](https://metr.org/time-horizons/) — METR
- [Lost in Benchmarks? Rethinking LLM Benchmarking with Item Response Theory](https://arxiv.org/abs/2505.15055) (arXiv 2505.15055)
