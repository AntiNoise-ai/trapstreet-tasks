# Attribution — pdf_mixed_scan

- **Document:** *Factors Affecting Reserve Balances of Depository Institutions
  and Condition Statement of Federal Reserve Banks* (statistical release H.4.1)
- **Issuer:** Board of Governors of the Federal Reserve System
- **Release:** July 30, 2026
- **Obtained from:** <https://www.federalreserve.gov/releases/h41/current/h41.pdf>
- **Licence:** a work of the United States federal government, not subject to
  copyright in the United States. Freely redistributable, no permission needed,
  no notice required. Attribution is given here as good practice, not as a
  licence condition.

## What was changed, and why it is disclosed

`H41_mixed.pdf` is the released PDF with **pages 6–11 replaced by 200 dpi
greyscale JPEG images of themselves**. Those pages therefore carry no text
layer. Pages 1–5 are byte-for-byte the original.

Nothing else is altered. No content is added, removed, reordered or retouched,
and every figure in `gold.cases.json` is the Federal Reserve's own, read off the
rendered page.

The construction is the instrument. Earlier versions of this task tried to
measure table-structure quality on ordinary digital PDFs and could not separate
the tools: four parsers scored 17–20/20 on one document and agreed on five of
six cells of this very H.4.1 table. Disorder is recoverable — a capable model
reconstructs the answer from a garbled row. Absence is not. Half the cases are
now on pages no text-layer parser can reach at all, which turns a marginal
difference into a binary one and caps text-only solutions at 10/20 by
construction.

Because the split is synthetic, it is stated here, in the README, and in
`gold.cases.json`'s `_construction` field, so no reader mistakes the document
for an as-published scan.

## Reproducing the document

```python
import fitz, io
from PIL import Image

src = fitz.open("h41.pdf")          # the file at the URL above
out = fitz.open()
for i, page in enumerate(src, 1):
    if i < 6:
        out.insert_pdf(src, from_page=i - 1, to_page=i - 1)
    else:
        pix = page.get_pixmap(dpi=200)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples).convert("L")
        buf = io.BytesIO(); img.save(buf, format="JPEG", quality=72, optimize=True)
        p = out.new_page(width=page.rect.width, height=page.rect.height)
        p.insert_image(p.rect, stream=buf.getvalue())
out.save("H41_mixed.pdf", deflate=True)
```

The Federal Reserve reissues H.4.1 weekly and `current/` moves, so the exact
figures here belong to the July 30, 2026 release. `_source.release` in
`gold.cases.json` records which one.
