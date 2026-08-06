# pdf_mixed_scan — half the document is a picture

## What it measures

Whether a PDF pipeline reaches content that has no text layer.

The document is one Federal Reserve statistical release. Pages 1–5 are ordinary
digital pages. Pages 6–11 are images of pages — same tables, no extractable
text. Ten cases ask for a cell on the digital half, ten on the image half.

A solution that only reads the text layer answers the first ten and **cannot
answer any of the second ten**. Not "answers them badly" — the information is
not present in what it receives. Its ceiling is 10/20, and that ceiling is
verified mechanically: `tests/test_judge.py` asserts every image-half figure is
absent from the document's text layer, so none can be reached by accident.

## Why the task is built this way

Three earlier attempts measured table-structure quality on ordinary digital
PDFs, and none of them separated the tools:

| Attempt | Result |
|---|---|
| Wide indicator tables in an EPD, 20 cases | pdf-inspector 17/20, docling 18/20, docling-OCR 19/20, MinerU 20/20 |
| Two-column arXiv papers, reading order | the reported failure did not reproduce on seven papers |
| This same H.4.1 table, digital, 6 hand-picked cells | four parsers agreed on five of six |

The lesson those three share: **disorder is recoverable, absence is not.** When
a parser garbles a row, a capable model reconstructs the answer from context and
the difference between parsers washes out. When a parser receives nothing, no
model can recover it. So the task stopped trying to grade how *well* the grid
survives and started asking whether the content arrives at all.

That also aligns the task with what the tools actually claim. `pdf-inspector`'s
headline feature is classifying scanned versus text-based PDFs to route OCR;
issues #227 and #252 on its tracker are users reporting that classification
going wrong. On this document it classifies correctly —
`pdf_type='mixed', confidence=0.69` — so what the task measures is whether a
solution *acts* on that classification.

## Measured

Each parser's output was fed to the same model (`claude-sonnet-5`) and judged
against the same gold.

| Pipeline | Score | Digital half | Image half | Parse time |
|---|---|---|---|---|
| MinerU | **20/20** | 10/10 | 10/10 | 996 s |
| docling (full-page OCR) | **19/20** | 9/10 | 10/10 | 929 s |
| pdf-inspector | 10/20 | 10/10 | **0/10** | ~1 s |
| PyMuPDF | 10/20 | 10/10 | **0/10** | ~0.2 s |
| pypdf | 10/20 | 10/10 | **0/10** | ~1 s |
| pdfplumber | 10/20 | 10/10 | **0/10** | ~2 s |

The spread is 0.50 to 1.00, and it comes entirely from the image half. Every
text-layer parser fails exactly cases 11–20 and no others; on the digital half
all six pipelines are indistinguishable.

That last point is a correction. An earlier run of this table showed PyMuPDF at
9/20 and pdfplumber at 7/20, and this README claimed the digital half separated
them. It did not — those four lost cases were the judge mis-parsing correct
answers (a thousands separator read as a decimal point, and a Unicode minus
sign the pattern did not recognise). Both are fixed and regression-tested. The
digital half discriminates nothing, which is consistent with the three earlier
attempts.

The trade-off is the interesting part: the two pipelines that reach the image
half are three orders of magnitude slower, and buy nothing on the digital half.

## Gold provenance

Every figure was read by eye off the page rendered at 2.4×, never from a
parser's extraction. Each case records `_page` and `_layer` (`text` or `scan`)
so any figure can be re-checked against the right rendering.

The candidate cells were *located* with PyMuPDF's table finder on the original
release; taking the values from there too would make PyMuPDF-based solutions
correct by construction.

## Scoring

Deterministic, no LLM judge. A case scores 1.0 only if every matcher passes.

`sci_value` had to learn both comma conventions this repo's documents use: a
thousands separator in `748,255` and a decimal point in `3,07`. Treating every
comma as a decimal point — which it did originally, because the EPD in
`../pdf_tables` writes its conversion factor as `3,07` — parses `748,255` as
748.255 and silently fails sixteen of these twenty cases. The unit tests caught
it before any solution ran. **`../pdf_tables/judge.py` still carries the
original version**; its own document is written entirely in scientific notation
so nothing there hits the bug today, but a model that answers `4,660` instead of
`4.66E+03` would be marked wrong.

## Known limitations

- **The scan is synthetic.** Pages 6–11 were rasterised from the same release,
  not photographed. Real scans add skew, noise and compression artefacts that
  make OCR harder, so OCR scores here are an upper bound. The construction is
  disclosed in [ATTRIBUTION.md](ATTRIBUTION.md) and reproducible from it.
- **One document.** The digital and image halves come from the same release, so
  the two halves are matched in style and difficulty — which is what makes the
  comparison clean, and also what stops it generalising to other document types.
- **A solution can pass the image half without OCR** by sending page images
  straight to a vision model. That is a legitimate strategy, not a loophole, and
  the task does not distinguish it from OCR — both reach the content.

## Rebuild

```bash
python3 build_cases.py
python3 -m pytest tests/ -q
```

`inputs/` and `expected/` are generated. Edit `gold.cases.json` instead.
