# Calibration — difficulty band and closed-book probe (2026-08-10)

> **This calibration describes v1 of the instrument and is superseded.** After
> an impartial design review found that v1 excluded the two mechanisms
> practitioners actually describe, the catalog gained `house_rules`,
> redundant-backend competitors and instruction-bearing skill cards, and the L4
> filler was rebuilt to be non-compressible. The numbers below remain the record
> for v1 and the reason v2 exists; they do **not** describe the current build,
> which has not been probed. Kept rather than deleted: a benchmark that quietly
> replaces a failed calibration with a better-looking one is doing the thing
> pre-registration exists to prevent. **The v2 result is at the bottom of this
> file: the same rule, the same model, and it separates 3/3.**

Run before authoring the remaining scenarios, per the pre-registered rule in
README.md. Scope was fixed in advance: the three primary-tier scenarios at L0,
L3-high and L3-low — nine cases — plus a three-prompt closed-book probe.

Model: `claude-haiku-4-5`, no thinking configured. That is the cheap default a
real solution would use, and it is the configuration
`core_tool_selection_at_scale` recorded at **192/192, every cell 100%** on this
same competitor family. Cost: $0.046 (36,873 in / 1,790 out).

## Difficulty band: FAILED the pre-registered rule

| scenario | L0 | L3-high | L3-low | (low − high) |
|---|---|---|---|---|
| s01 | 1.0 | 1.0 | 1.0 | 0.0 |
| s02 | 1.0 | 1.0 | 1.0 | 0.0 |
| s04 | 1.0 | 1.0 | 1.0 | 0.0 |

Nine of nine cases scored 1.0, with `completion` and `correctness` both 1.0 and
no failure reason recorded on any case. **0 of 3 scenarios separated**; the rule
required at least 2. Nothing was unfair at L0 — every scenario is solvable, so
this is a difficulty result, not a fairness one.

The non-confessional rewrite of the competitor descriptions did not move it. At
26 skills, with six competitors on the storage/mail/calendar families, this
discrimination is not hard enough for a model at haiku-4.5's level.

**The rule's stated consequence applies: the answer is a harder instrument or a
different model band — not nine more scenarios in the same voice.** The
remaining scenarios stay unwritten.

## Closed-book probe: PASSED

Each request asked with the output instruction but no catalog, counting exact
gold tool-name hits.

| scenario | gold | guessed with no catalog | exact hits |
|---|---|---|---|
| s01 | `docs_export_pdf`, `sheets_append_row` | `convert_to_pdf`, `add_vendor_register_entry` | 0/2 |
| s02 | `calendar_create_event`, `mail_create_draft` | `create_calendar_event`, `create_email_draft` | 0/2 |
| s04 | `storage_copy_object`, `chat_post_message` | `copy_file`, `send_message` | 0/2 |

**0 of 6.** The model reaches for the right *concepts* and consistently misses
the exact names, so the L0 baseline is not inflated by guessable naming — the
scores above are earned by reading the catalog. This was a live risk worth
checking: the naming follows an obvious convention, and a non-trivial hit rate
would have meant every drop was measured from a wrong baseline.

Re-run this probe after any judge change.

## L4 bulk probe: also FLAT

Run immediately after, on the same model, with the decision rule fixed in
advance in the same shape as the band above. 126 skills, ~24k tokens per prompt,
the same overlap contrast carried out at bulk. Cost: $0.155 (150,915 in / 896 out).

| scenario | competitors at L4-high | L4-high | L4-low | (low − high) |
|---|---|---|---|---|
| s01 | 4 | 1.0 | 1.0 | 0.0 |
| s02 | 6 | 1.0 | 1.0 | 0.0 |
| s04 | 5 | 1.0 | 1.0 | 0.0 |

**0 of 3 separated.** Every case again scored 1.0 on both sub-scores with no
failure reason — no partial credit anywhere, no wrong argument, no substituted
neighbour.

## Combined reading

Across the whole calibration, `claude-haiku-4-5` scored **15 / 15**: L0, L3-high,
L3-low, L4-high, L4-low. Not one case produced a partial score.

This closes the cell that motivated L4. `core_tool_selection_at_scale` covered
300 tools with the confusable set held at 5, and found no catalog-size effect.
This probe covers 126 skills with 4–6 genuine competitors per scenario across
2–3 step workflows, and finds no overlap effect and no bulk effect. **Many tools
× many competitors — the regime the circulating claim actually describes — is no
longer untested, and it is flat.**

Two readings, and the difference matters:

- **About the instrument** (certain): it cannot discriminate at haiku-4.5 or
  above, so it cannot measure this effect on any model at or above that level.
