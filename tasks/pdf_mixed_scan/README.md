# pdf_mixed_scan — half the document is a picture

## What it measures

Whether a PDF pipeline can answer analyst questions about a document half of
which has no text layer.

The document is one Federal Reserve H.4.1 release. Pages 1–5 are ordinary
digital pages; pages 6–11 are images of pages, same tables, no extractable
text. The twenty questions are the kind someone actually asks of this release —
they name no cell, often no table, and answering one means working out which
figures matter and what to do with them:

> How much more collateral could the Federal Reserve pledge against its notes
> without acquiring any additional securities?

> Reverse repurchase agreements fell over the year. What share of that decline
> came from the "Others" sub-line?

Seven need only the digital pages, seven only the image pages, and six need
both. Most answers are figures the document never prints — a ratio, a
difference, a base reconstructed by undoing a change column — so reproducing
the document does not produce them.

## Why it is built this way

Four earlier attempts measured how well a parser preserves table structure on
ordinary digital pages. None separated the pipelines, and the reason was always
the same: **disorder is recoverable, absence is not.** A capable model
reconstructs an answer from a garbled row, so parser differences wash out. What
a model cannot do is recover content that never arrived.

A fifth attempt made half the document unreachable but asked only single-cell
lookups. That separated text-layer pipelines from OCR ones, and nothing within
either group — everything that could read the page scored full marks. Questions
that require locating the right figures and combining them restore a gradient
there too, because a compound answer needs several cells right at once.

## Gold provenance## Gold provenance

Every figure was read by eye off the page rendered at 2.4×, never from a
parser's extraction. Each case records `_page` and `_layer` (`text` or `scan`)
so any figure can be re-checked against the right rendering.

The candidate cells were *located* with PyMuPDF's table finder on the original
release; taking the values from there too would make PyMuPDF-based solutions
correct by construction.

## Scoring

Deterministic, no LLM judge. A case scores 1.0 only if every matcher passes.

Every case is scored by one figure. The rules are stated here rather than left
as hidden gotchas:

- **How you write the number does not matter.** `748,255`, `748255`,
  `$748,255 million` and `7.48255E+05` are all accepted. A comma is read as a
  thousands separator when the digits are grouped in threes and as a decimal
  point otherwise, so `3,07` still means 3.07.
- **The sign does matter, and every convention is accepted.** `-179,225`,
  `−179,225` (U+2212), an en dash, `(179,225)` in accounting style, and a sign
  detached from its digits as this table prints it all resolve to the same
  negative figure. Omitting a negative sign fails.
- **Listing figures does not help.** An answer containing more than eight
  numbers is rejected outright as a shotgun, and within that the figure you are
  answering with must be among the last three you write. Citing a source
  ("748,255, table 6 page 9") or contrasting two cells ("Richmond is -40,560
  but Atlanta is 154") stays inside the window; reproducing a table row does
  not.
- **Hedging fails.** "I cannot determine this from the document" scores zero
  rather than counting as an abstention.

## Known limitations

- **The scan is synthetic.** Pages 6–11 were rasterised from the same release
  at 200 dpi, not photographed. Real scans add skew, noise and compression
  artefacts, so OCR results here are an upper bound. Disclosed with
  reproduction code in [ATTRIBUTION.md](ATTRIBUTION.md).
- **One document.** The two halves come from the same release, which is what
  makes the comparison clean and also what stops it generalising.
- **A pipeline may reach the image half with a vision model rather than OCR.**
  That is a legitimate strategy and the task does not distinguish them.
- **Scores belong to the leaderboard.** This file describes what is asked and
  how it is scored; it does not publish the author's own measurements.

## A judge that had to be corrected four times

Recorded because the pattern is more useful than the fixes. Every version
rejected *correct* answers, and every one was caught by running the task rather
than by reasoning about it:

| Rule | What it rejected |
|---|---|
| cap of 8 figures | an answer that quoted the row it read the value from — a date contributes two figures of its own |
| target must be among the last 3 | three answers that led with the figure in bold and explained underneath |
| target must be first or among the last 3 | the commonest analytical shape there is: preamble, answer, explanation |
| comma always a decimal point | `748,255` parsed as 748.255, failing sixteen of twenty |

Position was the wrong signal throughout. What protects these cases instead is
a property of the questions — most ask for a figure the document does not
print — plus a name requirement on the few whose answer *is* printed, and a cap
that only fires on a whole-page dump. `tests/fixtures/` holds sixty answers
from three real pipelines so the next revision cannot quietly undo this.

## Rebuild## Rebuild

```bash
python3 build_cases.py
python3 -m pytest tests/ -q
```

`inputs/` and `expected/` are generated. Edit `gold.cases.json` instead.
