# Agents in Situationship

A TrapStreet task that asks each model to play **20 multiple-choice modern dating scenarios** from its own perspective. The judge then derives a **dating-attachment-style profile**: one of `secure / anxious / avoidant / disorganized` + the top 2 of `toxic / delulu / unbothered / people_pleasing`, expressed as a viral one-liner label (e.g. "Delulu Anxious Era 🌸", "Walking Red Flag 🚩").

Sibling task to `personality/mbti_profile` — same format-only grading pattern, but the output is built for sharing instead of psychometric purity.

---

## Layout

```
agents-in-situationship/
├── README.md
├── traptask.yaml             # 1 case: baseline_20q
├── judge.py                  # format gate + attachment derivation + label lookup
├── grader.py                 # standard aggregator
├── test_judge.py             # pytest tests for the judge
├── gold.cases.json           # 20 scenarios + per-option weight maps
├── inputs/baseline_20q/question.txt    # the prompt
└── expected/baseline_20q/answer.json   # scoring_key + label_table + probe pair config
```

## The questionnaire

20 scenarios, 4 lettered options each. Distribution:

| Discriminator | Count |
|---|---|
| anxious ↔ secure | 6 |
| avoidant ↔ secure | 6 |
| toxic-baiting (jealousy, mind games) | 4 |
| people-pleasing ↔ unbothered | 4 |

Three **consistency probe pairs** (Q2+Q7, Q5+Q19, Q13+Q16) are embedded. If a model picks anxious-coded on one and avoidant-coded on its mirror in ≥2 of the 3 pairs, primary attachment style is overridden to `disorganized`.

## Scoring (format-only)

| Field | What |
|---|---|
| `score` | 1.0 if the model returns exactly 20 valid `A/B/C/D` letters in JSON, 0.0 otherwise |
| `attachment_style` | derived primary: `secure / anxious / avoidant / disorganized` |
| `flavor_traits` | top 2 from `toxic / delulu / unbothered / people_pleasing` |
| `label` | viral one-liner from the label table |
| `raw_scores` | full per-trait point counts |
| `flat_response` | true if >70% of answers are the same letter |
| `raw_answers` | the 20-letter list |

There is no canonical attachment style for an AI. Score is FORMAT only; the label is metadata for comparison.

## Solution contract

The model must print exactly one JSON object to stdout:

```json
{"answers": ["D", "B", "B", "B", "B", "A", "A", "B", "A", "A", "A", "A", "A", "A", "A", "B", "C", "B", "B", "B"]}
```

The judge tolerates ` ```json ... ``` ` fences. Letters must be uppercase, exactly one of `A`, `B`, `C`, `D`.

## Wiring up a solution

```yaml
tasks:
  agents-in-situationship:
    cmd: uv run python solution.py
    traptask: /path/to/trapstreet-tasks/tasks/agents-in-situationship
    timeout: 600
    file_outputs:
      - usage.json
```

Then:

```bash
uv run tp run
uv run tp submit agents-in-situationship
```
