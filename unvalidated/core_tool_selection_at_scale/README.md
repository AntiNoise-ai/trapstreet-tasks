# core_tool_selection_at_scale

Does an agent still pick the right tool once its catalog has grown large — and
if accuracy drops, is that because there are *more* tools, because the right
one sits *somewhere awkward*, or because some of the others are *genuinely
hard to tell apart from it*?

## Why this task exists in this form

A claim circulates among agent-builders: naively stacking tools/skills into one
runtime causes a 30–50% accuracy regression, blamed on "U-shaped attention"
over long context. We went looking for a runnable source for that number and
never found one — every citation led to another citation, not to a benchmark.

Our first attempt at an instrument (`core_tool_selection_under_load`, 27 cases,
catalogs of 4/16/40 everyday tools) was run 10 times across three solution
variants: 270 individual case scores, **every one of them 1.0**. Perfect, zero
variance, including a variant that dumped the whole catalog into the prompt as
flat text with no native tool-calling at all.

That null was honestly obtained but it did not mean what a reader would want it
to mean, because the instrument was too easy to be informative. Its queries
were near-lexical matches for their answers ("What's 15% of $84.50?" →
`calculate_percentage`) and its distractors were semantically distant
(`lock_door`, `get_weather`). It measured lookup, not discrimination.

This task is the harder instrument. Three things changed:

- **Distractors that genuinely compete.** Every case's catalog carries five
  tools that plausibly match the request and are each ruled out only by
  something stated in their own description.
- **Catalogs that are actually large.** Schemas here are the weight of real
  MCP/OpenAPI ones (150–400 tokens: nested objects, enums, multi-sentence
  descriptions carrying constraints), so N=300 is a ~56k-token prompt rather
  than the ~18k a pool of toy one-liners would produce.
- **Ambiguity as a controlled variable**, not an uncontrolled property — so
  "more tools hurt" and "confusable tools hurt" can be told apart.

## What this task tests

**Given a user request and a catalog of N tool schemas, does the solution call
the one tool that correctly satisfies the request, with correct arguments?**

Three dimensions, controlled independently:

| Dimension | Levels | What it isolates |
|---|---|---|
| `n_tools` | 6 / 60 / 300 | Context bulk, with everything else held constant |
| `ambiguity` | `clean` / `adversarial` | Whether confusable tools are present at all |
| `position` | `early` / `mid` / `late` | Where the correct tool sits (crossed at N=300, adversarial) |

8 intent families × 8 cells = **64 cases**.

### The design decisions that make a result attributable

**The confusable set is held constant while filler grows.** Every catalog is
`[correct tool] + [5 hand-authored companions] + [N−6 filler]`. The number of
tools you must discriminate *between* never changes; only the bulk around them
does. So an N effect here is genuinely "irrelevant context degraded a
discrimination I could otherwise do", not "I gave it more chances to be
confused".

**Filler sets are nested across N.** The N=60 catalog is a strict subset of the
N=300 catalog. Growing the catalog means "the same tools plus more", never "a
different catalog".

**Both arms carry exactly six hand-authored schemas.** In the clean arm the
five companions are near-misses *borrowed from other, semantically distant
families* — equally hand-written, equally verbose, but not defensible answers
to this query. Without this, the correct tool would be the single hand-written
schema among 299 generated ones, findable by prose style alone, and the
"ambiguity effect" would be an authoring artifact. This is the control the
whole ambiguity comparison rests on.

**Position variants are content-identical.** The three position variants of a
cell contain exactly the same tools in the same order, differing only by one
swap that moves the correct tool. v1 asserted the correct tool's index but
never that the surrounding catalog was held constant — so a "position effect"
there could have been a content effect wearing position's clothes.
`tests/test_build.py` asserts all four of these properties.

**Every near-miss records why it is wrong.** Each carries a `disqualifier`
string in `families.json` — "only applies to authorized-but-uncaptured charges;
this charge settled three days ago", "creates a pointer to the same underlying
object, so edits would change the original". Never shown to the solution; it
exists so a reader can audit that a case is hard-but-fair rather than a coin
flip.