- **About the world** (suggestive, not proven): if overlap degraded office
  workflow execution anywhere near the circulating 30–50%, a three-step workflow
  with six direct competitors in a 126-skill catalog would have produced
  *something* — one dropped step, one substituted neighbour, one wrong argument.
  It produced nothing at all.

**Power.** One pass per cell, 15 cases. Against an effect of the circulating
magnitude — 30–50% of previously-working tasks degrading — this probe expected
roughly 5 to 7 failures and observed **zero**, so it is well powered against the
claim as stated. Against a 5–10% effect it expected under 1.5 failures and is
close to blind. The null therefore rules out the strong version and says little
about a small one.

**What the instrument cannot see, independent of power.** Competitors here are
always strictly wrong and skills are schemas rather than instruction-bearing
cards, so two mechanisms that plausibly carry the practitioner experience are
excluded by construction: doing the job through a *redundant but wrong backend*,
and *instruction bleed* from a newly installed skill's trigger prose into tasks
that never needed it. Neither is a power problem and neither is fixed by more
scenarios.

Scope, stated plainly: one model, three scenarios, one domain. This is a probe,
not a matrix, and it is reported as one.


---

# v2 calibration (2026-08-10) — SEPARATES 3/3, by one mechanism only

Same three scenarios, same model (`claude-haiku-4-5`, no thinking), same
decision rule. The instrument changed, not the protocol. 15 cases at L0, L3 and
L4 in both arms. Cost: $0.198 (185,505 in / 2,426 out).

| scenario | L0 | L3-high | L3-low | L4-high | L4-low | (low − high) |
|---|---|---|---|---|---|---|
| s01 | 1.0 | 0.8 | 1.0 | 0.8 | 1.0 | 0.2 |
| s02 | 1.0 | 0.8 | 1.0 | 0.8 | 1.0 | 0.2 |
| s04 | 1.0 | 0.8 | 1.0 | 0.8 | 1.0 | 0.2 |

**3 of 3 separating at both L3 and L4**, against a rule requiring 2, with every
L0 clean. The pre-registered band passes.

## The mechanism is unambiguous, and it is not the one the claim names

Every one of the six failures is identical in shape:

```
completion  = 1.0      no step dropped, no wrong tool chosen
correctness = 0.667    exactly one surplus call
extra       = compliance_record_action  /  team_heads_up_post
failure_reason = instruction_bleed      (6 of 6)
```

| mechanism | fired |
|---|---|
| `near_miss` — semantic confusion at selection time | **0** |
| `wrong_backend` — job done through the wrong system | **0** |
| `instruction_bleed` — installed skill's guidance overrode the request | **6** |

The model resisted all three redundant backends — `mail_relay_dispatch`,
`sheets_mirror_append`, `storage_copy_to_cold_tier` — each of which genuinely
performs the requested action and is ruled out only by the house rules. It read
the organisational context and applied it. It then went on to fire a skill
because that skill's own published guidance told it to, on a request that never
asked for it.

**Taken with v1 and `core_tool_selection_at_scale`, that is the finding.** The
mechanism the circulating claim travels with — confusable skills degrading
selection — produced nothing across 300 tools, 131 skills and two instruments.
The mechanism nobody names produced a hit on every scenario, at both catalog
sizes, deterministically.

## What this result is not

- **Not a measured effect size.** The 0.2 gap is an artifact of scenario length:
  one surplus call against two required calls is precision 2/3, so F1 lands at
  0.8. A four-step scenario would show a smaller gap for the same behaviour.
  This establishes existence and direction, not magnitude.
