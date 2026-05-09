# Case 20 — Live Demo Flow

A roughly 7–8 minute live demo built around real pricing PDFs. London-flavoured for a UK audience. Designed for the "every office worker has wrestled with these documents" narrative: cloud bills, postal rates, bank fees, telco tariffs — pricing PDFs are the ground truth of how much you're going to pay, and **community AI parsers can't read them reliably.**

The demo lands because every audience member instantly grasps what's at stake: a missed row in a Royal Mail rate table is a wrong invoice. A merged cell in an AWS pricing PDF is a wrong cloud bill. A dropped footnote in a HSBC fee schedule is the £5/transaction nobody warned you about.

---

## The narrative arc

| Beat | Time | Purpose |
|------|------|---------|
| 1. Hook | 45–60s | Set the question — "can these AI repos actually read a pricing PDF?" |
| 2. Setup | 60s | Project the PDF page and the question |
| 3. The race | 2–3 min | Run 6 parsers head-to-head on the same PDF |
| 4. The reveal | 60s | Show the gold answer; score live |
| 5. The aggregate | 90s | Pre-recorded scoreboard across 4 PDFs |
| 6. The close | 45–60s | Generalise to "any AI agent that reads documents" |

**Total: ~8 minutes.**

---

## 1. The hook (45–60s)

> "Every office worker in this room has, in the last month, opened a pricing PDF and squinted at it: 'wait, is this £5.50 the price, or is the price £8.25 with the asterisk?' There are dozens of GitHub repos this year claiming AI that reads documents — for procurement, for cost optimisation, for vendor comparison. Some have venture funding. None have published a head-to-head head-to-head on the one thing every workflow depends on:
>
> *Did the parser pull out the right number from the right row?*"

This is the question the audience already cares about whether or not they realise it. Every "AI procurement assistant" is built on top of PDF-to-structured-data. If that fails, every downstream comparison or recommendation is wrong.

---

## 2. The setup (60s)

Project a single PDF page on screen. The lead PDF is **Royal Mail 2026 Business Price Guide, page 22** (Business Mail Letters rate table) — viscerally British and the failure modes are visible to anyone who's ever bought a stamp.

**Left pane — what the audience sees:**
- The actual page from the PDF, full-fidelity
- Highlight one row: "1st Class | Highly Machine-readable Unsorted | Mailmark | EBR | 25,000+"
- The price in that cell: **135.6p** per item

**Right pane — empty parser output slots, six of them.**

Walk the audience through:
- "Six AI document parsers all get this PDF as input."
- "We ask each one a simple question: *what's the 25,000+ price for highly machine-readable unsorted Mailmark first class items?*"
- "Watch what each parser actually returns."

### Recommended demo PDFs (lead with one, fall back to others)

| PDF | Why it bites in 2026 | What audience sees |
|-----|----------------------|--------------------|
| **Royal Mail Business Price Guide** ⭐ | Multi-row merged Letter cells; community parsers split them and lose row keys | Some parsers say "no such row" — when the row is plainly there. |
| **Snowflake CreditConsumptionTable** | Multi-page table boundary; community parsers shift columns and merge cells | Some parsers return `"AWS"` as the VPS price (junk). |
| **HSBC Business Price List** | Text-heavy fee descriptions with embedded numbers + cross-references | Parsers that "understand tables" choke on fee schedules formatted as paragraphs. |
| **Vodafone Business Advance** (control) | Clean single-page tables; most parsers get this right | Audience sees "ah, parsers can work — when the layout is simple." |

Lead pick: **Royal Mail**, with Snowflake as the dramatic finisher in the aggregate.

---

## 3. The race (2–3 min)

Run the same `(PDF, query)` through 6 parsers, side-by-side.

For each parser, show:
1. **Returned value** — green if right, red if wrong, yellow if missing/null, ⚠️ if hallucinated
2. **Latency**

### Recommended lineup

#### Tier A — community OSS PDF parsers (the cohort the narrative is about)

The PDF parsing repos that go viral on Twitter / GitHub. Most are scriptable directly.

- **Docling** (IBM) — biggest 2025 entry, table-aware
- **Marker** (vikp) — markdown-focused, ~13k stars
- **MinerU** — Chinese-origin, very popular for tables
- **Unstructured.io** — enterprise-flavoured OSS
- **olmOCR** (AI2) — released alongside olmOCR-Bench
- **pypdf** — baseline / "raw" extractor with no table awareness

#### Tier B — frontier vision LLMs (the comparison)

Direct API calls with the rendered PDF page as image input.

- **Claude 4.7** — strong vision/document handling
- **GPT-5** — native multi-page PDF input
- **Gemini 3 Pro** — long-context PDF input

### Practical 6-pane lineup

Top row: **Docling**, **Marker**, **MinerU** (Tier A — popular community parsers)
Bottom row: **Claude 4.7 vision**, **GPT-5 vision**, **pypdf** (Tier B frontier + raw baseline)

If a Tier A parser has install/runtime issues (Docling needs ML models, MinerU is heavy), pre-record that pane labelled "RECORDED."

---

## 4. The reveal (60s)

Flip to the gold answer. Show the canonical row + value. Score each parser live:

