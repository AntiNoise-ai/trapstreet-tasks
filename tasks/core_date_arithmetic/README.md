# core_date_arithmetic — Date / Time Reasoning

Part of TrapStreet's **Foundation 11** — basic mechanics every AI agent needs.

A trap-compatible task that tests whether a model can correctly do **date, time, and calendar arithmetic** — the everyday "3 days from Tuesday" / "what year did X end" / "what time is it in Tokyo when it's 9am in NYC" computations that any scheduling, booking, calendar, or finance agent will face.

## What this task tests

**Can the model do time math correctly?**

This sounds trivial — until you hand a model "It's 3pm UTC, what's the time in Tokyo?" and it confidently returns the wrong answer because it confused timezone offsets, or got DST wrong, or mixed up the calendar conversion for BC/AD years.

The eval covers 7 distinct subtypes of temporal reasoning:

| Type | Cases | What it tests |
|---|---|---|
| `add_subtract` | 3 | "Started 360 BC, lasted 8 years — when did it end?" |
| `compare` | 3 | "Which city visited in earliest year from this list?" |
| `multi_op` | 3 | Multi-step time arithmetic (start + duration × repetitions) |
| `schedule` | 3 | Meeting-slot intersection ("everyone available 2:30-3?") |
| `trick` | 3 | Unanswerable / underspecified questions — answer should be "unanswerable" |
| `duration` | 3 | Days between two dates ("How many days older is A than B?") |
| `timezone` | 3 | Cross-timezone time conversion |

## Why each subtype matters

- **`trick`**: separates models that hedge from models that hallucinate. The right answer is literally the string "unanswerable" — a model that invents a date instead of saying "can't compute" fails.
- **`timezone`**: tests whether the model knows real UTC offsets (not just "+5" assumption).
- **`schedule`**: tests interval-intersection logic.
- **`multi_op`**: tests whether the model can hold intermediate results in arithmetic chain.

## Input

Per case the agent receives:
- `INPUTS["question.txt"]` — the natural-language question, INCLUDING the original ToT prompt that asks the model to format its answer as JSON.

## Expected output

The model is asked to output JSON like `{"explanation": "...", "answer": "<value>"}` (per ToT's own design). The judge extracts the answer and matches it via:

- **`numeric` matcher** (tolerance ±0.5) — for pure-number answers (e.g. "2909" days)
- **`keywords_all` matcher** — for string answers (e.g. "352 BC", "Beijing", "unanswerable")
- **Multi-value `keywords_all`** — for compound answers (e.g. `{"A": 32, "B": 20, "C": 45}` → all 3 numbers must appear)
- **`no_hedge`** rejection — on every case

Each case scores 1.0 / 0.0. Run passes if ≥80% pass.

## Why this is hard

- Most LLMs are surprisingly bad at BC/AD year arithmetic (no year zero)
- Timezone questions trip up models that lazy-add/subtract instead of consulting the actual offset
- "Unanswerable" cases catch hallucination-prone models — strong models say "unanswerable" cleanly
- The keyword judge is loose enough that models can output explanations, but strict enough that a wrong final value fails

## Cost

21 small text-only cases, no images, no long context. ~$0.02-0.05 per run on most models.

## Honest limitations

- **English-only.** ToT is in English; date formats are western (MM/DD/YYYY, BC/AD).
- **Synthetic-style questions.** Many ToT questions use placeholder names like "E18 and E47" or "Camila" — not natural conversational style. Real-world agent users phrase differently.
- **3 cases per type.** Small sample. Variance per run could be ±5%. A v2 should expand to 5-10 cases per type for stability.
- **Timezone subset is small** (3 cases) — most timezone reasoning bugs happen in DST edge cases not represented here.

## Data source & license

All 21 cases sampled from baharef/ToT, `tot_arithmetic` split (CC BY 4.0). See [LICENSE.md](LICENSE.md).
