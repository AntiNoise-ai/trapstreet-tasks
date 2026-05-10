# PDF Sanitisation Tool

Replaces personally identifiable values in a PDF with fake-but-plausible substitutes — for safely sharing a real signed contract as a TrapStreet test case.

## What it does

1. Renders each page of the PDF to a high-DPI image
2. OCRs the image (RapidOCR — pure Python, no system deps)
3. For each `original → fake` mapping you provide, finds matching text and:
   - Paints white over the original value's bounding box
   - Stamps the fake value in the same position
4. Reassembles the edited pages into a new image-based PDF

## Setup (one-time, ~2 min)

```bash
# Use any Python 3.10+ — the venv already in /tmp/pdf-spike/venv works,
# or create a fresh one
python3 -m venv .venv
source .venv/bin/activate
pip install pymupdf rapidocr onnxruntime pillow
```

First run downloads ~15MB of OCR models. Subsequent runs are instant.

## Usage

1. **Edit `sanitise_pdf.py`** — find the `SUBSTITUTIONS = {...}` block at the top
2. Replace each `YOUR_REAL_*` placeholder with **your actual value** as it appears in the PDF, mapped to a fake-but-plausible replacement
3. Run:
   ```bash
   python sanitise_pdf.py /path/to/your_signed_contract.pdf /path/to/sanitised_output.pdf
   ```
4. **Open the output PDF and check every page** for missed values
5. If anything was missed, edit `SUBSTITUTIONS` and re-run

## What to put in `SUBSTITUTIONS`

For a UK Assured Shorthold Tenancy Agreement, typically:

| Category | Examples |
|---|---|
| Tenant identifiers | full name, first name only, last name only |
| Property address | flat number, street name, postcode (each separately if they appear apart) |
| Landlord identifiers | name, address (if named in contract) |
| Financial values | rent (in all formats: `£1,950`, `£1,950.00`, `1,950`, `1950`) |
| Dates | both UK formats: `5 September 2022` AND `05/09/2022` |
| Term length | months / years |
| DocuSign envelope ID | top-of-page signature wrapper |

The script is case-insensitive. Order top-to-bottom by specificity (longer strings first).

## Handling signatures + page-level redactions

The script has three additional knobs (all in the same config block at the top) for things text-substitution can't reach:

### `SIGNATURE_LABELS` — auto-wipe signature/initials regions

Any handwritten signature image, initials, or filled-in handwritten field that appears to the right of a labelled position. The script finds the label via OCR, then white-out a rectangle starting at the end of the label.

```python
SIGNATURE_LABELS = [
    ("Signature:", 700),    # 700px wide, ~3× label height tall
    ("Initials:", 250),
]
```

Verified: this correctly wipes the small `DocuSigned by:` signature images that DocuSign embeds at every signing position.

### `DROP_PAGES` — remove whole pages from the output

Use this for pages where there's too much PII to safely redact piece-by-piece (typically signature pages and "Prescribed Information" pages near the end of an AST):

```python
DROP_PAGES = [14, 15, 16]   # signature page + prescribed info pages
```

Page numbers are 1-indexed.

### `REDACTION_ZONES` — manual rectangle whiteboxes

Last resort. Format: `{page_number: [(x1, y1, x2, y2), ...]}` in image pixels at the script's DPI.

To get coordinates: set `DEBUG_DUMP = True`, run once. The script saves each rendered page to `/tmp/sanitise_debug/` so you can open in Preview, use the rectangle selector, and read pixel coords from the inspector.

```python
REDACTION_ZONES = {
    14: [(180, 1180, 820, 1310)],  # cover landlord signature image area
}
```

## What the script still CANNOT remove

- **Phone numbers, email addresses** — these aren't pre-loaded in `SUBSTITUTIONS`. Add them if your contract contains them.
- **Anything OCR misread badly** — the script can only act on what OCR found. Set `DEBUG_DUMP = True` and inspect `/tmp/sanitise_debug/` to see exactly what OCR captured.
- **Form fields rendered as PDF widgets (not flattened)** — rare in DocuSign output but possible. Open in Preview → Tools → Annotate → Rectangle as a fallback.

## Safety

- All processing is **local**. Nothing is uploaded to any service.
- The `SUBSTITUTIONS` dict contains your real values — keep this file local, don't commit it.
- The output PDF only contains the fake values + the surrounding contract structure. Safe to commit/share publicly.
