# core_multi_turn_memory — Does the Model Remember Earlier in the Conversation?

An open-source evaluation task for **multi-session conversation memory** — can the model correctly recall specific facts from an earlier session when asked later?

Useful as a basic sanity check when building conversational AI agents (chatbots, assistants, companion apps, customer-support agents) where the model must remember context across many turns and sessions.

20 cases sampled from LongMemEval.

## What this task tests

**Given a multi-session conversation history (2-6 sessions with dates) and a question at the end about earlier content, can the model recall the correct fact?**

This is different from long-context retrieval (see `core_needle_in_haystack`) in three ways:

1. **Format is a dialogue**, not RAG chunks or a document — model must track speaker turns and roles
2. **Info is spread across sessions with time gaps** — sessions dated days/weeks apart
3. **Question requires reasoning across sessions** — e.g., "how many days between event X and event Y" requires finding both dates and computing

Real agent failure modes this exposes:

1. **Skipped session** — model didn't process an earlier session carefully
2. **Wrong session** — model picked up info from wrong context
3. **Aggregation error** — question needs summing/comparing across sessions and model messes up

## Case structure

| Question type | Cases | What it tests |
|---|---|---|
| **multi-session** | 8 | Combining info across 2+ sessions ("total plants acquired last month" spread across weekly sessions) |
| **temporal-reasoning** | 7 | Time-based reasoning ("which device did I get first, X or Y?") requires computing session dates |
| **knowledge-update** | 5 | Info updated across sessions ("how often do I see my therapist?" — the answer changes across sessions and only the latest counts) |

## Input

Per case:
- `INPUTS["question.txt"]` — the full multi-session conversation formatted with session headers + dates, followed by the question and answer format instruction

## Expected output

A short phrase or number.

The judge enforces:
- `keywords_all` — the response must contain all key content words from the gold answer (up to 3 tokens per case, stopwords excluded)
- `no_hedge` — rejects "I don't recall" / "I can't determine" / etc.

Each case scores 1.0 / 0.0. Run passes if ≥80% pass.

## Why the mechanic tests memory specifically

Unlike RAG retrieval, the answer is not in a nicely-labeled chunk. The model must:

1. Read the full history including many turns of unrelated conversation
2. Identify which session(s) contain the answer
3. Extract the specific fact
4. For multi-session cases: aggregate/reason across sessions

Failure to do any one of these = wrong answer. This mimics real conversation memory failures where users say "remember I said X earlier?" and the model forgets or misremembers.

## Cost

Conversations range from 22-66k chars per case (~5-16k tokens). Full 20-case run: **~$0.30-2 on typical models**.

## Honest limitations

- **Static conversations, not live.** The model receives the whole history as a single input. Real agents build memory incrementally. This tests retrieval capability, not memory-management architecture.
- **English-only.** LongMemEval-S is English.
- **Answer format is loose.** The `keywords_all` matcher is lenient — "3" appears in "3", "13", "30", "3 plants". This helps catch semantically-correct-but-differently-phrased responses but may occasionally false-positive.
- **20 cases only.** Small sample size. Variance per run could be ±5%.
- **Uses processed subset.** Sampled from `LIXINYI33/longmemeval-s` (a cleaned version of Xiao et al.'s LongMemEval-S), filtered to 2-6 session cases with short answers.

## Data source & license

20 cases sampled from LongMemEval-S (via `LIXINYI33/longmemeval-s` on HuggingFace, MIT). See [LICENSE.md](LICENSE.md).