- ✅ Returned the correct value
- 🟡 Returned a value, but for the wrong row (e.g. picked Standard Tariff instead of Mailmark)
- ❌ Returned the wrong number (column-shift or merged-cell error)
- 🚫 Returned null / "no such row"
- ⚠️ **Hallucinated value** — returned a number that's not in the PDF anywhere

### The visceral moment

Pre-spike on Royal Mail (see [README.md](./README.md)) showed Docling lost the merged-cell row label "Highly Machine-readable Unsorted" — splitting it into "Highly" on one row and "Machine- readable Unsorted" on the next. The semantic key disappeared. So the demo query gets a 🚫 from Docling: *"no row matches 'Highly Machine-readable Unsorted'"* — even though the actual row is right there in the table.

For Snowflake (the cloud finisher), the visceral moment is even sharper: Docling returns `"AWS"` as the VPS price for AWS Asia Pacific (Seoul). A literal "this would be a real-money mistake" output.

---

## 5. The aggregate (90s)

Pre-recorded. Run the full lineup against ~10 hand-curated rows per PDF (40 rows total across the 4 PDFs). Show:

```
Parser           | Right | Wrong row | Wrong value | Null | Hallucinated | Avg latency
─────────────────┼───────┼───────────┼─────────────┼──────┼──────────────┼────────────
Claude 4.7 (vis) | 38/40 |   1/40    |    1/40     | 0/40 |    0/40      |   3.1s
GPT-5  (vision)  | 35/40 |   2/40    |    2/40     | 1/40 |    0/40      |   2.8s
Gemini 3 (vis)   | 33/40 |   3/40    |    3/40     | 1/40 |    0/40      |   2.6s
olmOCR           | 28/40 |   4/40    |    5/40     | 3/40 |    0/40      |   8.4s
Docling          | 21/40 |   8/40    |    9/40     | 2/40 |    0/40      |  12.7s
Marker           | 19/40 |   7/40    |   10/40     | 3/40 |    1/40      |  15.2s
MinerU           | 17/40 |   9/40    |   11/40     | 2/40 |    1/40      |  21.9s
Unstructured     | 14/40 |  10/40    |   12/40     | 4/40 |    0/40      |   6.3s
pypdf (raw)      |  9/40 |   3/40    |   25/40     | 3/40 |    0/40      |   0.4s
```

Numbers above are illustrative — populate from the actual pre-event run. Snowflake spike shows Docling at >50% broken on a single complex table; expect Tier A overall to land in the 40–70% range.

The mic-drop framing: **"The 'AI document parser' frameworks are dramatically worse than just feeding the PDF to Claude or GPT directly. The wrappers are layering bugs on top of capability."**

---

## 6. The close (45–60s)

> "Every workflow these AI agents claim to automate — the procurement comparison, the invoice review, the contract diff, the cost optimisation — runs through this one step: read the document, return the structured number. We measured it. The dedicated 'document AI' tools are not as good at it as the raw frontier models they're wrappers around. And the dedicated tools are catastrophically worse on the kind of tables that actually appear in real pricing documents.
>
> TrapStreet evaluates the steps, not the marketing."

Bridge to other cases (BFCL for tool-calling, FinanceBench for finance, CUAD for legal) as the same pattern across other agent categories — the building blocks fail before the orchestration even starts.

---

## Pre-event checklist

- [ ] Download all 4 PDFs to `data/` (snapshot date locked)
- [ ] Hand-curate 10 gold rows per PDF (~30–60 min/PDF, ~3 hours total). Verify against `pdftotext -raw`.
- [ ] Pull 5 candidate query rows from Royal Mail page 22 (the live race PDF); pre-test against all 6 parsers to find one with **maximum divergence** (ideally: 2 parsers right, 2 wrong-row, 2 null/hallucinated)
- [ ] Run the full lineup against 40 rows for the aggregate scoreboard
- [ ] Lock parser access; pre-record any parser that can't run in <30s on stage
- [ ] Build the 6-pane side-by-side display with colour-coded result + latency
- [ ] Build the gold-answer overlay with the canonical row + value
- [ ] Have a fallback recording of the entire demo

---

## Eval rubric for grading

For each `(parser, row)` pair:

| Outcome | Definition | Score |
|---|---|---|
| Right | Returned value matches gold (with numeric normalisation) | 1.0 |
| Wrong row | Returned a real PDF value, but from a different row than the query asked for | 0.0 (track separately) |
| Wrong value | Right row identified, but value extracted is wrong (column shift / merged cells) | 0.0 (track separately) |
| Null | Returned no value / "no such row" when the row is plainly in the PDF | 0.0 (track separately) |
| Hallucinated | Returned a value that doesn't appear anywhere in the PDF | 0.0 (track separately, **the worst failure**) |

### Headline metrics (3 separate numbers, not one average)

1. **Right-cell rate** across all 40 rows — capability ceiling
2. **Hallucinated-value rate** across all 40 rows — the "production lawsuit" metric
3. **Footnote-attribution rate** on rows whose price is modified by a footnote — the silent-failure metric

Reporting all three together is more honest than averaging them. A parser that's 80% right but hallucinates a fee 5% of the time is not 75% reliable — it's *unusable* for any procurement workflow.
