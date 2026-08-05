# Results — first full matrix (2026-08-05)

All numbers are medians across m repeated runs, with [min–max] across runs.
Every pass was re-scored with the final judge via `rescore_runs.py`, so no
scoring change sits inside the comparison. Reproduce with `analyze_runs.py`.

## Headline

**The circulating claim — that naively stacking tools causes a 30–50% accuracy
regression — does not reproduce with native tool-calling, at any model size we
tested, up to 300 tools and 61k tokens.**

The nearest thing to a reproduction we found — **one exploratory comparison,
not a pre-registered test** — is that flattening the catalog into the prompt as
text, instead of passing it through the tool-calling API, costs a small
open-weight model ~25 points at the largest catalog size. See the multiplicity
caveat below before treating that as established.

## Variants

| Variant | m | Overall | Notes |
|---|---|---|---|
| claude-opus-5 (high effort) | gate | **16/16** | adversarial N=6 and N=300 |
| claude-haiku-4-5, native tools | 3 | **1.000** [1.000–1.000] | 192/192 cases, every cell 100% |
| llama-3.1-8b, native tools | 5 | 0.812 [0.797–0.859] | |
| llama-3.1-8b, flat-text catalog | 5 | 0.812 [0.766–0.844] | same overall, different shape |
| qwen-2.5-7b | 5 | **no data** | upstream provider outage, see below |

## The strongest signal we found (exploratory)

Same model, same 64 cases, same catalogs — only the presentation differs:

| adversarial | native tools | flat-text | families favouring native |
|---|---|---|---|
| N=6 | 0.850 | 0.900 | 2/8 vs 1/8 |
| N=60 | 0.650 | 0.775 | 0/8 vs 3/8 |
| **N=300** | **1.000** | **0.750** | **5/8 vs 0/8** |

At N=300, five of eight families are better under native tool-calling and none
is better under flat text. One-sided exact sign test on 5 concordant discordant
pairs: **p ≈ 0.031**.

Flat text costs nothing at 6 or 60 tools — it is slightly *better* at both.
The penalty appears only at 300. This is a presentation × catalog-size
interaction, not a catalog-size effect: the identical 300-tool catalog handed
to the identical model through the tool-calling API scores **100%**.

Note what this is not: it is not "more tools degrade agents". It is
"flattening a large catalog into prompt text degrades a small model, while the
API path handling the same catalog does not".

### Multiplicity caveat — read before quoting the p-value

The sign test conditions on discordant pairs, so n = 5, not 8, and one-sided
p = 0.5⁵ ≈ 0.031. That number should not be read as a confirmatory result:

- The same comparison was run at **three** N levels and the smallest p is
  reported. A Bonferroni threshold across those three is ≈0.017, which 0.031
  does not clear.
- The same eight families also generated the catalog-size, ambiguity and
  position analyses — roughly a dozen family-level tests in total on one
  dataset.

This is therefore **one exploratory comparison selected post hoc from many**,
not a pre-registered test that survived. It is the most promising lead this
matrix produced and it is reported as a lead. Establishing it would require
pre-registering this specific comparison and testing it on a fresh set of
intent families.

## What did not reproduce

**Catalog size, native tool-calling.** llama-3.1-8b scores 87.5 at adversarial
N=6 and **100.0** at adversarial N=300 — the gap runs the wrong way for the
hypothesis. 0 of 8 families degrade from N=6 to N=300. haiku and opus are at
ceiling throughout.

**Ambiguity.** Marginal gaps look real (llama native: clean 91.7 vs adversarial
75.0) but collapse at matched N, which is the only comparison that controls
catalog size: 0.0pt at N=6, 0.0pt at N=300 for llama native. The pre-registered
rule is not met.

**Position / lost-in-the-middle.** No variant supports it. Where a position
spread exists at all (llama native: mid 100.0, early 75.0, late 62.5) the
middle is the **best** position, not the worst — the opposite of what U-shaped
attention predicts. haiku is tied at 100 across all three. The U-shaped
attention explanation for tool-selection failure gets no support here.

## Statistical caveat (see README amendment)

The pre-registered "non-overlapping ranges across m runs" criterion is weaker
than it looks: **52 of 64 cases returned an identical score on all 5 runs** —
these models are near-deterministic under `tool_choice=required`, so repeated
runs measure little and ranges come out artificially tight.

The honest unit of uncertainty is the family (n=8), so every claim above is
also reported as a family-level paired sign test. Under that test:

- native → flat-text at N=300: 5/8, **p ≈ 0.031** (clears 0.05)
- flat-text N=6 → N=300: 3/8, p = 0.125 (directional only)
- llama native position mid vs late: 3/8, p = 0.125 (directional only)

Only the presentation result reaches 0.05, and only before correcting for the
number of comparisons run (see above). The position result **passes the
registered rule but fails the better test**, and is reported as directional.

Everything in this document is one dataset of 8 intent families. The
appropriate summary is: the strong version of the circulating claim is clearly
absent, and one specific mechanism is worth a properly pre-registered
follow-up.

## qwen-2.5-7b: no data, not a zero

All 5 passes returned 0.000 with all 64 cases marked `solution_error`. This was
an upstream provider fault, not the model:

```
502 Upstream error from Phala: Expecting ':' delimiter: line 3 column 7
```

The model never answered a single case, including at N=6. Reported as missing
data. The grader's `solution_error` quarantine is what kept this out of the
accuracy figures — otherwise it would have published as "the small model scored
0%", a textbook catalog-size false positive.

## Judge corrections made during the matrix

Three scoring artifacts were found and fixed; **all three reduce measured
degradation**, i.e. they cut against the headline rather than toward it:

1. A clock-time expectation (`09:00`) rejected a full ISO-8601 timestamp
   carrying the same hour and minute. The query says "this morning" and gives
   no date, so any date is invented and the schema explicitly permits
   timestamps.
2. A stringified list (`"['Priya', 'Marco']"`) was rejected. Flat-text
   solutions serialise collections as reprs — rejecting that penalises the
   presentation mode, which would have inflated precisely the effect reported
   above.
3. Path-like arguments now match on final component, so `folder/Finance`
   satisfies `Finance` while `planning` still does not.

Wrong values still fail: `09:30` never satisfies `09:00`, a wrong attendee set
fails, a wrong folder fails, and date-only fields stay strict.
