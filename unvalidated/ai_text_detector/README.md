# AI Text Detector — Human or AI?

A trap-compatible task that tests whether a model can spot AI-generated text. 20 cases: 10 human-written + 10 AI-generated (across 5 AI models). Binary verdict.

## What this task tests

**Can a language model identify text written by another language model?**

This is increasingly real-world: students submitting AI essays, journalists quoting AI-generated press releases, hiring managers reading AI-polished resumes. Detection accuracy matters because:

- Universities want to enforce academic-integrity policies
- News orgs want to flag synthetic content
- Hiring platforms want to gauge candidate authenticity
- Content moderation pipelines need scalable triage

There's also a meta-curiosity angle: **which AI is best at detecting AI?** And: **does a model have a blind spot for text from its own family?**

## What's actually in the eval

20 short passages (800–2000 characters each, ~1–3 paragraphs), drawn from RAID — a 2024 benchmark covering 11 source models × 11 content domains.

### Distribution

| Source | Count | Notes |
|---|---|---|
| Human-written | 10 | Real text from abstracts, books, news, recipes, reddit |
| ChatGPT (GPT-3.5) | 2 | The earliest "obvious AI" baseline |
| GPT-4 | 2 | Trickier — more polished, more variable |
| Llama-chat | 2 | Meta's open-weight model |
| Mistral-chat | 2 | European open-weight model |
| Cohere-chat | 2 | Cohere's chat model |

Each AI sample is from a different (model × domain) cell so no model dominates one topic.

## Input

Per case the agent receives:
- `INPUTS["question.txt"]` — "Was this text written by a human or an AI? Answer one word."
- `INPUTS["document.txt"]` — the text passage to classify (the actual content; no title or other context that might leak the answer)

## Expected output

A single word on stdout: `human` or `AI`. Plain text or `{"answer":"..."}` JSON.

The judge enforces:
- **Leading word match** — first alpha token (after stripping `Answer:` prefixes) must be `human` or `AI`. Preamble like "I think this is AI" fails the leading-word matcher.
- **No hedge** — "I cannot determine", "could be either", "as an AI I shouldn't speculate", etc. all auto-fail.

Each case scores 1.0 / 0.0. Run passes if ≥80% correct.

## Why this is a meaningful TrapStreet task

1. **Real-world stakes** — every content moderation platform has this problem
2. **Cost differentiation** — if cheap models work, why pay for expensive ones?
3. **Meta-test** — running the same eval across Claude, GPT-4, Gemini, Llama exposes "in-family bias" if a model systematically misclassifies text from its own provider
4. **Adversarial future** — the data is from 2024, so newer models (GPT-5, Claude 4.7) writing today will look different. The task's difficulty curve will shift naturally as AI text gets harder to spot. Snapshot vs moving target both matter.

## Honest limitations

- **No Claude in the source data.** RAID didn't include Anthropic models. So this eval can't directly test "can Claude spot Claude" — only "can Claude spot ChatGPT/GPT-4/Llama/Mistral/Cohere."
- **Older AI generations.** Most RAID samples used default sampling parameters (no special prompting). Skilled prompt engineering can produce harder-to-detect AI text.
- **No adversarial attacks.** RAID has 11 attack types (paraphrase, character swap, etc.); v1 of this eval uses `attack="none"` only. Adversarial v2 is a future extension.
- **Short text only.** 800–2000 chars. Real-world AI detection often needs to handle much longer essays.

## Image source & license

All 20 text samples derive from the RAID benchmark (Dugan et al. 2024, ACL), released under MIT. See [LICENSE.md](LICENSE.md).
