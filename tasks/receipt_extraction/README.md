# Receipt Extraction — Read a Receipt Photo

A trap-compatible task that tests vision-LLM receipt parsing on real-world photos. 20 cases, 4 numeric extraction question types, all gradable as exact integer matches.

## What this task tests

**Can a vision model accurately extract specific numbers from a receipt photo?**

Receipt parsing is one of the most common real-world vision-LLM workloads. Every expense tracker, B2B SaaS billing tool, food-delivery app, accounting platform, and tax prep software needs this. The cost-per-image question is critical because volume scales fast — a single fintech app can process millions of receipts per month.

The questions span four extraction patterns:

| Question type | What it asks | Difficulty | Real-world use |
|---|---|---|---|
| **total_amount** | "What's the grand total?" | easy | Expense entry, payment confirmation |
| **item_count** | "How many line items?" | medium | Inventory tracking, fraud detection |
| **subtotal_amount** | "What's the pre-tax subtotal?" | medium | Tax reporting, breakdown analysis |
| **tax_amount** | "What's the tax/service charge?" | hard | Tax compliance, expense categorization |

Each question type gets 5 cases (20 total). All answers are integers in Indonesian Rupiah (IDR — the source receipts are mostly Southeast Asian).

## Why integer-only answers

Receipt parsing in production rarely needs price points down to the cent — most consumer/B2B apps work at integer-currency-unit precision. Strict integer matching also keeps grading deterministic: no float-precision edge cases, no currency-symbol formatting wars, no thousand-separator confusion.

## Input

Per case the agent receives:
- `INPUTS["question.txt"]` — one of the 4 extraction questions, with an explicit "answer as integer, no formatting" instruction
- `INPUTS["document.jpg"]` — the receipt photo (typically 400-800 KB JPEG, varying aspect ratios — receipts are tall and narrow)

## Expected output

A single integer on stdout. Plain text or `{"answer":"..."}` JSON — both work.

The judge enforces:
- **`leading_numeric` matcher with tolerance=0** — first number in the answer must match the gold exactly
- **`no_hedge` matcher** — "I cannot read the total clearly" auto-fails

The judge auto-strips currency symbols (`$`, `£`), commas, and spaces, so `Rp 1,591,600` parses correctly. But Indonesian-style period-as-thousand-separator (e.g. `48.000` meaning 48,000) was pre-filtered OUT of the source receipts to avoid notation ambiguity.

Each case scores 1.0 / 0.0. Run passes if ≥80% correct.

## Why this is a meaningful TrapStreet task

1. **Massive real-world demand** — receipt parsing is one of the top-3 vision-LLM commercial use cases in 2026
2. **Cost-vs-accuracy is dollars and cents** — fintech apps processing millions of receipts/month genuinely care about per-image price
3. **Difficulty range built-in** — total (easy, big text) → tax (hard, small text) — a single eval reveals if a model is just doing OCR or actually finding fields
4. **Multilingual signal** — CORD is Indonesian + English, exposing OCR weakness on non-English receipts (real-world apps face this all the time)

## Honest limitations

- **All Indonesian Rupiah (IDR).** No USD/EUR/JPY/RMB receipts. A v2 should add multi-currency cases.
- **All comma notation.** We pre-filtered out the ~20% of CORD receipts using period thousand-separators. That's a real-world receipt style not represented here.
- **No date / merchant extraction.** CORD-v2's annotations don't reliably include these fields. Real-world apps need them — a v2 should add cases backed by a more complete dataset.
- **Real photos, but pre-cropped.** CORD receipts are mostly well-framed; production apps face crooked / partially-obscured / poorly-lit photos far more often.
- **Source images have merchant info blurred** — CORD intentionally anonymizes header/footer. This may slightly help/hurt models depending on whether they were grounding on visual context.

## Image source & license

All 20 receipts derive from CORD-v2 (Park et al. 2019), CC BY 4.0. See [LICENSE.md](LICENSE.md).
