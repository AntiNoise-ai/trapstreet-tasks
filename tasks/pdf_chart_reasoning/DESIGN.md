# pdf_chart_reasoning — case plan

Successor to `pdf_chart_reading`, same document, different question set. The
predecessor is kept: it works as a pipeline classifier (0.00 / 0.27 / 0.59 /
0.68 / 0.73 / 0.86 across seven arms) and its leaderboard stays valid.

## Why a new set

`pdf_chart_reading` shipped 22 cases that span **four independent directions**
(90% of variance in 4 principal components, the first at 47%). Thirteen of them
read one bar's height, varying only the figure and the panel: the measuring
pipeline passed all thirteen, the OCR pipelines failed all thirteen. Its top
score, 0.864, is held by two fixable bugs rather than by any capability limit.

## What this document actually affords

Surveyed before authoring, because it decides what can be asked.

**Chart-only — the value exists in no table:**

| Source | Encoding | Quantity |
|---|---|---|
| Figure 2 | position, discrete marks | dots per rate level |
| Figures 3.A–3.E | length | participants per bin |
| **Figures 4.D–4.E** | **position, continuous** | **8 diffusion-index series, ~75 points each, 2007–2026** |
| Bottom panels of 4.A–4.C | length | participants per uncertainty/risk category |

**Text-derivable — a rendering of the tables, NOT chart-reading material:**

| Source | Reconstructible from |
|---|---|
| Figure 1 (medians, central tendencies, ranges) | table 1 |
| Figures 4.A–4.C top panels (median line + 70% band) | table 1 medians + table 2 error ranges |
| Figure 5 | table 1 + table 2 |

Verified: the measured 4.A band widths are 3.42 / 3.62 / 4.42 percentage
points against table 2's ±1.7 / ±1.8 / ±2.2 — exactly 2x. Anything asked of
those figures is answerable without looking at them, so they belong to the
semantic questions rather than the reading ones.

## Semantic and abstention material found in the document

Seven hooks, each stated by the release itself:

1. Table 1 footnote 2 — the central tendency **excludes the three highest and
   three lowest** projections. Figure 1 draws the band; only the footnote says
   how many participants sit outside it.
2. Table 2 note — the 70% intervals are **historical errors of outside
   forecasters** (2006–2025, private and government), not the spread of the
   participants' own projections. The band is measurable; its meaning is not.
3. Figure 2 note — dots are **rounded to the nearest 1/8 percentage point**,
   which is what lets figure 2 and figure 3.E be reconciled.
4. Table 1 vs figure 3.C — the same longer-run quantity printed as `2.0` and
   drawn in the bin labelled `1.9-2.0`.
5. Table 1 footnote 4 — **longer-run core PCE projections are not collected**.
   Figure 3.D therefore has three panels where 3.A/3.B/3.C/3.E have four, and
   a question phrased exactly like an answerable one is unanswerable.
6. Figure 2 carries no identities: no participant can be named.
7. Table 1 footnote — "one of these 18 participants did not submit projections
   for 2028", so **17** is stated in prose. Looks like it needs per-participant
   data; it does not. This is the reverse item, and it is what stops a
   habitually-refusing pipeline from scoring well on the abstention group.

## The distribution

23 cases, no capability above 17% of the set, floor of three.

| | Capability | n | Source | EncQA expectation | Measurable? |
|---|---|---|---|---|---|
| A | read a length encoding | 3 | 3.A–3.E | 0.34–0.38 | yes |
| B | read a position encoding, continuous | 3 | 4.D, 4.E | 0.48–0.54 | yes, but not by a bar-reader |
| C | compute an exact derived value | 4 | 4.D/4.E deltas, 3.x cross-bin | **0.26–0.40** | yes |
| D | count discrete marks | 3 | figure 2 | ~0.5 | yes |
| E | semantic / reconciliation | 4 | hooks 1–4 | — | **no** |
| F | abstention calibration | 3 | hooks 5–7, one of them reversed | — | **no** |
| G | cross-figure integration | 3 | 2 ↔ 3.E, 4.A ↔ table 2 | — | partly |

Deliberately excluded: find-extrema, find-anomaly and relative comparison.
EncQA puts frontier models at 0.85–1.00 on all three, and the predecessor's
three questions of that shape correlated at φ = +1.00 with each other.

## Open risk

E and F are projected to correlate: on the predecessor's arms every vision
pipeline passes both and every text pipeline fails both. Hook 7 (the reversed
abstention item) is the only thing in the design that separates them, and
whether it does is a question for the first real run, not for this document.
