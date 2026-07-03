# core_pdf_ocr — Transcribe Text from a Scanned PDF

Part of TrapStreet's **Foundation 11** — basic mechanics every AI agent needs.

A trap-compatible task that tests whether a vision model can correctly **OCR text from a scanned-looking PDF**. 20 cases across 4 progressive difficulty tiers.

## What this task tests

**Given a single-page PDF that looks like a book scan, can the model accurately read it?**

Every AI agent that ingests documents — invoice processors, legal-doc reviewers, receipt extractors, research assistants, accessibility tools — needs robust OCR. The question isn't "does OCR work in the lab", it's "does it stay accurate as scan quality degrades."

The 4 difficulty tiers expose exactly the OCR degradation curve a model has:

| Difficulty | Cases | What's applied | Real-world analog |
|---|---|---|---|
| `clean` | 5 | No artifacts | Born-digital PDF or pristine scan |
| `mild` | 5 | Light sepia, faint noise, 0.8° rotation, JPEG q85 | Phone photo of a flyer |
| `moderate` | 5 | Paper texture, blur, 2.5° rotation, JPEG q70 | Older office scanner |
| `heavy` | 5 | Dirt spots, heavy noise, 5° rotation, JPEG q50 | Decades-old archive scan |

## Case structure

5 distinctive book passages (Alice in Wonderland, Tom Sawyer, Huck Finn, Dracula, Pride and Prejudice) × 4 difficulty tiers = 20 cases. The SAME passage at 4 difficulty levels lets you see exactly where each model breaks down.

## Input

Per case:
- `INPUTS["document.pdf"]` — single-page PDF (~50-200 KB) with the rendered text
- `INPUTS["question.txt"]` — "Read document.pdf and transcribe the first sentence verbatim"

## Expected output

The first sentence of the page, transcribed verbatim.

The judge enforces:
- **`keywords_all` matcher** — requires 5 distinctive content words from the first sentence to appear in the answer (skips stopwords). This is lenient enough to accept minor punctuation/quotation variations but catches actual misreadings.
- **`no_hedge` matcher** — "I cannot read the page clearly" auto-fails.

Each case scores 1.0 / 0.0. Run passes if ≥80% pass.

## Why "keyword match" instead of exact sentence match

OCR-to-text is fundamentally lossy at the character level — `"`/`"` smart-vs-straight quotes, em-dash vs hyphen, capitalization, etc. Models often produce semantically correct transcriptions with cosmetically different output. The keyword matcher catches REAL misreadings (wrong words) without false-flagging trivial punctuation differences.

Strict matchers would punish accurate models for harmless variations. Keyword matching tests "did you get the content right" which is what an agent actually cares about.

## Why hard at the top of the difficulty curve

- `heavy` cases have ~5° rotation + dirt spots — vision models that depend on horizontal text alignment trip up here
- JPEG q50 compression smears fine-text edges — character-by-character readers degrade fast
- Dirt spots can look like punctuation or letters to a model that doesn't filter them out

A model that scores 100% on `clean` but 0% on `heavy` is honest signal: it has clean-document OCR but no robustness.

## Cost

Per-case input is a single small PDF (~100 KB). Vision tokens dominate cost: ~500-800 input tokens per PDF page. Full 20-case run: **$0.05-0.30** depending on model.

## Honest limitations

- **Synthetic, not real scans.** Real OCR challenges include uneven aging, ink bleed, page warping, handwritten annotations, and varied fonts. This task simulates the rotation / noise / compression dimensions but not the others. A v2 should add real scans from Wikisource / HathiTrust / open archives.
- **English-only.** Real OCR pipelines face multi-script documents, RTL languages, mixed scripts.
- **Single-page only.** Real document OCR needs to handle page-flow, headers/footers, footnotes. This is the atomic test.
- **5 passages from 19th-century novels.** Vocabulary is Victorian English. Modern business documents have different distribution.
- **Background is consistent off-white.** Real scans have varied paper colors, watermarks, archive stamps.

## Data source & license

Text content from Project Gutenberg (public domain). PDFs synthetically generated. See [LICENSE.md](LICENSE.md).
