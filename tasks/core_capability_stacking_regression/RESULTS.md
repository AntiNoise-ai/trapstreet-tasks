# Results

Two runs of the 84-case matrix (all 12 scenarios at L0 and at L1/L2/L3 in both
arms, one pass each). L4 is skipped in both — it is a separately registered bulk
probe, it has been run twice with the same answer, and neither the curve nor the
primary statistic reads it.

| run | model | thinking | cost | primary p |
|---|---|---|---|---|
| 1 | `claude-haiku-4-5` | none (the model has no adaptive mode) | $0.46 | 0.0625 |
| 2 | `claude-sonnet-5` | adaptive, on by default | $1.43 | **0.0078** |

Each model ran at its shipped default rather than at a forced-common setting.
Forcing thinking off on Sonnet to match haiku would have traded a real
capability difference for a scoring artifact: with thinking disabled it can leak
`<thinking>` tags into the visible response, and this judge parses a JSON block
out of that text — a leak scores `unparseable`, which says nothing about whether
the model picked the right skills.

Single-pass is justified rather than assumed: the v2.2 probe found 19 of 21
cells returning an identical score across three passes. Per-case metrics were
handed to the task's own `grader.py` in both runs, so what follows is the
pre-registered analysis as it will run on the leaderboard, not a
re-implementation.

> **The two runs did not see an identical corpus.** Run 1 exposed the s12
> unfairness (below), and the fix rewrote nine prompts in the same commit that
> recorded the result. So s12 is not comparable across the runs; s01–s11 are
> scored identically. s12 is an edge scenario and was never in the primary test,
> so the headline statistic is unaffected. Every cross-run number below is
> computed over s01–s11 with s12 dropped from *both* sides. `by_failure_reason`
> is not comparable in either direction — run 1's `incomplete` bucket absorbed
> cases that would now score `over_eager`, and the stored manifest holds
> post-judge metrics, so it cannot be relabelled after the fact.

---

## Run 2 — `claude-sonnet-5`: the primary test clears

```
PRIMARY   mean(low − high) per scenario over L1–L3, sign-flip permutation
          n = 9,  mean_diff = +0.146,  p = 0.0078        clears α = 0.05

secondary high vs low at matched L3, exact sign test
          7 favouring, 0 against, 2 tied,  p = 0.0078
```

Eight of nine primary scenarios run in the hypothesised direction. The two tests
agree here, which they did not in run 1.

**The one scenario running against it is a parse failure, and it makes the
reported p conservative rather than generous.** `s03` comes out at −0.111, and
its L1 *low-overlap* case is the run's single `unparseable` (score 0.0). A zero
in the low arm drags the low mean down, which is what flips the sign. Left in as
scored — chasing it would only move p further below the threshold, and that is
exactly the direction in which a result should not be optimised after the fact.

### The first monotone curve

| | L0 | L1 | L2 | L3 |
|---|---|---|---|---|
| high overlap | 0.978 | 0.844 | 0.770 | **0.703** |
| low overlap | 0.978 | 0.889 | 0.941 | 0.926 |

Drops of `[0.133, 0.074, 0.068]`. Run 1's series was non-monotone and its curve
verdict came with a warning attached; this one decreases at every step, so the
registered shape rule is being applied to something it was designed for.

**The registered rule returns `linear`, and the underlying shape is
front-loaded**: the first pack of overlapping skills costs 0.133, and each
further pack costs about half that. Damage decelerates. That is the opposite of
a threshold — there is no level at which the arm falls apart, and the cheapest
intervention is whatever prevents the *first* overlapping skill from being
installed, not a routing layer that engages once a catalog is large.

The low arm stays flat across the same ladder (0.978 → 0.926), so the decline is
attributable to overlap rather than to catalog size. That is the control the
design exists to provide, and it holds.

### Dose

`by_competitor_dose` is live for the first time (run 1's was silently empty —
see faults, below). Broadly monotone: 1 competitor → 1.00, 2–5 → ~0.82,
6 → 0.76, 7 → 0.66, 11 → 0.44.

---

## What the second model changed about the finding

### The task discriminates on mechanism, not on overall score

| over s01–s11 | haiku-4.5 | sonnet-5 |
|---|---|---|
| score | 0.862 | 0.856 |
| L0 baseline | 0.952 | 0.964 |
| **high-overlap arm** | 0.779 | **0.755** |
| **low-overlap arm** | 0.915 | **0.921** |
| arm gap | 0.137 | **0.166** |

