#!/usr/bin/env python3
"""
sanitise_pdf.py — Replace PII values in a PDF with fake-but-plausible substitutes.

Workflow:
1. Edit the SUBSTITUTIONS dict below with your real → fake mappings.
2. Run: python sanitise_pdf.py input.pdf output.pdf
3. Inspect output.pdf to verify all values were replaced.
4. If anything was missed, see "TROUBLESHOOTING" at the bottom of this file.

Approach:
  - Renders each page as a high-DPI image.
  - Runs OCR (RapidOCR, pure-Python via onnxruntime — no system deps).
  - For each substitution, finds OCR boxes containing the original value,
    paints white over them, and stamps the new text in the same position.
  - Reassembles edited images into an image-based PDF.

Why an image-based output:
  - The original PDF has a mangled text layer (DocuSign font encoding).
  - Parsers were already forced to OCR — output keeps the same failure mode.
  - This is a feature for the eval, not a bug: tests parsers under realistic conditions.

Dependencies (run once):
  pip install pymupdf rapidocr onnxruntime pillow
"""

import sys
import io
from pathlib import Path

# ============================================================
# EDIT THIS — your real values → fake replacement values
# ============================================================
# Tips:
# - Be specific. "1950" matches more than "£1,950.00" — use the most specific
#   form first if both apply. The script processes top-to-bottom.
# - For dates, include all the formats your contract uses (e.g. both
#   "05/09/2022" and "5 September 2022" if both appear).
# - If a value appears with surrounding text in the same OCR line
#   (e.g. "Rent £1,950 per calendar month"), the script keeps the
#   surrounding text and only swaps the value.
# - Strings are matched case-INsensitively. Replacements are written verbatim.

SUBSTITUTIONS = {
    # --- Tenant ---
    # "YOUR_REAL_FIRSTNAME YOUR_REAL_LASTNAME": "Alex Morgan",
    # "YOUR_REAL_LASTNAME":                     "Morgan",
    # "YOUR_REAL_FIRSTNAME":                    "Alex",

    # # --- Property address ---
    # "YOUR_REAL_FLAT_NUMBER":   "Flat 12",
    # "YOUR_REAL_STREET":        "Fictional Wharf",
    # "YOUR_REAL_POSTCODE":      "E14 9XX",

    # --- Landlord (only fill if your contract names them) ---
    # "YOUR_LANDLORD_NAME":   "Acme Holdings Ltd",

    # --- Financial ---
    # "£1,950.00": "£1,900.00",
    # "£1,950":    "£1,900",
    # "1,950.00":  "1,900.00",
    # "1,950":     "1,900",

    # Deposit (if it appears separately)
    # "£2,000": "£2,480",  # uncomment + fill in your real → fake amounts

    # --- Dates ---
    # Cover both UK formats — your contract likely uses both styles
    # "5 September 2022":  "5 September 20224",
    # "05/09/2022":        "05/09/2022",
    # "4 September 2025":  "4 September 2025",
    # "04/09/2025":        "04/09/2025",

    # --- Term length (page 3) ---
    # "36 months":   "24 months",
    # "36":          "24",   # ⚠️ broad — only enable if you check it doesn't hit unrelated "36" values

    # --- DocuSign envelope ID (top of every page) ---
    "17F88224-2E4B-46C7-94E0-094AAA8CF631": "XXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
    "17F8B224-2E4B-46C7-94E0-0544AA9CF631": "XXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",  # OCR variant
}

DPI = 200    # render resolution; 200 is good balance, 300 sharper but slower
PAD_PX = 3   # extra padding around each redaction box (pixels)

# ============================================================
# Pages to OMIT entirely from the output (1-indexed page numbers).
# Use this for pages with handwritten signatures, tenant initials,
# or other PII that's safer to drop than to redact.
# Example: AST signature pages → DROP_PAGES = [14, 15, 16]
# ============================================================
DROP_PAGES = []  # e.g. [14, 15, 16]

