# Case 20: PDF Pricing Extraction

> Live demo flow for this case: see [DEMO.md](./DEMO.md).

**Concept:** "There are 50+ community AI repos that 'parse PDFs to structured data.' Can they actually pull the right number out of a real pricing PDF — including the asterisked footnote that adds £40K/year to the bill?"

A real-world pricing PDF (multi-tier table, footnotes, multi-page, regional matrix) goes in. A structured representation of the pricing comes out — JSON rows or markdown table. The model/parser must preserve cell values, column semantics, and footnote attribution. Failures are visible in plain text: a wrong number is a wrong invoice.

This is the foundational sub-step for every "AI procurement assistant," "AI cost optimizer," "AI vendor comparison" workflow. If extraction fails, every downstream comparison or recommendation is wrong.

---

## Why this fits TrapStreet

- **Community-repo competition, not frontier-model leaderboard** — the relevant cohort is the explosion of OSS PDF parsers (Docling, Marker, MinerU, Unstructured, olmOCR, LlamaParse, pypdf), each going viral in turn on Twitter.
- **I/O only** — PDF in, structured data out. Black box. No tracing, no introspection.
- **Universally recognisable** — every office worker has compared pricing PDFs (cloud vendors, telco rates, postal rates, bank fees). The failure mode "the parser missed the row that says 5XL is regional-only" is visceral.
- **Discrimination confirmed empirically** — pre-spike on the Snowflake CreditConsumptionTable PDF: Docling produced >50% structurally broken rows on the multi-page Table 2(a), while Claude 4.7 vision parsed the same table cleanly. The signal is large.

---

## Test PDF corpus (4 PDFs, London-flavoured)

PDFs are not redistributed in this repo — download fresh each run from the source URLs below.

| # | PDF | Pages | Profile | Source URL |
|---|-----|-------|---------|------------|
| 1 | **Royal Mail 2026 Business Price Guide** ⭐ | 35 | Multi-tier volume bands (1-249, 250-999, ..., 25,000+), pence-per-item rates, dagger/asterisk footnotes, multi-page rate tables, hierarchical row groupings (1st/2nd Class → Letter type → Format) | https://www.mymailingroom.com/wp-content/uploads/Royal-Mail-2026-Business-Price-Guide.pdf |
| 2 | **Snowflake Service Consumption Table** ⭐ | 21 | Cloud pricing across regions (incl. AWS Europe London, Azure UK South, GCP Europe West 2 London), 6-column multi-page Edition matrix (Standard/Enterprise/Business Critical/VPS), superscript footnotes, sparse cells with em-dashes | https://www.snowflake.com/legal-files/CreditConsumptionTable.pdf |
| 3 | **HSBC Business Price List** | 40 | UK bank fees, multi-column tables (Small Business / Charitable Bank), text-heavy fee descriptions with embedded numbers and percentages, cross-references ("see examples below") | https://www.business.hsbc.uk/-/media/media/uk/pdfs/regulations/business-price-list.pdf |
| 4 | **Vodafone Business Advance Price Plan Guide** (control / easy) | 24 | Multi-tier matrix tables (MBB Extra → Extra 10), Yes/No feature grids, £20-£76 monthly fees, single-page tables, "additional £5.00 per Connection per month" footnote | https://www.vodafone.co.uk/cs/groups/configfiles/documents/document/vfcon072748.pdf |

⭐ = primary discrimination PDFs. Vodafone is included as a deliberate "easy" control to show that not every PDF breaks every parser — discrimination requires the right corpus.

---

## Input / Output Schema

### Input
- `pdf_path` — local path or URL to the PDF
- `query` (optional, for narrow-scope eval) — a structured spec of the cells the model is being asked to return, e.g.:
  ```json
  {
    "table": "Table 2(a): On Demand Credit Pricing",
    "row_match": {"Cloud Provider": "AWS", "Region": "Europe (London)"},
    "columns": ["Standard", "Enterprise", "Business Critical", "VPS"]
  }
  ```

### Output (model)
- A flat list of cell values for the requested row, OR
- The full extracted table as markdown / JSON, OR
- A free-form text answer (graded on substring match against gold values).

Three eval modes — pick whichever the model under test supports.

