# pdf_tables — reading values out of wide, repetitive tables

## ⚠️ Licence status

The document is a free public download from the manufacturer, but it carries
**no redistribution licence**, and none could be found for its programme
operator (EPD Hub). The comparable operator, IBU, grants own-use only and
expressly not sublicensable. Shipping the PDF in a public task repo is
therefore not clearly permitted.

It is published anyway, at the project owner's explicit direction. See
[ATTRIBUTION.md](ATTRIBUTION.md) for exactly what was and was not established,
and for how the rights holder can have it removed.

## What it measures

Whether a PDF parser preserves **row/column association** in wide tables.

The document carries six tables of 18 data columns each, spread over three
pages, and three of them report overlapping quantities under different
standards. Every case asks for a value at a row × column intersection, or for
something answerable only by scanning a whole row or column, or by telling two
near-identical tables apart. A parser that linearises the page — reading cells
in visual order without reconstructing the grid — produces text where the right
number is present but attached to the wrong row or column. The model on top
cannot recover from that, and the failure is silent: the answer looks like a
plausible figure from the same table.

This is the complement of `pdf_reader_v2`, which measures whether a parser can
read the text layer *at all*. There the failure was encoding; here the text
extracts perfectly and the **structure** is what gets lost.

## The twenty cases

| Stratum | n | What makes it hard |
|---|---|---|
| easy | 3 | First data column, neighbours orders of magnitude away |
| medium | 4 | Mid-row, with a same-row neighbour close enough to look plausible |
| hard | 5 | Past the eleven-column ND run, or the last of eighteen columns |
| expert | 8 | Two tables reporting the same quantity under different standards; scanning a whole column; combining rows; applying a footnote |

**Difficulty is assigned from structural properties, checkable by eye on the
rendered page** — how many columns separate the cell from its row label,
whether an adjacent cell is numerically close enough that a drift looks
plausible (recorded per case in `_decoy`), whether a same-named row exists in
another table, and whether the answer needs a scan or a combination rather than
a point lookup. It is **not** taken from the text-preservation probes; see
"A difficulty model that did not work" below.

The sharpest stratum is `cross_table`. Page 11 reports environmental impacts
under EN 15804+A2 / EF 3.1; page 13 reports the same product's impacts under
EN 15804+A1 / CML. Same quantities, same modules, different characterisation
standard, and the figures land within a few percent of each other:

| | page 11 (EF 3.1) | page 13 (CML) | apart |
|---|---|---|---|
| GWP, A1-A3 | 2.94E+02 | 3.19E+02 | 8% |
| GWP, module D | -2.47E+01 | -2.45E+01 | **0.8%** |
| ADP-fossil, A1 | 4.66E+03 | 4.29E+03 | 8% |

Answering from the wrong table produces a figure that survives any forgiving
tolerance, so `case_15` tightens its relative tolerance to 0.2%. `case_02` and
`case_16` deliberately ask for the same quantity from each table, so a solution
that conflates them cannot get both right.

## Gold provenance — the constraint that makes this task valid

**Every figure in `gold.cases.json` was read by eye off the rendered page.**
None came from a parser's table extraction.

This is load-bearing, not fastidiousness. The candidate question sites were
located with PyMuPDF's `find_tables`. Sourcing the gold the same way would make
PyMuPDF-based solutions correct *by construction* — they would score near 100%
because the answer key is their own output, and nothing on the leaderboard
would reveal it. Each case records the `_page` its gold was read from. If a
case is ever revised, re-render that page and read it again; do not re-extract.

## Scoring

Deterministic, no LLM judge. A case scores 1.0 only if every matcher passes.

Two matchers were added on top of `pdf_reader_v2`'s:

- **`sci_value`** — the inherited `NUMBER_RE` splits `2.25E+01` into
  `[2.25, 1]`, so the value 22.5 is never produced and every case here would
  be unscoreable. It also handles the 1E-15 … 1E+03 range with a *relative*
  tolerance, prefers E-notation tokens so that unit strings carrying digits
  (`kg CO2e`, `kBq U235e`) are not read as answers, and accepts the comma
  decimal separator the document's own footnote uses.
