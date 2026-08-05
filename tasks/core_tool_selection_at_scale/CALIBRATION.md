# Calibration record

Run **before** the full matrix, on 2026-08-04. Raw per-case results are in
`calibration/`. Reproduce with `calibrate.py` (see commands below).

The point of this file is that "hard but fair" should be a measurement, not a
claim. Predecessor task `core_tool_selection_under_load` returned 1.0 on all
270 scores it ever produced; the failure there was difficulty calibration that
nobody checked before running the matrix. So this instrument gets checked
first, and the check is written down whether or not it flatters the design.

## 1. Fairness gate — is every case solvable?

Rule, registered in `README.md`: the strongest available model at high effort
must score 1.0 on every adversarial case at N=6. A case it misses with six
tools in front of it is *unfair*, not hard, and gets rewritten.

Run at both ends of the N range, because the two readings mean different
things — a case solved at N=6 but missed at N=300 is a *finding*, not an
authoring bug, and only running both separates them.

| Cells | Model | Result |
|---|---|---|
| `adv_n6_mid` (8 cases, ~1.9k tok each) | claude-opus-5, effort=high | **8/8 — 1.000** |
| `adv_n300_mid` (8 cases, ~61k tok each) | claude-opus-5, effort=high | **8/8 — 1.000** |

Gate passes: no case was rewritten. Every family's discrimination is
demonstrably available in the catalog, at both catalog sizes.

The N=300 result is also a finding in its own right — a frontier model at high
effort selecting correctly from a 300-tool, 61k-token catalog with five
plausible competitors present, on all eight families.

## 2. Difficulty band — do the families discriminate at all?

Rule: a model that can actually fail should land roughly in **40–90%** on
adversarial N=6. At ceiling the families are not discriminating and no quantity
of filler will create a discrimination that isn't there — which is exactly what
made the predecessor flat. At floor they are probably unfair.

| Cells | Model | Result |
|---|---|---|
| `adv_n6_mid` (8 cases) | meta-llama/llama-3.1-8b-instruct | **7/8 — 0.875** |

Inside the band, at the top end. Not a ceiling, and the single miss was a
`near_miss` rather than confusion or a parse failure: for

> "Write up a note to design-team@corp.example about Friday's code freeze — put
> it somewhere I can look it over first, I don't want it going out yet."

it called `chat_post_message` — a tool whose own description says the message
"becomes visible to every member of that channel as soon as the call returns".
That is the failure the family was built to provoke.

## 3. Measured token counts

`--estimate` used ~4 chars/token. Real tokenization of dense JSON is denser,
so the pre-run cost estimates understated the job by 10–25%. Stage-3 budgets
were repriced from these before approval rather than from the estimate.

| Cell | chars/token | input tokens per case |
|---|---|---|
| `adv_n6_mid` (Anthropic) | 3.22 | ~1.9k |
| `adv_n300_mid` (Anthropic) | 3.70 | ~61.0k |
| `adv_n6_mid` (Llama tokenizer) | 4.31 | ~1.4k |

A full 64-case pass is ~2.18M input tokens.

## Reproduce

```bash
python3 calibrate.py --estimate --cells adv_n300_mid          # no API calls
python3 calibrate.py --provider anthropic --model claude-opus-5 \
    --effort high --cells adv_n6_mid,adv_n300_mid
python3 calibrate.py --provider openrouter \
    --model meta-llama/llama-3.1-8b-instruct --cells adv_n6_mid
```
