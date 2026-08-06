# pdf_mixed_scan — half the document is a picture

## What it measures

Whether a PDF pipeline reaches content that has no text layer.

The document is one Federal Reserve statistical release. Pages 1–5 are ordinary
digital pages. Pages 6–11 are images of pages — same tables, no extractable
text. Ten cases ask for a cell on the digital half, ten on the image half.

A solution that only reads the text layer can answer the digital cases and
**cannot answer the image cases at all**. Not "answers them badly" — the
information is not present in what it receives. Its ceiling is half marks, and
that ceiling is enforced rather than assumed: `tests/test_judge.py` asserts that
every image-half figure is absent from the document's text layer, so none can be
reached by accident.

## Why the task is built this way

Three earlier attempts at this measurement graded how well a parser preserves table
structure on ordinary digital pages — a wide indicator table, two-column
academic papers, and this same H.4.1 table in its released form. None of them
separated the pipelines: the scores clustered inside the run-to-run noise.

The lesson those three share: **disorder is recoverable, absence is not.** When
a parser garbles a row, a capable model reconstructs the answer from context and
the difference between parsers washes out. When a parser receives nothing, no
model can recover it. So the task stopped trying to grade how *well* the grid
survives and started asking whether the content arrives at all.

Detecting the split is not the hard part — a parser that classifies PDFs will
report this document as mixed. What the task measures is whether the pipeline
*acts* on that: routes the image pages to OCR or to a vision model, rather than
returning what the text layer happened to contain.

## Gold provenance

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

- **The scan is synthetic.** Pages 6–11 were rasterised from the same release,
  not photographed. Real scans add skew, noise and compression artefacts that
  make OCR harder, so OCR scores here are an upper bound. The construction is
  disclosed in [ATTRIBUTION.md](ATTRIBUTION.md) and reproducible from it.
- **One document.** The digital and image halves come from the same release, so
  the two halves are matched in style and difficulty — which is what makes the
  comparison clean, and also what stops it generalising to other document types.
- **A solution can reach the image half without OCR** by sending page images
  straight to a vision model. That is a legitimate strategy, not a loophole, and
  the task does not distinguish it from OCR — both reach the content.
- **Scores are the leaderboard's to report.** This file describes what the task
  asks and how it is scored; it deliberately does not publish the task author's
  own measurements of any tool.

## Rebuild

```bash
python3 build_cases.py
python3 -m pytest tests/ -q
```

`inputs/` and `expected/` are generated. Edit `gold.cases.json` instead.
