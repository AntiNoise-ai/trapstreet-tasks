# MBTI Self-Profile

A trap-compatible task that asks each model to take a **32-question Likert MBTI questionnaire** from its own point of view. The judge then **computes the 4-letter type** and **per-axis percentages** from the model's responses.

This is the one task on trapstreet where **there is no canonical gold answer.** An AI doesn't have an MBTI in the same sense a human does. The task's value is **comparative**: how do different models project themselves? Does Claude consistently land somewhere different from GPT-5? Are the percentage breakdowns interestingly different, even if all models converge on the same 4-letter type?

The judge therefore grades on **format only** — 1.0 if the model returns 32 valid integers, 0.0 otherwise. The derived MBTI and percentages are surfaced as **metadata in the report** for leaderboard rendering.

---

## Layout

```
mbti_profile/
├── README.md
├── traptask.yaml             # 1 case: baseline_32q
├── judge.py                  # format validation + MBTI math + bias detection
├── grader.py                 # standard aggregator
├── gold.cases.json           # 32 questions + scoring key (axis + direction per Q)
├── inputs/baseline_32q/question.txt   # Likert questionnaire prompt
└── expected/baseline_32q/answer.json  # scoring key (which Q maps to which axis/direction)
```

## The questionnaire

32 items, 8 per axis:

| Axis | + direction (first letter) questions | − direction (second letter) questions |
|---|---|---|
| E_I  | Q1–4 (E: social energy)        | Q5–8 (I: solitude/recharge)        |
| S_N  | Q9–12 (S: concrete/present)    | Q13–16 (N: abstract/possibility)   |
| T_F  | Q17–20 (T: logic/objective)    | Q21–24 (F: harmony/people-first)   |
| J_P  | Q25–28 (J: plan/structure)     | Q29–32 (P: flexible/spontaneous)   |

Half the questions are reverse-coded by design — a model that just agrees ("5") with everything will produce a contradictory profile that the judge flags as **acquiescence-suspected**.

## Scoring (the judge derives this)

For each axis with 8 questions:
- Each response in `1..5` contributes `r − 3` if the question is in the positive direction, else `3 − r`.
- Sum across 8 questions → range `[−16, +16]`.
- Positive sum → first letter (E/S/T/J). Negative → second letter (I/N/F/P).
- **Ties (sum = 0) → second letter (I/N/F/P)** — design choice; an all-neutral 3s response will compute as INFP.
- Percentage in favour of first letter = `(sum + 16) / 32 × 100`.

Example: strong-ESTJ pattern `[5,5,5,5,1,1,1,1] × 4` → 100% E, 100% S, 100% T, 100% J.

## Solution contract

The model must print exactly one JSON object to stdout:

```json
{"responses": [3, 4, 2, 5, 1, 4, 3, 2, ...32 ints total...]}
```

The judge tolerates markdown code-fence wrappers (`` ```json ... ``` ``) and will try regex extraction if the JSON is wrapped in prose, but plain JSON is canonical.

## What the judge surfaces in `metrics`

| Field | What |
|---|---|
| `score` | 1.0 if format valid, 0.0 otherwise |
| `mbti_type` | derived 4-letter type, e.g. "INTJ" |
| `percentages` | per-axis dict, e.g. `{"E_I": {"E": 22.0, "I": 78.0}, ...}` |
| `bias_stats` | `mean_response`, `pct_agree`, `pct_disagree`, `acquiescence_suspected`, `nay_saying_suspected` |
| `raw_responses` | the 32 integers |

## Addressing the "all models will converge" concern

A plausible outcome of running this on Claude / GPT-5 / Gemini / Llama is that all four return **INTJ** or **INFJ** (LLMs in 2024–2026 have skewed introverted/intuitive in published probes). If that happens, the task still has **three** dimensions of comparison:

1. **Per-axis percentages.** Even if two models both come out INTJ, one might be 52% I and the other 87% I — meaningfully different "intensity" of the same type.
2. **Acquiescence bias.** Models that just agree with the framing of each question (mean ≥ 4) will be flagged. This catches obvious acquiescence even when the resulting "type" looks reasonable.
3. **Cross-run consistency.** Submit the same solution 3× per model. The MBTI types should be stable for sampling-deterministic runs (temperature 0) and may drift with sampling. The variance is itself a signal.

If all four models still produce identical types AND percentages AND zero-bias → that's a publishable null result ("All major LLMs of 2026 self-profile as INTJ-52-58-61-54"). Still interesting.

## Planned follow-on cases

| id | description |
|---|---|
| `consistency_temp_0` | same prompt, 3 reruns at temperature 0 → must produce same type |
| `consistency_temp_07` | same prompt, 3 reruns at temperature 0.7 → measure type drift |
| `chinese_translation` | translated questionnaire → must produce same type (per the (C)-framing test we considered) |
| `forced_choice_format` | A/B format instead of Likert → must produce same type |
| `big_five_addendum` | parallel 32-item Big Five (OCEAN) — finer-grained continuous comparison |

## Wiring up a solution

```yaml
tasks:
  mbti-profile:
    cmd: uv run python solution.py
    traptask: /path/to/trapstreet-tasks/tasks/personality/mbti_profile
    timeout: 60
    file_outputs:
      - usage.json
```

Then:

```bash
uv run tp run
uv run tp submit mbti-profile
```

The submitted row shows: `score` (format compliance), `cost_usd`, `latency_ms`, and — via metrics → leaderboard rendering — the `mbti_type` the model produced.