# ============================================================
# Auto-redact a horizontal strip to the right of these label patterns.
# When OCR finds the label on a page, the script paints white over a
# rectangle starting at the end of the label, extending right by `width_px`,
# at the same vertical position as the label. Use this to nuke
# signatures, initials, and handwritten fields that OCR can't read.
#
# Format: ("label substring", width_in_pixels). Match is case-insensitive.
# Example:
#   ("Signature:", 600)    → wipe 600px right of any "Signature:" label
#   ("Initials:", 200)     → 200px right of "Initials:"
# ============================================================
# SIGNATURE_LABELS = [
#     ("Signature:", 700),
#     ("Initials:", 250),
# ]

# ============================================================
# Manual rectangle redactions (last resort for things auto-detect misses).
# Format: { page_number_1_indexed: [(x1, y1, x2, y2), ...] }
# Coordinates are in IMAGE pixels at the script's DPI.
# To get coords: open the rendered page image (the script saves
# debug renders to /tmp/sanitise_debug/ if DEBUG_DUMP=True below) in
# Preview, use rectangle selection, read pixel coords from inspector.
# ============================================================
REDACTION_ZONES = {
    # 14: [(180, 1180, 820, 1310)],  # e.g. cover landlord signature image area
}

# ============================================================
# Auto-detect and replace EMAILS via regex (catches all without you knowing them)
# ============================================================
REDACT_EMAILS = True
EMAIL_REPLACEMENT = "tenant@example.com"   # what to write in place of any email

# ============================================================
# Auto-detect and replace UK PHONE NUMBERS via regex
# Matches: 020 XXXX XXXX, 0207 XXX XXXX, 07XXX XXXXXX, +44 XXX, etc.
# ============================================================
# REDACT_PHONES = True
# PHONE_REPLACEMENT = "020 0000 0000"

# ============================================================
# Label-anchored value replacement.
# Like SIGNATURE_LABELS, but instead of just wiping the strip,
# it WRITES a fake replacement value where the original was.
# Use this for filled-in form fields whose value isn't in SUBSTITUTIONS
# because you don't know the exact text the OCR will see.
#
# Format: ("label substring", width_px, "fake replacement to write")
# Example:
#   ("Name of Landlord", 400, "Acme Holdings Ltd")  → wipes 400px right of label,
#                                                      writes "Acme Holdings Ltd" there
#   ("A5. Name of the Landlord", 400, "Acme Holdings Ltd")
# ============================================================
LABELED_REPLACEMENTS = [
    # ("Name of Landlord", 500, "Acme Holdings Ltd"),
    # ("A5. Name of the Landlord", 500, "Acme Holdings Ltd"),
]

DEBUG_DUMP = False  # set True to write each rendered page to /tmp/sanitise_debug/

# ============================================================
# Implementation — you shouldn't need to edit below this line
# ============================================================