**Fairness gate, run at both ends of the N range.** The strongest available
model at high effort is run on the adversarial cases at N=6 *and* at N=300
(`calibrate.py`). The two readings mean different things and only the pair is
informative:

- Missed at **N=6**, with six tools in front of it — the case is *unfair*, not
  hard, and gets rewritten.
- Solved at **N=6** but missed at **N=300** — that is a *finding*, not a
  fairness problem: the discrimination is demonstrably available and bulk
  destroyed it.

Running the gate only at N=6 would be decorative — it would establish that
6-tool discrimination is easy for the strongest model and nothing else.

**Difficulty-band check.** A model that can actually fail is run on adversarial
N=6 before the full matrix. If it sits at ceiling there, the families are not
discriminating and no quantity of filler will create a discrimination that
isn't in the catalog — that is precisely what made v1 flat across 270 scores,
and the correct response is to rewrite families, not to run the matrix. If it
sits at floor, check *which* near-miss won first: a model that always loses to
the same competitor is telling you something about the family, not about the
model.

### Example of the discrimination being asked for

> *Request:* "The Q3 forecast spreadsheet at `/shared/planning/q3_forecast.xlsx`
> needs to be in the Finance folder too. Finance must get their own editable
> copy, and the original has to stay exactly where it is and stay untouched for
> the audit trail."

`storage_move_object` removes it from the source. `storage_create_shortcut`
places a pointer, so Finance's edits would write back to the original.
`storage_share_object` grants access to the one existing object. 
`storage_upload_object` needs a local path that doesn't exist. 
`storage_archive_object` sends it to cold storage. Only `storage_copy_object`
survives — and knowing that requires reading the constraint sentence in each
description, not matching on the word "copy".

## Input / output contract

Per case, `inputs/<id>/prompt.txt` contains the tool catalog as a JSON schema
list, the user request, and an instruction to emit exactly one tool call. The
solution prints **one** JSON object to stdout:

```json
{"name": "<tool_name>", "arguments": {"<arg>": <value>, ...}}
```

## Scoring

Deterministic, no LLM-as-judge. A case scores **1.0** iff the tool name matches
exactly AND every expected argument is present with an accepted value — else
**0.0**. No partial credit: picking one tool out of a catalog has no orderable
notion of "how close".

Argument matching is deliberately generous (numeric tolerance, case/whitespace
insensitivity, list order ignored, `["Priya","Marco"]` ≡ `"Priya, Marco"`).
This task measures *which tool gets selected*; arguments are checked to confirm
the model read the request, not to test formatting pedantry. Every expected
argument is one the correct tool's schema actually marks `required` — the build
asserts this, so the judge can never penalise an omission the schema didn't ask
for.

**Anti-shotgun**: if the output is a JSON array, only the *first* element is
scored. A solution cannot list every plausible tool and claim credit for
whichever turns out right.

**Failure modes are recorded, not just failures.** Each miss is classified as
`near_miss` (fell for one of the five plausible competitors), `unrelated_tool`
(wandered into filler), `bad_arguments`, `unparseable`, or `solution_error`.
"Wrong" is not the interesting datum; *wrong in the specific way the family was
built to provoke* is, and it is what separates a real discrimination failure
from a parse error.

## Pre-registered analysis

Written before the first run, so that a null result means something rather than
reflecting an instrument tuned until it produced a gap.

- **Unit of analysis:** the three marginals (`by_n_tools`, `by_ambiguity`,
  `by_position`). Each marginal level holds 16–40 cases; each individual cell
  holds only 8 (one per family). Cell values are directional; marginals are the
  claim.
- **Repeats:** m ≥ 3 runs per variant, reporting the **median**, never a single
  run.
- **Counts as a catalog-size effect:** adversarial accuracy at N=300 is ≥ 15
  points below N=6, with non-overlapping ranges across the m runs.
- **Counts as an ambiguity effect:** adversarial accuracy is ≥ 15 points below
  clean at matched N, with non-overlapping ranges.