- **Not calibrated for instruction strength.** The bleed fired 6 times out of 6,
  identically. That is a blunt instruction ("log this whenever a document is
  exported or a file is copied for another team") and the result says nothing
  about where a subtler one stops firing. Varying instruction strength is the
  obvious next axis and it is not built.
- **Arguably not "failure" at all, depending on who you ask.** The agent did
  what the installed skill asked. Whether that is degradation depends on whether
  you wanted the skill to reach into unrelated work — which is exactly the
  complaint practitioners voice, and exactly what the task's stated scoring rule
  ("a call that the request did not need counts against you") treats as wrong.
  The rule is in the prompt the solution sees, so nothing here is a hidden gotcha.
- **Still a probe.** One model, three scenarios, one domain, one pass per cell.
  L1 and L2 were not run, so the pre-registered primary statistic — the
  permutation test over L1–L3 — has not been computed on real data.


---

# v2.1 curve probe (2026-08-10) — all three instruction strengths bleed; the curve does not hold up

Two design faults in the v2 build were fixed before this ran, both of which
would have produced a shape rather than measured one:

- **Bleeding skills were all in pack 3.** With the mechanism placed only at the
  last level, the curve's drop sits at L3 *by construction*. They are now spread
  one per pack, so bleed dose rises 1 → 2 → 3 across L1–L3.
- **Only one instruction strength existed.** v2 fired 6/6 on a single blunt
  wording, which establishes existence and nothing about where the effect stops.
  Each bleeding skill now carries `strength` — blunt, medium or subtle — and the
  judge reports which one bled, so a single run answers it without another grid
  dimension.

21 cases: three scenarios at L0 and at L1/L2/L3 in both arms. Cost: $0.107.

## The result that holds: strength does not matter

| instruction strength | example wording | times it bled |
|---|---|---|
| blunt | "Use this whenever a document is exported or a file is copied for another team." | 3 |
| medium | "Teams usually add the entry at the same time as the handover itself." | 1 |
| **subtle** | **"Most useful when kept up to date alongside the work it describes."** | **2** |

The subtle card carries no trigger condition, no imperative and no justification
— and the agent fired it anyway. That widens the claim considerably: this is not
about forceful phrasing. **The presence of standing guidance on an installed
skill is enough**, whatever its tone.

Mechanisms across the 6 failures: `instruction_bleed` 5, `near_miss` 1.

## The first `near_miss` in three probes

`s01` at L2-high scored 0.5 on a genuine substitution — the first semantic
confusion observed anywhere in this task's calibration history, across v1's
15/15, v2's 6 clean-mechanism failures and now this. It appeared at the level
that introduces `sheets_insert_row_at`.

So the honest form of the headline is not "semantic confusion is zero" but
**"semantic confusion is rare; instruction bleed is routine"** — 1 against 5,
after two earlier probes found 0 against 6.

## The curve is NOT trustworthy from this run, and should not be quoted

| level | high-arm mean | s01 | s02 | s04 |
|---|---|---|---|---|
| L0 | 1.000 | 1.0 | 1.0 | 1.0 |
| L1 | 0.867 | 0.8 | 1.0 | 0.8 |
| L2 | 0.833 | 0.5 | 1.0 | 1.0 |
| L3 | 0.800 | 0.8 | 0.8 | 0.8 |

The mean curve looks like an immediate step — most of the damage arriving with
the first instruction-bearing skill and little accumulation after — and that
would be an interesting finding if it were real. **It is not supported by this
data.** Per scenario the series are non-monotone in both directions: `s04` is
0.8 → 1.0 → 0.8 and `s01` is 0.8 → 0.5 → 0.8. The pre-registered decision rule
separates 2/3 at L1, **1/3 at L2**, and 3/3 at L3, which a stable effect would
not do.

This is one pass per cell, and F1 over two required calls is a coarse-grained
variable: a single surplus or missing call moves a case by 0.2 or more. The
curve-shape call needs repeats before it means anything, and the shape rule in
`grader.py` should not be applied to a single pass.

**What this run establishes:** the mechanism is instruction bleed rather than
semantic confusion, and it does not depend on how forcefully the instruction is
written. **What it does not establish:** the shape of the dose-response, or
whether more instruction-bearing skills make things worse at all.


---

# v2.2 repeat sampling (2026-08-10) — the wobble was not noise, and a position confound was the reason it could not be read

Run before authoring any further scenarios, on the reasoning that repeats are
cheap and hand-authored scenarios are not: discovering a stability problem at
three times the case count costs three times as much to fix.

3 passes × 21 cells (three scenarios, L0 and L1–L3 in both arms). Cost: $0.321.

## The v2.1 curve was stable, not noisy — so the earlier diagnosis was wrong

**19 of 21 cells returned an identical score on all three passes.** Every median
reproduced the single-pass value exactly, including `s01` at L2-high scoring 0.5
three times out of three.

That reproduces the lesson `core_tool_selection_at_scale` recorded — 52 of its
64 cases identical across 5 runs — and it overturns the reading in the v2.1
section above. The non-monotone per-scenario series (`s04` at 0.8 → 1.0 → 0.8)
is **not sampling noise**. It is a stable property of those specific cells, and
averaging more passes was never going to remove it.

| | L1-high | L2-high | L3-high |
|---|---|---|---|
| s01 | 0.80 [0.8–0.8] | **0.50 [0.5–0.5]** | 0.80 [0.8–0.8] |
| s02 | 1.00 [1.0–1.0] | 1.00 [1.0–1.0] | 0.80 [0.8–0.8] |
| s04 | 0.80 [0.8–1.0] | 1.00 [1.0–1.0] | 0.80 [0.8–1.0] |

## What was actually wrong: position was confounded with level

`compose_catalog` shuffled the assembled tool list with a seed of
`(scenario, stack_level)`. A shuffle's permutation depends on the list's
**length**, so every level produced a completely different ordering. Measured on
the built cases before the fix, one bleeding skill sat at:

```
s01  subtle@9   (L1)  ->  subtle@1   (L2)  ->  subtle@14  (L3)
s04  subtle@10  (L1)  ->  subtle@6   (L2)  ->  subtle@1   (L3)
```

Position was controlled **between the arms** — which protects the arm
comparison, and was tested — and uncontrolled **across levels**, which is what
the dose-response curve is read along. So the level axis carried dose and
position together and the curve could not be attributed to either.

Being straight about the limit of this explanation: position is now known to be
a confound, but it does not obviously *cause* the observed pattern. At L2 the
subtle card sat *earlier* (index 6) for `s04` and did **not** bleed, while at L1
it sat later (index 10) and did. The direction runs the wrong way for a simple
salience story. The honest statement is that the curve was uninterpretable, not
that position explains it.

## Fixed

Ordering is now a stable sort on a per-tool key instead of a shuffle of the
assembled list, so adding a level only interleaves new skills between existing
ones and never rearranges them. Two properties now hold at once, both asserted
in `tests/test_build.py`:

- base skills at **identical absolute indices in both arms** at every level (the
  original control, preserved)
- base skills in the **same relative order at L0 and at every level above it**
  (the missing control)

Added skills key off their slot — pack index and position within the pack —
rather than their name, so the k-th skill of pack i lands in the same place in
both arms despite the two arms containing entirely different skills.

**Every number in this file predates that fix.** The mechanism findings do not
depend on ordering and stand: instruction bleed 13 occurrences against
`near_miss` 3 across 63 calls, and all three instruction strengths bleeding
(blunt 8, medium 3, **subtle 5**). The curve does depend on it and has not been
re-measured.


---

# v2.3 curve re-measured after the position fix (2026-08-10)

21 cells, single pass — justified by v2.2's finding that 19 of 21 cells return
an identical score across three passes, so repeats buy almost nothing on this
instrument. Cost: $0.107.

## The fix changed real outcomes, which settles that ordering matters

Same catalog contents at every cell; only the ordering rule changed.

| cell | before the fix | after |
|---|---|---|
| s01 L2-high | **0.50** (identical on 3/3 passes) | **1.00** |
| s04 L3-high | 0.80 | **0.667** |

The single `near_miss` ever observed in this task's calibration history — s01 at
L2-high, stable across three passes — **disappeared when the ordering was
fixed**. It was a position artifact. This pass recorded `instruction_bleed` 5,
`near_miss` **0**.

So *where* a skill sits moves outcomes about as much as *which* skills are
present. That is worth stating on its own, and it is the confound this task came
closest to publishing a curve on top of.

Instruction strengths bleeding, again all three and now evenly: blunt 2,
medium 2, **subtle 2**.

## The curve is still not monotone, and the remaining explanation is n

| level | high-arm mean | s01 | s02 | s04 | separating |
|---|---|---|---|---|---|
| L0 | 1.000 | 1.0 | 1.0 | 1.0 | — |
| L1 | 0.867 | 0.8 | 1.0 | 0.8 | 2/3 |
| L2 | 0.933 | 1.0 | 1.0 | 0.8 | 1/3 |
| L3 | 0.822 | 0.8 | 1.0 | 0.667 | 2/3 |

L2 sits **above** L1. Two explanations have now been eliminated by measurement
rather than argument:

- **sampling noise** — ruled out by v2.2: 19 of 21 cells identical across three
  passes.
- **position confounded with level** — ruled out by construction: ordering is
  now a stable sort, and the curve still wobbles.

What is left is the simplest thing: **three scenarios is too coarse to trace a
curve.** Each cell is close to binary — the agent either fires the bleeding
skill or it does not — so the level mean takes one of a handful of values and a
single scenario flipping moves it by 0.07 to 0.11. No amount of extra sampling
or extra control fixes that; it needs more scenarios.

**This is the earned justification for authoring the remaining nine.** The
curve, and with it the linear-vs-inflection call that the whole
compression-versus-routing question hangs on, cannot be answered at n=3, and now
that has been demonstrated rather than assumed.

What stands regardless of n, across four probes and 100+ calls:

- **instruction bleed is the mechanism** — it is essentially the only failure
  observed once position is controlled
- **it does not depend on how forcefully the instruction is written** — blunt,
  medium and subtle all bleed, repeatedly
- **semantic confusion at selection time is not the mechanism** — zero
  occurrences in this pass, and the one earlier occurrence was a position artifact