The two models score within 0.006 of each other overall — a leaderboard column
would call this a tie. They are not tied. Sonnet is better at the baseline and
better in the low arm, and *worse* in the high arm. **The more capable model is
not more robust to skill overlap; by the measure this task exists to take, it is
somewhat less so.**

This is the argument for reporting the arm split rather than the headline score.
A single aggregate hides the entire effect.

### Subtle instruction bleed disappears; blunt bleed does not

| strength | haiku-4.5 | sonnet-5 |
|---|---|---|
| blunt | 13 | 14 |
| medium | 8 | 8 |
| subtle | 3 | **0** |

Run 1 supported "standing guidance of any tone is enough." That does not survive
the second model. Sonnet ignores the softly-worded cards entirely while still
following the blunt ones at the same rate as haiku. The honest form is now:
**forcefulness is what carries instruction bleed, and resistance to the soft end
arrives before resistance to the hard end.**

### Curve shape is model-dependent

Run 1 returned `inflection@L3` on a non-monotone series; run 2 returns `linear`
on a monotone one. Only the second is a curve the rule was built to classify.
One clean observation is not a settled answer about shape, but the direction of
the evidence is that the degradation is smooth and front-loaded rather than
threshold-shaped.

---

## Run 1 — `claude-haiku-4-5`

```
PRIMARY   n = 9,  mean_diff = +0.118,  p = 0.0625         does NOT clear α = 0.05
secondary 8 favouring, 0 against, 1 tied,  p = 0.0039
```

Seven of nine primary scenarios ran in the hypothesised direction; two ran
against it (`s01` −0.222, `s09` −0.167), and that was enough to keep the exact
permutation above the threshold. The two tests disagreed because the primary
averages the whole ladder while the secondary reads only its top rung.
**The reported result for run 1 is p = 0.0625.** Anyone wanting the L3-only
comparison as a primary should register it in advance and run it on a fresh set.

Curve `[+0.131, −0.064, +0.222]` — non-monotone, so the `inflection@L3` verdict
should not be quoted without the series beside it.

Mechanisms: `instruction_bleed` 13, `near_miss` 11, `incomplete` 9,
`bad_arguments` 6, `unparseable` 1. Instruction bleed was the largest single
mechanism, but the earlier picture — bleed as *essentially the only* mechanism —
was an artifact of three scenarios. At twelve, semantic confusion is a real and
comparable contributor.

### Three faults run 1 exposed, all since fixed

1. **The dose plot was dead.** `grader.py` reads `n_competitors` off the judge's
   metrics; `judge.py` never emitted it. `by_competitor_dose` came back `{}` on a
   full matrix. A diagnostic that silently reports nothing reads as *no signal
   here*, which is worse than not having it. Live in run 2.
2. **`s12` was unfair, and the L0 gate caught it.** Its request said "the
   register line" without ever naming which register, so the expected `sheet`
   argument was unanswerable. It scored 0.5 at L0 *and* in the low arm — failing
   where nothing has been added is the signature of an unfair case rather than a
   hard one. Now "the vendor register line"; scores 1.0 across the board in run 2.
3. **`completion == 1.0` could be labelled `incomplete`.** Volunteering a surplus
   *base* skill had no category and fell through. It now has one, `over_eager`,
   kept separate from `unsolicited_addition` because base skills sit in both arms
   and cannot produce an arm difference.

All three have regression tests. None changes any score in run 1's primary
tiers, so its p = 0.0625 stands as run.

---

## Scope

Two models, one domain, twelve scenarios, one pass per cell, no L4. Run 2's
`by_difficulty` came out easy 0.895, medium 0.852, hard 0.874, edge 0.871 — the
tiers are within 0.04 of each other, so the labels track intended discrimination
rather than measured difficulty and should not be read as calibrated levels.

Two gaps worth naming rather than defending. **One domain** — office automation
only; nothing here shows the effect generalises to other tool ecosystems. And
**the arm gap is bounded by scenario length**: one surplus call against two
required calls is a 0.2 hit by construction, so the absolute size of the effect
is a property of the case design, not a portable number. The *sign*, the
*curve shape*, and the *between-model comparison* are what travel.

The raw model outputs were not retained in either run, only per-case metrics.
That is why run 2's single `unparseable` cannot be diagnosed without re-running
the case — worth fixing in the harness before a third run.
