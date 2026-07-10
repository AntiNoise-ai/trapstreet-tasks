# core_follow_instructions — Does the Model Follow Instructions in the Prompt?

An open-source evaluation task for **instruction following** — does the model actually obey constraints stated in the prompt (word count, format, forbidden words, tone) or does it drift?

Useful as a basic sanity check when building AI agents that rely on the system prompt / instruction prompt to steer model behavior — which is essentially every agent, since instruction-following is the primary lever for shaping agent output.

25 cases sampled from Google's IFEval benchmark.

## What this task tests

**Given a prompt with verifiable constraints (e.g., "write in all lowercase" + "include the word 'blueprint' exactly 3 times" + "at least 300 words"), does the model produce output that satisfies EVERY constraint?**

Instruction following is where a lot of agent bugs live. A system prompt says "always respond in JSON" — but the model returns markdown-wrapped JSON. A prompt says "keep under 200 words" — but the model returns 350. A prompt says "do not use commas" — but the model can't help itself.

The failure mode is usually silent: the model produces reasonable-looking text that violates one of the constraints, and the downstream parser or user experience breaks in ways that are hard to trace back.

## Case structure

| Difficulty | Cases | Constraints per case | What it tests |
|---|---|---|---|
| **easy** | 5 | 1 | Baseline — does the model handle a single constraint? |
| **medium** | 12 | 2 | Can the model handle two constraints together (e.g., word count + no commas)? |
| **hard** | 8 | 3 | Three simultaneous constraints — most agent instruction prompts have many rules |

## Constraint types covered

The 25 cases together cover 17 constraint types from IFEval:

- `punctuation:no_comma` — no commas allowed
- `change_case:english_lowercase` / `english_capital` — all lower/upper case
- `keywords:forbidden_words` — must not contain listed words
- `keywords:existence` — must contain listed keywords
- `keywords:frequency` — keyword appears N times
- `keywords:letter_frequency` — specific letter appears N times
- `startend:quotation` — response wrapped in `"..."`
- `startend:end_checker` — must end with a specific phrase
- `combination:repeat_prompt` — must repeat the prompt verbatim at start
- `combination:two_responses` — two responses separated by `******`
- `length_constraints:number_words` / `number_sentences` / `number_paragraphs`
- `detectable_format:number_highlighted_sections` — N `*text*` highlighted sections
- `detectable_format:number_bullet_lists` — N bullet points
- `detectable_format:title` — must include a `<<Title>>` title
- `detectable_format:json_format` — must be valid JSON
- `detectable_content:number_placeholders` — N `[bracket]` placeholders
- `detectable_content:postscript` — must include a `P.S.` section

## Input

Per case:
- `INPUTS["question.txt"]` — the IFEval prompt (the constraints are stated in natural language within the prompt itself)

## Expected output

Free-form text that satisfies EVERY constraint stated in the prompt.

The judge enforces:
- `ifeval_constraints` — runs each declared verifier against the response
- `no_hedge` — rejects responses that punt (e.g. "I can't help with that")

Each case scores 1.0 only if ALL constraints pass. This is intentional — real instruction-following is all-or-nothing (a JSON output with one wrong field breaks the downstream parser).

## Why this is hard

- **Constraint interaction.** Some constraints conflict subtly. "Write 500 words + no commas" is hard because English long prose naturally uses many commas.
- **Silent failures.** Models often "almost" comply — 4 highlighted sections instead of 5, 199 words instead of 200 — and the eval catches these where a human review might not.
- **Multi-constraint tracking.** Hard cases require holding 3 constraints simultaneously, and models regularly forget one while satisfying others.

## Cost

25 text-only cases with short prompts. ~$0.05-0.30 per full run on most models.

## Honest limitations

- **English-only.** IFEval is English. A multilingual instruction-following test would be a v2.
- **Constraints are structural, not semantic.** IFEval verifies form (word count, format, keywords) not meaning (tone, on-topicness). Semantic instruction following is harder to grade.
- **Subset of IFEval verifiers.** This task supports 20 of IFEval's ~35 constraint types. The 6 unsupported (mostly language:response_language variants, complex format detectors) are skipped in sampling.
- **All-or-nothing scoring.** A response satisfying 2 of 3 constraints scores 0. This is intentional (see above) but means one buggy constraint fails a whole case.

## Data source & license

25 cases sampled from Google's IFEval (`HuggingFaceH4/ifeval` on HuggingFace, Apache 2.0). See [LICENSE.md](LICENSE.md).