- **`regex_forbidden`** — an anti-shotgun primitive, implemented and tested
  but **used by no case**, deliberately. It was written for the two "which
  single column/row has this property" cases, and the first parser run showed
  why that does not work: pdf-inspector answered "only B6 carries numeric
  values; B1, B2, B3, B4, B5 and B7 are marked ND" — completely correct — and
  scored 0, because a forbidden pattern cannot tell naming-to-exclude from
  naming-to-claim. Both cases now ask for the *value* in the column instead.
  A shotgun over labels cannot produce the right figure; a thorough answer is
  no longer punished for being thorough.

## What has been measured

| | result |
|---|---|
| Closed-book probe (no document attached) | **0 / 20** |
| No-parser control (pages as images, Opus) | **19 / 20**, $5.26 |
| Unit tests | 79 pass |

The control's one miss is `case_13`: it answered the C3 cell where C2 was
asked. The gold was re-verified afterwards by rendering that row at 4x — C2 is
1.44E-04 and the question is unambiguous, so the case is marked a ceiling case.
A parser solution that misses it should not be assumed to have failed because
of its parser.

## Known limitations

- **One document.** Twenty cases over three pages of one EPD. This measures
  performance on this class of wide, repetitive indicator table; it does not
  support a general claim about a parser. Two other corpora were tried and
  rejected — see below.
- **No parser solution has been run against this case set yet.** The previous
  twelve-case version had exactly two end-to-end data points, and any statement
  ranking one parser against another rested on a proxy that was later shown not
  to predict outcomes.
- **`sci_value` commits to the last figure in the answer** unless a case sets
  `mode: any`. A model that states its answer and then continues into further
  arithmetic is scored on where it ended up. `case_18` needed `mode: any`
  precisely because its natural answer ends on a sum rather than on either
  operand — the unit test caught that before any run.

## A difficulty model that did not work

Two probes were built to grade cell difficulty from parser text. Neither
predicted the one outcome then measured, and they failed in opposite
directions:

- **Loose** — "the value appears within ~220 characters of its row label."
  A whole 19-column row fits inside that window, so it cannot tell whether the
  *column* is still identifiable. It called 10 of 11 tested cells recoverable.
- **Strict** — "the value appears at the right ordinal position in the row's
  token sequence." This assumes flat token output; a parser emitting a real
  markdown table lets the model read column headers instead of counting. It
  said no parser could locate four cells that pdf-inspector then answered
  correctly.

The current case set uses neither. Both are kept in the scratch tooling only as
a cross-check: a cell both call hard is probably hard, and a cell both call easy
is probably easy, but neither number belongs in a claim about parser quality.

## Rebuild

```bash
python3 build_cases.py                    # regenerate inputs/ and expected/
python3 -m pytest tests/ -q               # 61 tests
python3 ../../scripts/validate_task.py .  # structural self-consistency
```

`inputs/` and `expected/` are generated. Edit `gold.cases.json` instead.


## A redesign that was attempted and abandoned

Recorded so nobody repeats it.

The plan was to source difficulty from pdf-inspector's own issue tracker rather
than from a probe — one case per reported failure mode, which would ground case
selection in something real. Four modes looked testable through this task's
shape:

| Issue | Reported failure | Outcome |
|---|---|---|
| #219 | two-column pages emitted in raster order | **could not reproduce** |
| #251 | `.markdown` silently drops content `extract_text()` keeps | real, but already covered by `pdf_reader_v2`'s vanilla-vs-deshift pair |
| #229 | sparse table rows collapse into one row | never verified |
| #246 | CJK CIDFontType2 corruption | needs a document carrying that specific defect; none sourced |

**#219 did not reproduce on seven CC-BY two-column arXiv papers.** Two apparent
hits were both defects in the detector, not the parser: the arXiv stamp runs
vertically down the left margin, so its y-coordinate says nothing about reading
order; and a results table spanning the full page width was split at the page
midline and its right half read as an intruding second column. With both
corrected, pdf-inspector got reading order right on every page tested.

Two corpora were also rejected on content, not licence:

- **DP-Bench** (upstage/dp-bench, MIT — licence acceptable under
  `tasks/imported/README.md`): every document is a single page with few tables.
  It is a layout-annotation corpus, not a multi-page document corpus.
- **CC-BY arXiv papers**: 6–15 tables each, but 0–2 extractable
  (row-label → value) associations, against this EPD's 748. ML results tables
  do not have the row-label/value shape the questions need.

The lesson worth keeping: **verify the failure is present in the parser's output
before authoring any case.** Both rejections cost minutes; skipping that step on
the EPD cost twelve hand-authored cases whose selection rationale later turned
out to be unsupported.