### Output (gold)
Hand-curated per PDF. ~10 representative rows per PDF, cell-by-cell labels, transcribed from the rendered page (verified against `pdftotext -raw`). Stored as JSON:
```json
{
  "pdf": "snowflake-credit-consumption-table-2026-05-05.pdf",
  "table": "Table 2(a): On Demand Credit Pricing",
  "rows": [
    {
      "match": {"Cloud Provider": "AWS", "Region": "Europe (London)"},
      "values": {"Standard": "$2.70", "Enterprise": "$4.00", "Business Critical": "$5.40", "VPS": "$8.10"}
    }
  ]
}
```

(Curation budget: ~30–60 min per PDF for 10 representative rows.)

---

## Data Access

No PDFs in repo. Download fresh:

```bash
mkdir -p data
curl -sL -o data/royalmail-2026.pdf "https://www.mymailingroom.com/wp-content/uploads/Royal-Mail-2026-Business-Price-Guide.pdf"
curl -sL -o data/snowflake-pricing.pdf "https://www.snowflake.com/legal-files/CreditConsumptionTable.pdf"
curl -sL -o data/hsbc-business-price-list.pdf "https://www.business.hsbc.uk/-/media/media/uk/pdfs/regulations/business-price-list.pdf"
curl -sL -o data/vodafone-business-advance.pdf "https://www.vodafone.co.uk/cs/groups/configfiles/documents/document/vfcon072748.pdf"
```

PDFs change occasionally (Snowflake re-issues with new effective dates; Royal Mail updates annually). Pin a snapshot date when running formal eval. Re-curate gold rows if the PDF version changes materially.

---

## Spike findings (Docling 2.93)

Empirical pre-test on **two** corpus PDFs. Procedure: Claude 4.7 vision baseline (page-by-page read) vs Docling 2.93 with default OCR pipeline. Ground truth verified with `pdftotext -raw`.

### Snowflake CreditConsumptionTable (21 pages, 210s conversion)

**Catastrophic failure on Table 2(a) "On Demand Credit Pricing"** (page 5–6, table spans page boundary):

| Failure mode | Affected rows | Severity |
|---|---|---|
| Cloud Provider column shifted from position 1 → position 6 (e.g. "AWS" appears as last column) | ~9 of 30 rows | A "what's the VPS price for Seoul on AWS?" query returns `"AWS"` (junk) |
| Business Critical + VPS values merged into one cell ("$5.50 $8.25") | ~8 of 30 rows | A column-position parser returns the wrong number every time |
| Footnote markers attached as data values ("5XL3" instead of "5XL" + footnote ref 3) | every superscripted header | Loses footnote semantics — "may not be GA in all Regions" is silently dropped |
| Multi-page Table 1(f) fragmented into two duplicate-titled tables | 1 split table | Downstream code must know to look in both |
| Merged column headers flattened ("Credits Per Hour" duplicated 10× instead of one merged span) | every multi-column header | Cosmetic but breaks programmatic header detection |

**Concrete example** — AWS Asia Pacific (Seoul) row:

Ground truth (`pdftotext`):
```
AWS Asia Pacific (Seoul) $2.75 $4.05 $5.50 $8.25
```
Docling output:
```
| Asia Pacific (Seoul) | $2.75 |  | $4.05 | $5.50 $8.25 | AWS |
```
- "AWS" shifted to column 6 (should be column 1)
- Enterprise column blanked (should be $4.05)
- VPS price ($8.25) buried inside merged cell with $5.50

**Claude 4.7 vision (baseline)** parsed the same table cleanly. Single error: misread superscript "3" as "¹" on a footnote marker — but kept correct table structure on every page.

### Royal Mail 2026 Business Price Guide (35 pages, 88s conversion)

**Milder failure but still discriminating.** Cell *values* came through correct on every rate table I checked. The failure mode was *row hierarchy*: Royal Mail's tables use multi-row merged Letter cells (e.g. "Highly Machine-readable Unsorted" spans 2 sub-rows: Advanced/UNI and Mailmark/EBR). Docling split these merged cells across the sub-rows, breaking semantic queries.

**Concrete example** — Business Mail Letters table (page 22):

