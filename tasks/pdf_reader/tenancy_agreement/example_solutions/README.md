# Example solutions — tenancy_agreement task

Three reference agents for the tenancy_agreement task. Holds the reasoning
layer constant (Claude) so the variable is the PDF-handling layer.

| Solution | PDF handling | Setup cost | First-case latency |
|---|---|---|---|
| `claude-pdf/` | Direct: PDF → Claude (vision-LLM sees pages natively) | API key only | ~10-30s |
| `docling-claude/` | Docling extracts → markdown → Claude answers from text | RapidOCR models (~50MB) | ~60s (then cached) |
| `marker-claude/` | Marker extracts → markdown → Claude answers from text | Marker weights (~2GB) | 2-5 min on CPU (then cached) |

Each solution is its own `uv` project. Both extraction-based solutions cache
the parsed markdown (the PDF is identical across all 22 cases) so cases 2-22
just hit the API.

## Setup

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

(Optional) override the model:
```bash
export MODEL=claude-opus-4-5-20250929   # default; or sonnet-4-5 for cost
```

## Run one solution

```bash
cd example_solutions/claude-pdf
uv sync                          # one-time install
uv run tp run                    # all 22 cases
uv run tp run --fail-fast        # stop on first failure
uv run tp run -t money           # only money-tagged cases
```

Reports land in `.trap/test/latest/report.json` (and a rich table in stdout).

## Cost estimate

22 cases × 1 PDF (~1.8MB) × 3 solutions ≈ **$2–5 in API calls per full sweep**,
depending on which model you use. Sonnet is roughly 5× cheaper than Opus.

## What to compare

After running all three, look at:
- **Overall score** — which approach passes the threshold?
- **`by_category` breakdown** — does vision-LLM win on signature blocks
  (`metadata`) while Docling wins on tables (`money`)?
- **Per-case failure patterns** — where do extraction-based agents fall back
  to "I cannot determine" because the parser garbled the text layer?

The DocuSign font encoding in this PDF specifically breaks naive text
extraction. Expect a real gap between vision-based and OCR-based approaches
on this exact case.
