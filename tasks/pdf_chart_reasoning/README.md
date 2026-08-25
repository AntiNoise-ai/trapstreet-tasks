# pdf_chart_reasoning — seven things, three cases each

## What it measures

Whether a document pipeline can do more than one thing with a chart. Twenty-three
questions about one Federal Reserve *Summary of Economic Projections*, spread
across seven capabilities with no capability holding more than three or four:

| Capability | n | What it needs |
|---|---|---|
| read a length encoding | 3 | a bar's height against a gridline drawn every two participants |
| read a position encoding | 3 | a continuous index read off an axis, at one quarterly observation |
| compute an exact derived value | 4 | two readings and an operation, boundaries included |
| count discrete marks | 3 | a dense row of identical dots |
| semantic reconciliation | 4 | what a band *means*, which of two correct numbers was asked for |
| abstention calibration | 3 | two questions the document cannot answer, one that only looks that way |
| cross-figure integration | 3 | the same quantity in two chart types, with rounded bin edges between them |

## Why it is built this way

Its predecessor, `pdf_chart_reading`, is still published and still useful: it
sorts pipelines into text extraction, OCR, native vision, rendered vision,
agent loops and geometric measurement, and the spread is clean. But it spends
thirteen of twenty-two cases reading one bar's height, and across seven arms its
items span **four independent directions**, with the first holding 47% of the
variance. A pipeline that measures a bar correctly measures all thirteen; one
that cannot, fails all thirteen. Its top score, 0.864, is held by two fixable
bugs rather than by any limit on what the arm can do.

This set is the same document asked differently. Three constraints shaped it:

- **No capability over a third of the set**, floor of three, so that no single
  ability can carry the score and no ability is measured by a coin flip.
- **Nothing whose task type is already saturated.** EncQA puts frontier models
  at 0.85–1.00 on finding extrema, finding anomalies and relative comparison,
  and the predecessor's three questions of that shape correlated at φ = +1.00
  with each other. Its hardest cells are retrieving an exact value (0.34–0.54)
  and computing an exact derived one (0.26–0.40), and those are what this set
  is built around.
- **Seven cases that measurement cannot answer.** The semantic and abstention
  groups turn on what the release says about its own figures, not on what the
  figures show.

## The document decides what can be asked

Surveyed before authoring, and it changed the plan. Only part of this release's
thirteen figure pages carries information that is not also printed:

- **Chart-only:** figure 2's dots, figures 3.A–3.E's distributions, and figures
  4.D–4.E's eight diffusion-index series of 75 quarterly points each.
- **A rendering of the tables:** figure 1 (table 1's medians, central tendencies
  and ranges), figures 4.A–4.C's top panels and figure 5 (table 1's medians ±
  table 2's error ranges). Measured, figure 4.A's GDP band is 3.42 / 3.62 / 4.42
  percentage points wide against table 2's ±1.7 / ±1.8 / ±2.2 — exactly twice.

Anything asked of the second group is answerable without looking at it, so those
figures appear here only in the semantic questions, where the point is that the
band is measurable and its meaning is not.

## Gold provenance

Bars and dots: `extract_gold.py`, from the pre-rasterisation vector paths, with
every panel checked against the participant count the release states in words.

Diffusion indexes: `extract_series.py`. Dates come from structure rather than
from fitting the year labels, which one stray label off the axis was enough to
skew by two years — 75 markers plus one double-width gap is 76 quarterly slots,
19.00 years exactly, which puts the first slot at the SEP's first release and
the gap at the March 2020 meeting the figure's own note says is omitted. Values
are checked against the definition in that note: the index is (higher − lower) ÷
participants, so every value is a multiple of about 1/18.

Dates before 2012 carry a `~` in `series_gold.json`. The SEP has accompanied the
March, June, September and December meetings for most of its life, but the early
ones did not -- the fourth was published with the January 2009 minutes -- so
counting quarterly back from the anchor names the month correctly only in the
settled era. No case is authored against one of those points, and a test keeps
it that way.

Semantic and abstention answers are stated by the release: table 1's footnotes
and table 2's note.

## Scoring

Deterministic, no LLM judge. Each question ends with a contract:

> End your reply with a line of the form `ANSWER: <value>`.

and the judge grades that line. A reply without one scores zero, and an empty
reply is reported as empty rather than as a formatting problem.

Counts are graded exactly. The diffusion index is continuous and cannot be, so
it carries a tolerance of **±0.025**, which is derived rather than chosen: the
index moves in steps of about 1/18 = 0.056, so half a step keeps two adjacent
legal values from both passing, and 0.025 of an index unit is 5.6 pixels at the
shipped 200 dpi — readable by a careful reader, not by a glance. Cases were
selected so that the measurement behind the gold is itself within a tenth of a
participant of a legal value.

## Known limitations

- **The hardest chart tasks are not available here.** EncQA's lowest cells are
  encodings that need a legend — area at 0.14–0.20, quantitative colour at 0.16.
  This release has no pie, bubble or heat map; every figure is length or
  position encoded and readable against an axis.
- **Measurement still answers sixteen of the twenty-three.** The ceiling this
  set imposes on a purely geometric pipeline is a design property, not a wall:
  the seven it cannot answer are the semantic and abstention groups.
- **The predecessor is not retired.** Two tasks, two different questions.

## Rebuild

```bash
python3 build_document.py sep_original.pdf sep_charts.pdf
python3 extract_gold.py sep_original.pdf gold_geometry.json
python3 extract_series.py sep_original.pdf series_gold.json
python3 author_cases.py gold.cases.json
python3 build_cases.py
python3 -m pytest tests/ -q
```