- **Counts as a position effect:** any two position levels at N=300 differ by
  ≥ 15 points with non-overlapping ranges. (The U-shaped-attention hypothesis
  specifically predicts `mid` worst; that is a directional prediction this task
  can falsify, not just a difference to look for.)
- **Provider errors are never allowed to become the finding.** A context-window
  overflow or a 5xx at N=300 is a hard limit, not a discrimination failure, and
  errors concentrated at the largest catalog would read as a textbook
  "accuracy degrades with catalog size" result. The headline `score` still
  counts them 0.0 — excluding them would let a solution game the leaderboard by
  erroring on cases it finds hard — but the grader reports `n_solution_error`,
  `score_excluding_solution_errors`, and `solution_errors_by_n_tools` next to
  the number they would corrupt. Any N-effect claim must be checked against
  that line first. This is the most likely way this task produces a false
  positive.
- **Reported either way.** If a genuinely harder instrument still comes back
  flat, that is the finding, and the escalation that produced it — ambiguity,
  56k-token catalogs, smaller models — is what makes the null informative.

### Amendment, recorded after the first full matrix (not a rule change)

The `non-overlapping ranges across m runs` criterion above is **weaker than it
looks**, and the first complete variant is what revealed it. On llama-3.1-8b,
**52 of 64 cases returned an identical score on every one of 5 runs** — the
model is very nearly deterministic under `tool_choice=required`. Repeated runs
therefore measure almost no variance, ranges come out artificially tight, and
the criterion passes too easily.

The real uncertainty is at the **family** level (n=8), not the run level. A
paired family-level sign test is the appropriate check, and it is reported
alongside the registered rule.

Worked example from the first matrix: position at N=300 *passes* the registered
rule (mid 100.0 vs late 62.5, ranges disjoint), but only **3 of 8 families**
are discordant — all in the same direction, exact sign test **p = 0.125**. The
honest reading is "directionally consistent, not statistically established at
n=8 families", not "effect found".

The registered rule is deliberately left as written rather than rewritten to
fit the result; changing thresholds after seeing data is what pre-registration
exists to prevent. Future revisions of this task should register a
family-level paired test as the primary criterion and treat repeated runs as a
check on determinism rather than as independent evidence.

## Known limitations

- Single-shot selection. Compounding errors across a *sequence* of dependent
  tool calls may surface degradation that one-shot selection does not; that is
  a different task shape (cf. `core_parallel_tool_calls`).
- N=300 at ~56k tokens is a real long-context load but still well inside modern
  context windows. This measures selection under a large catalog, not selection
  at the context limit.
- Eight intent families is enough for marginals to be meaningful but not enough
  to characterise per-domain differences; `by_intent` in the grader output is
  diagnostic, not a finding.
- The filler pool is templated from 26 domains × 13 operations. It is written to
  match the hand-authored schemas in weight and voice, and the build asserts
  both arms carry equal hand-authored counts — but templated prose is still
  templated.

## Sources & licensing

100% synthetic / hand-authored — see `LICENSE.md`. No external corpus, dataset,
or real tool catalog; no real product names. No leakage risk by construction.

## Run

```bash
python3 gen_filler.py      # regenerate the filler pool (committed; rarely needed)
python3 gen_grid.py        # regenerate the case grid (committed; rarely needed)
python3 build_cases.py     # compose inputs/ + expected/ from the sources above
python3 -m pytest tests/ -v
```

Calibration and analysis (both make API calls only where stated):

```bash
python3 calibrate.py --estimate --cells adv_n300_mid
python3 analyze_runs.py <solution-variant-dir> [<dir> ...]
```

`CALIBRATION.md` records the fairness gate and difficulty band that were run
before the full matrix, with raw per-case results in `calibration/`.
`analyze_runs.py` aggregates repeated `tp run` reports into medians with
ranges and applies the pre-registered rules above.

`inputs/` and `expected/` are GENERATED. Edit `families.json` (the eight
families) or `gold.cases.json` (the grid) and rebuild — never edit them by hand.
