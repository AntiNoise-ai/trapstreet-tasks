#!/usr/bin/env python3
"""Turn the AST's drawn-on black boxes into real redactions, and cover the
PII the boxes missed.

Two distinct problems in the source PDF, both fixed here:

1. **Drawn, not redacted.** 15 black rectangles are painted over names,
   addresses, emails, phone numbers and signatures. Painting hides pixels; the
   text underneath is still in the content stream and comes straight out of
   `extract_text()`. (The document's fonts are a DocuSign subset shifted by
   -29 codepoints, so naive extraction looks like mojibake and this reads as
   safe. It is not: the shift auto-detects.)

2. **Two pages were missed entirely.** Page 11 clause 5.4c and page 15 each
   carried personal data with no box over it — visible on screen, not just in
   the text layer.

This script removes the underlying text with `apply_redactions()` and repaints
a black rectangle so the document looks the same as before.

Business contact details (letting agent, TDS, OVO, banks) are deliberately NOT
redacted — they aren't personal data, and TDS is the gold answer to case_11.

Usage:
    python3 tools/apply_redactions.py in.pdf out.pdf
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import fitz

SHIFT = 29  # DocuSign font-subset codepoint offset; see module docstring


def deshift(s: str) -> str:
    return "".join(
        chr(ord(c) + SHIFT) if 0x01 <= ord(c) <= 0x60 and ord(c) not in (9, 10, 13) else c
        for c in s
    )


# Trigger tokens live in a LOCAL, GITIGNORED file — one lowercase token per
# line, blank lines and #-comments ignored. They are the operator's real
# personal data (names, street names, postcodes with spacing removed), so
# committing them here would republish in plaintext exactly what this script
# strips from the PDF. Same rule the sibling tool documents:
# ../../pdf_reader/tools/README.md — "keep this file local, don't commit it".
#
# Tokens are compared against each LINE's deshifted text with every
# non-alphanumeric character stripped. Flattening this hard is deliberate: PDF
# word-splitting fragments emails across word boxes and splits postcodes in
# two, so any pattern depending on the original spacing or punctuation misses
# them. Compare flattened forms and the fragmentation stops mattering.
TOKENS_FILE = Path(__file__).parent / "pii_tokens.local.txt"


def load_triggers() -> list[str]:
    if not TOKENS_FILE.exists():
        raise SystemExit(
            f"missing {TOKENS_FILE.name}\n"
            f"Create it next to this script — one lowercase token per line, "
            f"non-alphanumerics stripped (a postcode 'AB1 2CD' becomes 'ab12cd'). "
            f"It is gitignored; do not commit it."
        )
    return [
        re.sub(r"[^a-z0-9]", "", ln.strip().lower())
        for ln in TOKENS_FILE.read_text().splitlines()
        if ln.strip() and not ln.startswith("#")
    ]


MOBILE_RE = re.compile(r"\b07\d{3}\s?\d{6}\b")

# Business contact details — not personal data, and some are load-bearing:
# "The Dispute Service" / TDS is the gold answer to case_11.
KEEP = re.compile(r"TDS|Tenancy Deposit|Dispute Service|Dexters|ovoenergy|Barclays|Lloyds|Santander", re.I)


def black_boxes(page: fitz.Page) -> list[fitz.Rect]:
    """The rectangles someone already painted over PII."""
    out = []
    for d in page.get_drawings():
        f = d.get("fill")
        if not f or not (f[0] < 0.15 and f[1] < 0.15 and f[2] < 0.15):
            continue
        r = d["rect"]
        if r.width >= 20 and r.height >= 5:
            out.append(r)
    return out


def uncovered_pii(page: fitz.Page, boxes: list[fitz.Rect], triggers: list[str]) -> list[fitz.Rect]:
    """Bounding boxes of lines carrying PII that no black box already covers.

    Redaction is WHOLE-LINE, not word-level. Word-level was tried and leaked
    twice: an email's domain fragment stops matching any email pattern once
    the local part has been redacted away, and a postcode's two halves are
    separate word boxes. Partial redaction of a line is exactly where residue
    survives, so the unit is the line.

    The cost is one cosmetic over-redaction: on page 11, clause 5.4c's line
    loses its trailing prose along with the address it contained. No case asks
    about clause 5.4c, so this is accepted rather than special-cased — a
    narrower rule here is exactly the kind of cleverness that let the two
    leaks through.
    """
    lines: dict[tuple[int, int], list] = {}
    for w in page.get_text("words"):  # (x0,y0,x1,y1,word,block,line,word_no)
        lines.setdefault((w[5], w[6]), []).append(w)

    hits: list[fitz.Rect] = []
    for group in lines.values():
        group.sort(key=lambda w: w[7])
        text = " ".join(deshift(w[4]) for w in group)
        if KEEP.search(text):
            continue
        flat = re.sub(r"[^a-z0-9]", "", text.lower())
        if not (any(t in flat for t in triggers) or MOBILE_RE.search(text)):
            continue

        r = fitz.Rect(
            min(w[0] for w in group), min(w[1] for w in group),
            max(w[2] for w in group), max(w[3] for w in group),
        )
        if not any((r & b).get_area() / max(r.get_area(), 0.01) > 0.9
                   for b in boxes if b.intersects(r)):
            hits.append(r)
    return hits


def main(src: str, dst: str) -> None:
    triggers = load_triggers()
    doc = fitz.open(src)
    n_existing = n_new = 0

    for page in doc:
        boxes = black_boxes(page)
        new = uncovered_pii(page, boxes, triggers)
        n_existing += len(boxes)
        n_new += len(new)

        for r in boxes:
            # Real removal, then repaint so the page looks unchanged.
            page.add_redact_annot(r, fill=(0, 0, 0))
        for r in new:
            page.add_redact_annot(r + (-1, -1, 1, 1), fill=(0, 0, 0))

        if boxes or new:
            # images=KEEP: signature images sit under some boxes and are
            # already visually covered; text is what leaks.
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
            if new:
                print(f"  page {page.number + 1}: {len(boxes)} existing, {len(new)} newly covered")

    doc.save(dst, garbage=4, deflate=True, clean=True)
    doc.close()
    print(f"redacted {n_existing} existing boxes + {n_new} uncovered spans -> {dst}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: apply_redactions.py in.pdf out.pdf")
    main(sys.argv[1], sys.argv[2])