Ground truth (`pdftotext`):
```
1st Class | Standard Unsorted               | Standard Tariff | STL | 100g | 170.0p | 170.0p | 165.2p | 161.7p | 157.8p | 154.7p
         | Standard Unsorted               | Account++       | UNA | 100g | 167.0p | 167.0p | 162.3p | 158.8p | 155.0p | 152.0p
         | Highly Machine-readable Unsorted | Advanced        | UNI | 100g | 167.0p | 152.5p | 147.8p | 145.1p | 140.7p | 137.5p
         | Highly Machine-readable Unsorted | Mailmark        | EBR | 100g | 167.0p | 150.5p | 146.4p | 144.6p | 138.6p | 135.6p
```

Docling output (lines 866–869, Letter cell only):
```
| Standard Unsorted             | <- correct
| (blank)                       | <- lost row-spanning hierarchy
| Highly                        | <- split mid-cell
| Machine- readable Unsorted    | <- split mid-cell, leading "Highly" missing
```

A query "what's the 25,000+ price for 1st Class Highly Machine-readable Unsorted Mailmark items?" needs to match `Letter = "Highly Machine-readable Unsorted"`. Docling's output has no such string anywhere — only fragments. Semantic search returns nothing.

| Failure mode | Severity |
|---|---|
| Multi-row merged Letter cells split into fragments | 3 of 4 sub-rows on the demo table have wrong row labels |
| Merged column headers duplicated ("Number of items per sales order †" repeated 6× instead of one merged span) | Cosmetic but breaks programmatic header detection |
| Footnote text preserved (incl. "†" and "++" markers) | ✓ better than Snowflake on this dimension |
| All cell *values* correct | ✓ no value errors on tables I checked |

### Comparative summary

| Dimension | Snowflake | Royal Mail |
|---|---|---|
| Cell values | ~17 of 30 rows broken on Table 2(a) | All correct on tables I checked |
| Row labels | Mostly correct | 3 of 4 sub-rows lose hierarchical Letter cells |
| Column shifts | Severe ("AWS" lands in column 6) | None observed |
| Cell merges | Severe ($5.50 + $8.25 → "$5.50 $8.25") | None observed |
| Footnote markers | Attached as data values, semantics lost | Preserved correctly |
| Conversion time | 210s | 88s |
| Discrimination axis | Wrong values returned to queries | Right values, wrong row keys |

**Both are discriminating** but in different ways. A demo run that uses both PDFs lets the audience see two distinct failure modes: *value corruption* (Snowflake) and *semantic key corruption* (Royal Mail). HSBC and Vodafone fill in the picture as text-heavy and easy-control respectively.

---

## Eval Notes

- **Grading:** cell-level exact match against gold cells (10 rows per PDF, per table). Numeric normalization (e.g. `"$5.50"` == `"$5.5"` == `"5.50 USD"`) recommended.
- **Headline metrics (track separately, don't average):**
  - **Cell-value accuracy** on labelled rows
  - **Column-shift rate** — how often a value lands in the wrong column
  - **Cell-merge rate** — how often two adjacent cells get jammed into one
  - **Footnote attribution accuracy** — does the parser preserve the link from a value to its modifying footnote, or silently drop it
- **The killer metric for the demo: footnote attribution.** Every parser misses some cells. The differentiator is which parsers tell you "the £40K-changing footnote exists" vs which silently drop it.
- **Recommended community-repo lineup:** Docling, Marker, MinerU, Unstructured, pypdf, olmOCR (open-source PDF parsers). Plus frontier vision baselines: Claude 4.7, GPT-5, Gemini 3.
- **Why no academic benchmark:** olmOCR-Bench (AI2, 2025) and FinTabNet exist but neither contains pricing PDFs specifically. Hand-curating ~10 rows × 4 PDFs takes ~3 hours one-time and is reusable across all parsers — much cheaper than waiting for a benchmark to catch up.

---

## License notes

- Snowflake PDF: publicly distributed by Snowflake; we link, don't redistribute.
- Royal Mail PDF: published via mymailingroom.com (third-party host); current version of the official Royal Mail price guide. Treat as link-only.
- HSBC PDF: published on hsbc.uk public website.
- Vodafone PDF: published on vodafone.co.uk public website.

If any URL 404s, the PDF likely got reissued with a new effective date — search "{vendor} pricing PDF {current year}" and update the URL + re-curate gold.
