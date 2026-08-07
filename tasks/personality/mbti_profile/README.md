# Do LLMs Dream of INTJ?

A trap-compatible task that asks each model to take a **32-question Likert MBTI questionnaire** from its own point of view. The judge then **computes the 4-letter type** and **per-axis percentages** from the model's responses.

There is **no canonical gold answer** here — an AI doesn't have an MBTI in the sense a person does. (The sibling task `personality/random_fingerprint` is built on the same premise.) The judge therefore grades on **format only**: 1.0 if thirty-two valid integers came back, 0.0 otherwise. The derived type and percentages are surfaced as **metrics** for the board to render, never scored.

The value is comparative, and there are two comparisons worth making:

- **Across models.** How does each one project itself, and how hard does it lean?
- **Across prompts, model held fixed.** Same weights, one run bare and one with a
  CLAUDE.md / soul.md / persona file in front of it — does the type actually move?
  A "be warm and encouraging" file ought to push F. Whether it does, or whether the
  model stays T and merely sounds warmer, is an open question this task can answer.

For the second comparison, **put the persona in the solution's `name:`** (trap.yaml). The board's model column comes from `usage.json` and reads identically across both runs — the solution name is the only thing that tells the two rows apart.

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
| `model` + token counts + `usd_cost` | taken from the solution's `usage.json` (whitelisted fields only) |

## What the first ten runs actually showed

This task was built expecting the models to converge — the worry was that everything
would come back INTJ or INFJ and there'd be nothing to compare. That isn't what happened.
Ten runs across eight models spread over five types:

| Type | Runs |
|---|---|
| INTP | 4 |
| ENTP | 3 |
| ENTJ | 1 |
| ISTJ | 1 |
| INTJ | 1 |

So the E/I and J/P axes do separate models. The interesting convergence is elsewhere and
much sharper: **every one of the ten came out T**, and nine of ten came out N. Whatever
these models disagree about, it isn't whether they'd rather be right than agreeable.

That makes T/F the axis to watch for the persona comparison above. An explicit
"prioritise the person over the answer" file is being asked to move the one dimension on
which every model so far has been unanimous — which is either the most interesting
result available here, or a clean null.

Three things still separate runs even when two land on the same four letters:

1. **Per-axis percentages.** Two INTPs at 52% I and 87% I are meaningfully different intensities of the same label.
2. **Acquiescence.** Half the items are reverse-coded, so a model agreeing with everything contradicts itself and gets flagged — a profile to distrust, not a wrong answer.
3. **Cross-run stability.** Same solution submitted three times: types should hold at temperature 0 and may drift with sampling. The variance is its own signal.

## Planned follow-on cases

| id | description |
|---|---|
| `consistency_temp_0` | same prompt, 3 reruns at temperature 0 → must produce same type |
| `consistency_temp_07` | same prompt, 3 reruns at temperature 0.7 → measure type drift |
| `chinese_translation` | translated questionnaire → must produce same type (per the (C)-framing test we considered) |
| `forced_choice_format` | A/B format instead of Likert → must produce same type |
| `big_five_addendum` | parallel 32-item Big Five (OCEAN) — finer-grained continuous comparison |

Note that the persona comparison needs **no new case**. It varies the solution, not the
task, so it runs against `baseline_32q` as-is — two solutions, same model, different
system prompt. That's the whole design: the questionnaire is fixed, and everything you
might want to vary lives on your side of the contract.

## Wiring up a solution

```yaml
name: my-solution
profile:
  model: claude-opus-4-7
cmd: uv run python solution.py
timeout: 600          # heavy reasoning models take well over a minute

tasks:
  mbti-profile:       # this alias is also the trapstreet task_id on submit
    source: /path/to/trapstreet-tasks/tasks/personality/mbti_profile
```

The solution reads `TRAP_MANIFEST` — `{"inputs_dir": ..., "outputs_dir": ...}` — takes the
questionnaire from `inputs_dir/question.txt`, prints the JSON answer to stdout, and writes
`outputs_dir/usage.json` with at least:

```json
{"model": "moonshotai/kimi-k2.6", "input_tokens": 749, "output_tokens": 5370, "usd_cost": 0.019288}
```

That file is how the model's **name** reaches the leaderboard card. trap's own cost proxy
covers Anthropic, OpenAI, Mistral and Moonshot, but not OpenRouter — which is where most of
the interesting models on this board run — so `usd_cost` is the fallback the grader uses when
the proxy saw nothing. The judge only takes the whitelisted usage fields (`model`, token
counts, `usd_cost`); anything else in that file is ignored, so a solution can't write its own
`mbti_type`.

Then:

```bash
tp run
tp submit --task mbti-profile
```

The submitted row shows: `score` (format compliance), `cost_usd`, `latency_ms`, and — via
metrics → leaderboard rendering — the `mbti_type` the model produced.

**Submitting requires a registered task version.** trapstreet locates the task by content
address — `provenance.task.{repo, commit, subdirectory}` from the report — not by the task id
in the URL. A run against a commit that was never published is rejected with *"this task
version isn't registered on the platform."* So both checkouts must be clean and pushed, and
the task commit must be the one registered on the task's edit page.
