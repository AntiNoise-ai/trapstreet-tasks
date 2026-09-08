# Sourcing a document for a chart-reading task

A chart-reading task needs a document whose figures encode values that exist
nowhere else. That sentence is easy to write and hard to satisfy, because the
institutions that publish the best charts are the same institutions that publish
the data behind them.

This is what the admission checks rejected, and what survived. Everything below
was measured on the documents named, not inferred. Four of the six checks are
about the document; the two that decided the outcome are about the figure.

## The checks

1. **Are the values only in the figure?** Not just absent from the document's
   tables — absent from everything the publisher releases.
2. **Is there a text alternative?** `/Alt` or `/ActualText` in the PDF, or an
   accessible HTML version on the publisher's site.
3. **Is redistribution permitted?** Including for each figure separately.
4. **Is the underlying dataset published somewhere else?** A registry, a data
   portal, a supplement.
5. **Can the figure reproduce a count it prints?** If not, it has no resolution
   to spare and cannot produce gold.
6. **Does the figure print its own values?** Then it is a table, and a question
   about it measures OCR.

A document passes only if 1–4 pass. **A figure passes only if all six pass for
that figure**, and 5 and 6 are where most figures die.

## Why US federal agency publications fail

Section 508 requires federal agencies to provide accessible alternatives for
their charts. **The accessible alternative to a chart is the data.**

The Federal Reserve's Summary of Economic Projections was the source for
`pdf_chart_reasoning`, on the belief that its diffusion-index figures carried
values printed in no table. The PDF does. The release does not: the accessible
version publishes every series quarter by quarter.

```
Figure 4.D. Diffusion indexes of participants' uncertainty assessments
  SEP              Change in real GDP   Unemployment   PCE inflation   Core PCE
  October 2007     0.76                 0.53           0.35            0.06
  January 2008     0.88                 0.76           0.29            0.29
  ...
```

Thirteen figures, all covered, every release. The Financial Stability Report is
published the same way. This is a legal obligation rather than an oversight, so
it holds for the whole class: **an agency's own publications cannot source this
kind of task.**

The exception is a document an agency *hosts* without authoring. FDA advisory
committee briefing materials are written by the sponsor and posted under a
publication obligation; FDA attaches only a notice that the file "may not be
fully accessible." Measured across three such documents: `/Alt` and
`/ActualText` occurrences, zero.

## Why open data and registries fail

Two more families rejected, both for check 4:

- **Vaccine immunogenicity.** A Moderna influenza package looked ideal until its
  trial was checked: `NCT05827978` has results posted on ClinicalTrials.gov,
  which is where the GMTs and seroconversion rates live. Results reporting is
  mandatory within a year of primary completion, so **a completed trial is an
  exposed trial**.
- **Public-health surveillance.** A US influenza surveillance deck carried 23
  measurable figures; CDC FluView Interactive publishes the same data weekly,
  with an R package to fetch it.

## What survives

Sponsor briefing packages about trials that are still running. That is a narrow
class, and the narrowness is the point: everything wider has a data release
attached to it.

Two further filters within it, both of which rejected real candidates:

- **Scanned pages are a different task.** One 96-page briefing document had 46
  pages with no text layer at all. Questions about it would measure OCR and page
  layout, which is what the retired `pdf_mixed_scan` measured and why it was
  retired.
- **Third-party reprints are not ours to redistribute.** A sponsor slide deck
  carried 19 figure pages citing journal figures — "Copyright 2025 Massachusetts
  Medical Society. Reprinted with permission." The permission was granted to the
  sponsor.

## Per figure, not per document

A document that passes as a whole still contains figures that do not. Both
failures below were found only by descending to the figure:

- **The prose states the curve.** One package's text reads "The 1-year, 2-year,
  and 3-year survival rates were 75.3%, 61.0%, and 47.2%" — three points of a
  Kaplan-Meier figure, printed. Its median is stated too. Landmark and median
  questions about that figure need no figure.
- **One package, several trials.** A cell-therapy briefing plotted three trials.
  Two of them are complete with results posted; one is not. Only the third
  trial's figures are usable, in a document that passes every check at the
  document level.

