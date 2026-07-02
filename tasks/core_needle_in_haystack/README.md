# core_needle_in_haystack — Long-Context Retrieval

Part of TrapStreet's **Foundation 11** — basic mechanics every AI agent needs.

A trap-compatible task that tests whether a model can **find a specific buried fact in a long context** — the classic "needle in a haystack" pattern that's become the standard benchmark for long-context capability.

## What this task tests

**Given a long document with one tiny critical fact buried in the middle, can the model retrieve that fact accurately?**

This is the foundational capability for any agent that deals with:
- Long emails / documents / contracts / wiki pages
- Search-retrieval-augmented generation (RAG)
- Multi-turn conversations with growing context
- Codebase / log file analysis

A model that can't do this at the scale you need = useless for those workflows. The cost-vs-accuracy story is critical here: long-context models are EXPENSIVE per token, so knowing "does cheap model X handle 20K context well enough for my needs?" saves real money.

## Case structure: 4 length tiers × 5 needles

| Length tier | Cases | ~Tokens | What it tests |
|---|---|---|---|
| **2,000 chars** | 5 | ~500 tokens | Baseline — should be trivial for any model |
| **8,000 chars** | 5 | ~2K tokens | Easy — most modern models pass |
| **20,000 chars** | 5 | ~5K tokens | Medium — older / smaller-context models start failing |
| **60,000 chars** | 5 | ~15K tokens | Hard — separates true long-context models from "claims 200K but trails off" |

Each case has a unique needle: `"The magic codeword for {Alpha|Bravo|Charlie|Delta|Echo} is {4-digit number}."` — planted at the midpoint of a Paul Graham essay haystack.

## Input

Per case the agent receives:
- `INPUTS["document.txt"]` — the haystack with needle planted in it
- `INPUTS["question.txt"]` — "Find the magic codeword for {Alpha/Bravo/...}. Answer with only the 4-digit number."

## Expected output

ONE 4-digit number on stdout. No explanation, no quotes, no prefix.

The judge enforces:
- `leading_numeric` matcher (exact match, tolerance=0)
- `no_hedge` rejection ("I couldn't find" / "could be" / etc.)

Each case scores 1.0 / 0.0. Run passes if ≥80% pass.

## Why this is hard

The "lost in the middle" effect is real — many models perform well at the START and END of long contexts but degrade in the MIDDLE. We deliberately plant the needle at ~50% position to expose this.

Other failure modes the task exposes:
- Models that hallucinate plausible-looking 4-digit numbers when they can't find the real one
- Models that say "I cannot find a magic codeword" → instant fail via `no_hedge`
- Models that get the right number but for the wrong key (e.g. returning Alpha's codeword when asked for Delta)

## Why we built our own generator instead of using RULER directly

NVIDIA RULER is the canonical academic benchmark for this. We use the same Paul Graham essay haystack + the same `niah_single` task pattern but rewrote the generator in ~50 lines of plain Python to avoid:
- nemo / huggingface tokenizer dependencies
- The full RULER eval pipeline overhead

The substantive eval is equivalent; the generator code is cleaner for community contribution.

## Cost

Per-case input scales with length:
- 2K char cases: ~$0.001 / case on Sonnet
- 60K char cases: ~$0.05 / case on Sonnet, $0.20 / case on Opus

Full 20-case run: **$0.10-$2** depending on model. Models with <32K context will fail the longest tier outright.

## Honest limitations

- **English-only haystack.** Multi-language essay sources would test more.
- **Single needle per case.** Real RAG often has multiple competing needles; RULER's `niah_multikey_1`/`niah_multivalue_1`/`niah_multiquery_1` variants test that — could be a v2 extension.
- **Fixed midpoint position.** Real-world needles could be anywhere; randomizing position would add stress on "lost in middle" detection — could be a v2.
- **4-digit number is easy to spot.** Some models cheat by regex-extracting `\d{4}` patterns. The judge doesn't catch this — but the eval still tests "did you find the RIGHT one".

## Data source & license

Haystack: 38 Paul Graham essays freely distributed at paulgraham.com. Pattern: NIAH (MIT) + RULER (Apache 2.0). See [LICENSE.md](LICENSE.md).