def main(input_path: str, output_path: str) -> None:
    import fitz  # pymupdf
    from rapidocr import RapidOCR
    from PIL import Image, ImageDraw, ImageFont

    print(f"Loading {input_path} ...")
    doc = fitz.open(input_path)
    print(f"  {len(doc)} pages")

    print("Initialising OCR (first run downloads ~15MB of models) ...")
    ocr = RapidOCR()

    # Pick a font that visually matches typical contract typesetting (Arial-style sans-serif)
    font_paths = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",             # macOS (best match for ASTs)
        "/Library/Fonts/Arial.ttf",                                  # macOS alternative location
        "/System/Library/Fonts/HelveticaNeue.ttc",                   # macOS fallback
        "/System/Library/Fonts/Helvetica.ttc",                       # macOS fallback
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",  # Linux (Arial-equivalent)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",            # Linux fallback
        "C:/Windows/Fonts/arial.ttf",                                # Windows
    ]
    system_font = next((p for p in font_paths if Path(p).exists()), None)
    if system_font:
        print(f"  Using font: {system_font}")
    else:
        print("  Warning: no system font found, falling back to default (may look ugly)")

    def fit_font_size(text: str, target_height_px: int, max_width_px: int):
        """Find the largest font size where rendered text fits within (max_width, target_height)."""
        if not system_font:
            return ImageFont.load_default()
        # Binary search for the size where the text's rendered cap-height matches target_height
        lo, hi = 6, max(7, int(target_height_px * 1.5))
        best = ImageFont.truetype(system_font, max(8, int(target_height_px * 0.85)))
        # Quick measurement: for the typical "1234567890" digit string get the bbox
        for _ in range(8):  # ~8 binary-search iterations is plenty
            mid = (lo + hi) // 2
            try:
                f = ImageFont.truetype(system_font, mid)
            except Exception:
                break
            # measure the actual rendered glyph height of an "Hg" sample (cap + descender)
            bbox = f.getbbox("Hg")
            rendered_h = bbox[3] - bbox[1]
            rendered_w = f.getlength(text) if text else 0
            if rendered_h > target_height_px or (max_width_px and rendered_w > max_width_px):
                hi = mid - 1
            else:
                best = f
                lo = mid + 1
        return best

    if DEBUG_DUMP:
        debug_dir = Path("/tmp/sanitise_debug")
        debug_dir.mkdir(exist_ok=True)
        print(f"  Debug renders → {debug_dir}")

    out_doc = fitz.open()
    total_replacements = 0
    total_signature_redactions = 0
    total_zone_redactions = 0
    pages_dropped = 0
    import re

    for page_num in range(len(doc)):
        page_no_1idx = page_num + 1

        if page_no_1idx in DROP_PAGES:
            print(f"\nPage {page_no_1idx}/{len(doc)} ... DROPPED (in DROP_PAGES)")
            pages_dropped += 1
            continue

        print(f"\nPage {page_no_1idx}/{len(doc)} ...")
        page = doc[page_num]

        # 1. Render page as high-DPI image
        pix = page.get_pixmap(dpi=DPI)
        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")

        # 2. OCR the image
        result = ocr(img)
        ocr_items = []
        if result.boxes is not None and len(result.boxes) > 0:
            ocr_items = list(zip(result.boxes, result.txts, result.scores))

        draw = ImageDraw.Draw(img)
        page_replacements = 0

        # 3a. Apply text substitutions (OCR-driven)
        for original, fake in SUBSTITUTIONS.items():
            if not original or original.startswith("YOUR_REAL_"):
                continue
            ol = original.lower()
            for bbox_corners, text, conf in ocr_items:
                if ol not in text.lower():
                    continue
                xs = [p[0] for p in bbox_corners]
                ys = [p[1] for p in bbox_corners]
                x1, y1 = min(xs) - PAD_PX, min(ys) - PAD_PX
                x2, y2 = max(xs) + PAD_PX, max(ys) + PAD_PX
                new_text = re.sub(re.escape(original), fake, text, flags=re.IGNORECASE)
                draw.rectangle([x1, y1, x2, y2], fill="white")
                box_height = max(8, int(y2 - y1) - 2 * PAD_PX)
                box_width = int(x2 - x1) - 2 * PAD_PX
                font = fit_font_size(new_text, box_height, box_width)
                # Vertically center: PIL draws from top-left of font's ascender box.
                # Use textbbox to get the actual glyph offset and align baseline-ish.
                tb = font.getbbox(new_text or "Hg")
                glyph_h = tb[3] - tb[1]
                text_y = y1 + max(0, ((y2 - y1) - glyph_h) // 2 - tb[1])
                draw.text((x1 + PAD_PX, text_y), new_text, fill="black", font=font)
                page_replacements += 1
                print(f"  ✓ text: {original!r} → {fake!r}  (in: {text!r})")

        # 3b. Auto-redact signature zones (label-anchored)
        # for label, width_px in SIGNATURE_LABELS:
        #     ll = label.lower()
        #     for bbox_corners, text, conf in ocr_items:
        #         if ll not in text.lower():
        #             continue
        #         xs = [p[0] for p in bbox_corners]
        #         ys = [p[1] for p in bbox_corners]
        #         label_x_end = max(xs)
        #         label_y_top = min(ys)
        #         label_y_bot = max(ys)
        #         label_height = label_y_bot - label_y_top
        #         # Vertical extent: signature images often extend well above and below
        #         # the label text. Use ~3× label height in each direction.
        #         strip_y_top = max(0, int(label_y_top - label_height * 1.5))
        #         strip_y_bot = min(img.height, int(label_y_bot + label_height * 3.0))
        #         strip_x1 = label_x_end + 4
        #         strip_x2 = min(img.width, label_x_end + width_px)
        #         draw.rectangle([strip_x1, strip_y_top, strip_x2, strip_y_bot], fill="white")
        #         total_signature_redactions += 1
        #         print(f"  ✓ sig-zone: {label!r} → wiped {strip_x2-strip_x1}px right of label  (label-text: {text!r})")

        # 3c. Apply manual REDACTION_ZONES (rectangle whiteboxes)
        # for (x1, y1, x2, y2) in REDACTION_ZONES.get(page_no_1idx, []):
        #     draw.rectangle([x1, y1, x2, y2], fill="white")
        #     total_zone_redactions += 1
        #     print(f"  ✓ zone: rect ({x1},{y1})-({x2},{y2})")

        # 3d. Auto-detect and replace EMAIL addresses
        if REDACT_EMAILS:
            EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
            for bbox_corners, text, conf in ocr_items:
                if not EMAIL_RE.search(text):
                    continue
                xs = [p[0] for p in bbox_corners]
                ys = [p[1] for p in bbox_corners]
                x1, y1 = min(xs) - PAD_PX, min(ys) - PAD_PX
                x2, y2 = max(xs) + PAD_PX, max(ys) + PAD_PX
                new_text = EMAIL_RE.sub(EMAIL_REPLACEMENT, text)
                draw.rectangle([x1, y1, x2, y2], fill="white")
                box_height = max(8, int(y2 - y1) - 2 * PAD_PX)
                box_width = int(x2 - x1) - 2 * PAD_PX
                font = fit_font_size(new_text, box_height, box_width)
                # Vertically center: PIL draws from top-left of font's ascender box.
                # Use textbbox to get the actual glyph offset and align baseline-ish.
                tb = font.getbbox(new_text or "Hg")
                glyph_h = tb[3] - tb[1]
                text_y = y1 + max(0, ((y2 - y1) - glyph_h) // 2 - tb[1])
                draw.text((x1 + PAD_PX, text_y), new_text, fill="black", font=font)
                page_replacements += 1
                print(f"  ✓ email: → {EMAIL_REPLACEMENT!r}  (in: {text!r})")

        # 3e. Auto-detect and replace UK phone numbers
        # if REDACT_PHONES:
        #     # UK landline: 0XX XXXX XXXX or 0XXX XXX XXXX or 0XXXX XXXXXX (with optional spaces / parens)
        #     # UK mobile: 07XXX XXXXXX or 07XXXXXXXXX
        #     # International: +44 XXX XXX XXXX
        #     PHONE_RE = re.compile(
        #         r"(?:\+44\s?|\(?0)\d[\d\s\-\(\)]{8,14}\d"
        #     )
        #     for bbox_corners, text, conf in ocr_items:
        #         m = PHONE_RE.search(text)
        #         if not m:
        #             continue
        #         # Sanity check: must contain at least 10 digits
        #         digits_only = re.sub(r"\D", "", m.group())
        #         if len(digits_only) < 10:
        #             continue
        #         xs = [p[0] for p in bbox_corners]
        #         ys = [p[1] for p in bbox_corners]
        #         x1, y1 = min(xs) - PAD_PX, min(ys) - PAD_PX
        #         x2, y2 = max(xs) + PAD_PX, max(ys) + PAD_PX
        #         new_text = PHONE_RE.sub(PHONE_REPLACEMENT, text)
        #         draw.rectangle([x1, y1, x2, y2], fill="white")
        #         box_height = max(8, int(y2 - y1) - 2 * PAD_PX)
        #         box_width = int(x2 - x1) - 2 * PAD_PX
        #         font = fit_font_size(new_text, box_height, box_width)
        #         # Vertically center: PIL draws from top-left of font's ascender box.
        #         # Use textbbox to get the actual glyph offset and align baseline-ish.
        #         tb = font.getbbox(new_text or "Hg")
        #         glyph_h = tb[3] - tb[1]
        #         text_y = y1 + max(0, ((y2 - y1) - glyph_h) // 2 - tb[1])
        #         draw.text((x1 + PAD_PX, text_y), new_text, fill="black", font=font)
        #         page_replacements += 1
        #         print(f"  ✓ phone: → {PHONE_REPLACEMENT!r}  (in: {text!r})")

        # 3f. Label-anchored value replacement (e.g. landlord name)
        for label, width_px, replacement in LABELED_REPLACEMENTS:
            ll = label.lower()
            for bbox_corners, text, conf in ocr_items:
                if ll not in text.lower():
                    continue
                xs = [p[0] for p in bbox_corners]
                ys = [p[1] for p in bbox_corners]
                label_x_end = max(xs)
                label_y_top = min(ys)
                label_y_bot = max(ys)
                label_height = label_y_bot - label_y_top
                strip_y_top = max(0, int(label_y_top - 2))
                strip_y_bot = min(img.height, int(label_y_bot + 4))
                strip_x1 = label_x_end + 4
                strip_x2 = min(img.width, label_x_end + width_px)
                draw.rectangle([strip_x1, strip_y_top, strip_x2, strip_y_bot], fill="white")
                font = fit_font_size(replacement, label_height, strip_x2 - strip_x1)
                tb = font.getbbox(replacement or "Hg")
                glyph_h = tb[3] - tb[1]
                text_y = strip_y_top + max(0, ((strip_y_bot - strip_y_top) - glyph_h) // 2 - tb[1])
                draw.text((strip_x1 + 2, text_y), replacement, fill="black", font=font)
                page_replacements += 1
                print(f"  ✓ label-replace: {label!r} → {replacement!r}  (label-text: {text!r})")

        if DEBUG_DUMP:
            img.save(debug_dir / f"page_{page_no_1idx:02d}_sanitised.png")

        # 4. Save modified image into output PDF as a new page
        img_buf = io.BytesIO()
        img.save(img_buf, format="PNG")
        img_buf.seek(0)

        page_w_pt = img.width  * 72 / DPI
        page_h_pt = img.height * 72 / DPI
        new_page = out_doc.new_page(width=page_w_pt, height=page_h_pt)
        new_page.insert_image(new_page.rect, stream=img_buf.getvalue())

        total_replacements += page_replacements

    print(f"\n=== Summary ===")
    print(f"  Text substitutions:        {total_replacements}")
    print(f"  Signature-zone redactions: {total_signature_redactions}")
    print(f"  Manual zone redactions:    {total_zone_redactions}")
    print(f"  Pages dropped:             {pages_dropped}")
    print(f"  Pages in output:           {len(doc) - pages_dropped}")
    out_doc.save(output_path)
    out_doc.close()
    doc.close()
    print(f"Wrote {output_path}")
    print()
    print("Next steps:")
    print(f"  1. Open {output_path} in Preview and check every page for missed values.")
    print(f"  2. If anything was missed, edit SUBSTITUTIONS at the top of this script and re-run.")
    print(f"  3. Common missed items: signatures (image, not OCR-able), tenant initials,")
    print(f"     phone numbers, alternative date formats. See TROUBLESHOOTING below.")


# ============================================================
# TROUBLESHOOTING
# ============================================================
# Q: A value didn't get replaced.
# A: Most likely the OCR read it slightly differently from your SUBSTITUTIONS key.
#    Re-run with this debug snippet at the top of main() to dump all OCR text:
#      for page_num in range(len(doc)):
#          pix = doc[page_num].get_pixmap(dpi=DPI)
#          img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
#          r = ocr(img)
#          if r.boxes is not None:
#              for t in r.txts: print(f"p{page_num+1}: {t!r}")
#    Then update SUBSTITUTIONS to match what OCR actually saw.
#
# Q: My signature got missed.
# A: Signatures are images, not text — OCR can't see them. Open the output PDF
#    in Preview and use Tools → Annotate → Rectangle (filled white) over each.
#
# Q: A replacement looks wrong (font too big/small or in wrong position).
# A: Font sizing is best-effort based on bbox height. Tweak PAD_PX or the
#    `font_size = max(8, int(box_height * 0.78))` factor.
#
# Q: There's a value in a TABLE CELL and the redaction crosses cell borders.
# A: Reduce PAD_PX (set to 0 or 1).

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python sanitise_pdf.py input.pdf output.pdf")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