## Two checks that only fire at the figure, and decide everything

**Resolution.** A figure can pass every exposure and licence check, have
separable colours, and still be unable to produce a number. Require the
extraction to reproduce a count the figure itself prints:

| figure | density | extracted | printed |
|---|---|---|---|
| waterfall, 94 bars in 922 px | 9.8 px/bar | 56/45 and 54/38, two methods | N=47 |
| ECDF, 51 steps in 410 px | 8.0 px/step | 48 | n=51 |
| Kaplan-Meier, 3900 px wide | ample | reproduces | at-risk row |

Neither failure is visible by looking at the figure, and neither is a colour
problem. A figure that cannot reproduce its own printed count cannot produce
gold.

**A figure that prints its own values is a table.** A vector forest plot listed
`n/N` and `ORR (95% CI)` for all twenty-four subgroups in a column beside the
markers. Its geometry duplicates its labels, so a question about it measures
OCR. `pdf_chart_reasoning`'s README had already found this shape in its own
document — "figure 1 is a rendering of table 1 ... anything asked of it is
answerable without looking at it" — and it recurs wherever a chart is drawn to
be read precisely, which is most of the time in a regulatory filing.

Together these two are why a document that passes at the document level can
still yield **one** usable figure. Count usable figures before authoring, not
documents.

## Screen the presentation deck, not only the briefing document

The two are posted for the same meeting and carry the same analyses, and the
sponsor's slides are often **vector where the briefing document is raster**. That
one difference decides check 5: a waterfall that could not reproduce its own
N=47 as a 922-pixel image extracts exactly from paths in the deck — 45 blue bars
and 45 red, matched, heights to two decimals, at a different data cutoff.

The best figure found in this search was in a deck and not in the document it
accompanies: a per-lesion waterfall of about two hundred vector bars, grouped by
patient with the patient identifiers on the axis, no per-bar values printed, and
a summary in the footer — "66.0% (35/53) had a reduction of >30%" — that serves
as the invariant an extraction has to reproduce.

Vector is not a problem to be avoided, either. A vector chart is exactly
measurable, and the reason `pdf_chart_reasoning` rasterised its document was to
stop a *solution* measuring it that way. That step belongs at the end, after the
gold is extracted, and the machinery for it already exists.

## Measuring gold: the metric that works

Gold has to be measured, never eyeballed — `pdf_chart_reasoning`'s extractor
records the author reading one panel as 1/4/5/4/1 where the geometry said
2/5/6/4/1. When the source figures are raster, the measurement is over pixels,
and the question is whether a curve survives as a separable block of colour.

**Distinct colour count is the wrong test.** Measured on one document:

| figure | distinct colours | saturated core pixels | separable? |
|---|---|---|---|
| spider plot | 5,567 | 19,659 | **yes** |
| Kaplan-Meier | 786 | 0 | **no** — its curves are greys |

The colour count says the opposite of the truth on both. The test that works is
**saturated core pixels**: how many pixels sit in frequent, saturated colours.
A synthetic render puts a curve in one exact RGB; anti-aliasing only blurs its
edge. A figure drawn in greys and pastels has no core at all, whatever its
colour count.

Two properties worth wanting in the source, both satisfied by a high-resolution
synthetic render:

- **Already raster.** Then "the value exists only as pixels" needs no
  rasterisation step, and there is no vector path for a geometry reader to
  measure exactly and be correct by construction.
- **Invariants printed on the figure.** Kaplan-Meier plots draw their at-risk
  counts and annotate their medians. Those are not exposure — they are inside
  the image, published nowhere — and they are what a measurement is validated
  against, the way `extract_gold.py` validated bar heights against the
  participant count the release stated in words.

## What this costs

Screening a document takes minutes and is worth automating; the two scripts that
run these checks live with the task that uses them. Choosing the document is
cheap. Writing the extractor for its particular figures is not, and it does not
transfer between documents: different renderers, different palettes, different
resolutions. Budget the sourcing at hours and the gold pipeline at days.
