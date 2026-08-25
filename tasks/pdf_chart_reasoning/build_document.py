"""Rasterise the figure pages of the June 2026 SEP.

The charts are vector paths. A parser cannot read a data point out of them, but
`page.get_drawings()` can measure every bar and dot exactly -- which would make
a geometry-reading solution correct by construction. Rasterising the figure
pages removes the paths, so the value survives only as pixels.

Pages 1-2 and 16-17 (the release note, table 1, table 2 and the notes) keep
their text layer, exactly as published.

    python3 build_document.py sep_original.pdf sep_charts.pdf
"""
import io
import sys

import pymupdf
from PIL import Image

FIGURE_PAGES = range(3, 16)          # 1-based: figures 1, 2, 3.A-3.E, 4.A-4.E, 5
DPI = 200
QUALITY = 80


def main(src_path: str, out_path: str) -> None:
    src = pymupdf.open(src_path)
    out = pymupdf.open()
    for i, page in enumerate(src, start=1):
        if i not in FIGURE_PAGES:
            out.insert_pdf(src, from_page=i - 1, to_page=i - 1)
            continue
        pix = page.get_pixmap(dpi=DPI)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=QUALITY, optimize=True)
        p = out.new_page(width=page.rect.width, height=page.rect.height)
        p.insert_image(p.rect, stream=buf.getvalue())
    out.save(out_path, deflate=True)

    check = pymupdf.open(out_path)
    for i in FIGURE_PAGES:
        p = check[i - 1]
        assert not p.get_text().strip(), f"page {i} still carries text"
        assert not p.get_drawings(), f"page {i} still carries vector paths"
    print(f"{out_path}: {len(check)} pages, {len(FIGURE_PAGES)} rasterised, verified clean")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
