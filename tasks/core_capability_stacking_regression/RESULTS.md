# Results — first full matrix (2026-08-10)

84 cases: all 12 scenarios at L0 and at L1/L2/L3 in both arms, one pass each,
`claude-haiku-4-5` with no thinking. L4 was skipped — it is a separately
registered bulk probe, it has been run twice with the same answer, and neither
the curve nor the primary statistic reads it. Cost: $0.463.

Single-pass is justified rather than assumed: the v2.2 probe found 19 of 21
cells returning an identical score across three passes. Per-case metrics were
handed to the task's own `grader.py`, so what follows is the pre-registered
analysis as it will run on the leaderboard, not a re-implementation.

## Headline: the pre-registered primary test does not clear 0.05

```
PRIMARY   mean(low − high) per scenario over L1–L3, sign-flip permutation
          n = 9,  mean_diff = +0.118,  p = 0.0625        does NOT clear α = 0.05
```

Seven of nine primary scenarios run in the hypothesised direction; two run
against it (`s01` −0.222, `s09` −0.167), and that is enough to keep the exact
permutation above the threshold.

**The secondary test disagrees, and it is not the claim.**

```
secondary  high vs low at matched L3, exact sign test
           8 favouring, 0 against, 1 tied,  p = 0.0039
```

The two disagree because the primary averages the whole ladder while the
secondary reads only its top rung, where the competitor dose is highest and the
effect is cleanest. That is a coherent story and it may well be the right one —
but it is a story arrived at *after* seeing which test looked better, which is
exactly what pre-registration exists to prevent. **The reported result is
p = 0.0625.** Anyone wanting the L3-only comparison as a primary should register
it in advance and run it on a fresh set.

## Degradation surface

| | L0 | L1 | L2 | L3 |
|---|---|---|---|---|
| high overlap | 0.963 | 0.832 | 0.896 | **0.674** |
| low overlap | 0.963 | 0.941 | 0.852 | 0.963 |

By arm across everything: high **0.755**, low **0.881**, baseline 0.914.

**Curve shape: the registered rule returns `inflection@L3`** on drops of
`[+0.131, −0.064, +0.222]`. Read that with care. The middle drop is *negative* —
the high arm scores better at L2 than at L1 — so the series is still not
monotone, and a rule designed to distinguish a threshold from a straight line is
being applied to something that is neither. The rule fired as written and is
reported as written; it should not be quoted as "degradation has a threshold at
L3" without the shape of the underlying series alongside it.

## Mechanisms

| failure | count |
|---|---|
| `instruction_bleed` | 13 |
| `near_miss` | 11 |
| `incomplete` | 9 |
| `bad_arguments` | 6 |
| `unparseable` | 1 |

Instruction bleed is still the largest single mechanism, but the earlier picture
— bleed as *essentially the only* mechanism — was an artifact of three
scenarios. At twelve, semantic confusion is a real and comparable contributor.
That is a correction to what the three-scenario probes appeared to show, and it
weakens the sharper version of the claim accordingly.

Two caveats on this table. Some of the 9 `incomplete` were really surplus base
calls, which had no label at the time and fell through to the wrong one; a
follow-up fix added `over_eager` for that case. And 6 `bad_arguments` are partly
an authoring fault, not a model fault — see below.

**Instruction strength now shows a gradient**, which three scenarios could not
resolve:

| strength | times it bled |
|---|---|
| blunt | 13 |
| medium | 8 |
| subtle | 3 |

All three still bleed, so the earlier finding stands: the effect does not
require forceful wording. But it is clearly *graded* by forcefulness, which the
n=3 probes reported as flat. The honest form is "subtle guidance bleeds too,
about a quarter as often as blunt guidance", not "strength does not matter".

## Three faults this run exposed, all since fixed

The run was worth its cost as much for these as for the numbers.

1. **The dose plot was dead.** `grader.py` reads `n_competitors` off the judge's
   metrics; `judge.py` never emitted it. `by_competitor_dose` came back `{}` on
   a full matrix. A diagnostic that silently reports nothing reads as *no signal
   here*, which is worse than not having it.
2. **`s12` was unfair, and the L0 gate caught it.** Its request said "the
   register line" without ever naming which register, so the expected `sheet`
   argument was unanswerable. It scored 0.5 at L0 *and* in the low arm — failing
   where nothing has been added is the signature of an unfair case rather than a
   hard one. `s12` is an edge scenario and excluded from the primary test, so the
   headline is unaffected.
3. **`completion == 1.0` could be labelled `incomplete`.** Volunteering a surplus
   *base* skill had no category and fell through. It now has one, `over_eager`,
   kept separate from `unsolicited_addition` because base skills sit in both arms
   and cannot produce an arm difference.

All three have regression tests. None of them changes any score in the primary
tiers, so the p = 0.0625 above stands as run.

## Scope

One model, one domain, twelve scenarios, one pass per cell, no L4. `by_difficulty`
came out easy 0.914, medium 0.818, hard 0.920, edge 0.598 — the hard tier scoring
*above* the medium tier is a sign that the tier labels track intended
discrimination rather than measured difficulty, and they should not be read as
calibrated levels.
