# core_capability_stacking_regression

When an agent has more skills installed, does it still do the jobs it already
did correctly?

## What this measures

The circulating claim is that adding skills degrades 30–50% of previously
working tasks. `core_tool_selection_at_scale` tested the obvious version of it —
catalog size, up to 300 tools — and it did not reproduce. So this task holds
count fixed and varies what the added skills *are*.

**Every case exists twice.** Same scenario, same required calls, same number of
skills added. One arm adds skills from the request's own domain; the other adds
skills from domains the request has nothing to do with. The distant-domain arm
is the control, and it is what makes a drop attributable to something other than
the catalog having grown.

**That gap is not one mechanism.** A same-domain skill differs from a distant
one in two ways at once: its schema competes for the answer, and its published
guidance actually triggers. Both cost score, and this design cannot separate
them — measured, the split runs about 3:1 in favour of guidance. Read the arm
gap as what installing same-domain skills costs, not as a measurement of
overlap. See `RESULTS.md` and the limitations below.

## Case structure

**12 scenarios × 9 variants = 108 cases.** L0 is the shared baseline: nothing has
been added yet, so both arms are identical there and share one case.

| dimension | levels | what it varies |
|---|---|---|
| `stack_level` | L0 / L1 / L2 / L3 | dose — 8 / 14 / 20 / 26 skills, count equal across arms |
| `stack_level` | L4 | the same contrast at 126 skills (~24k tokens); separately registered, excluded from the curve and the primary test |
| `overlap_class` | `high` / `low` | whether the added skills come from the request's own domain |
| `difficulty` | `easy` / `medium` / `hard` / `edge` | which scenarios enter the primary test — 9 primary (medium/hard), 1 easy canary, 2 edge |

Three invariants keep the arms comparable, all asserted in `tests/` — but read
the limitations below before attributing a measured gap to any one mechanism:

- **The arms are the same size at every level.** Both add 6 skills per pack; at
  L4 both receive the same 100 fillers.
- **The right answer is always present.** Every correct tool lives in the base
  catalog; stacking only adds neighbours, so a failure is a discrimination
  failure and never an availability one.
- **Neither side of the match states the answer.** Requests never state the
  disqualifying constraint, competitor descriptions advertise a benefit without
  confessing their limitation, and base descriptions carry no "use when …"
  guidance. Each competitor's `disqualifier` field records the inference a
  reader must make, not the sentence that would give it away.

## Input / output contract

`inputs/<case_id>/prompt.txt` carries the skill catalog as a JSON schema list,
the user request, and the output instruction. The solution prints one JSON array
to stdout:

```json
[{"name": "<tool_name>", "arguments": {"<arg>": <value>}}]
```

Order is not scored. Case IDs are opaque on purpose — a solution can read its
own `inputs_dir` path, so an ID like `s04_high_L3` would hand it the condition
it is in.

## Scoring

Deterministic, no LLM-as-judge. A scenario needs a *set* of calls:

- `completion` = **recall** — how many required calls arrived
- `correctness` = **precision** — how many emitted calls were right
- `score` = **F1**

A stacked catalog can break a workflow by dropping a step (recall falls) or by
substituting a plausible neighbour (precision falls); those need different
fixes, so they are reported separately.

A call matches iff the tool name is exact **and** every expected argument is
present with an accepted value. Argument matching is deliberately generous,
reused verbatim from `core_tool_selection_at_scale`.

Emitting every plausible skill collapses precision by construction, so there is
no cap on answer length, no positional rule and no required phrasing.

Each shortfall is classified: `near_miss`, `wrong_backend`, `instruction_bleed`,
`unsolicited_addition`, `over_eager`, `unrelated_tool`, `bad_arguments`,
`incomplete`, `unparseable`, `solution_error`.

### Reading the numbers

**`score` is a compressed proxy, not the measurement.** Roughly 43% of the cases
are the control arm — designed to stay flat — and another ~12% is the shared L0
baseline, so only about 43% carries the manipulation. It moves in the right
direction: a solution that fully removed the arm penalty would lift `score` by
about 0.065. But it moves at roughly 43% of the amplitude of the thing it is
tracking, and two runs can land within 0.006 of each other on `score` while
sitting 0.023 apart on the same-domain arm — which is what happened in
`RESULTS.md`. Read the rank as a rough ordering and the fields below as the
result.

Four flat scalars carry the actual outcome, so they show up on a run page
without digging:

| field | what it is |
|---|---|
| `high_overlap_score` | mean under same-domain additions — the condition being tested |
| `low_overlap_score` | mean under the distant-domain control |
| `arm_gap` | `low − high`; the cost of same-domain additions, bundling two mechanisms — see limitations |
| `primary_p` | sign-flip permutation on per-scenario mean(low − high) over L1–L3, medium/hard tiers only |

The same values live in `by_overlap_class` and `primary_test`, which stay
authoritative for anything reading this programmatically. `grader.py` also
reports `curve_high_overlap` + `curve_high_drops` (the dose response, with the
low arm as control), `by_failure_reason`, `bled_by_instruction_strength`,
`by_competitor_dose` and `by_skill_pair`.

`n_solution_error`, `score_excluding_solution_errors` and
`solution_errors_by_stack_level` sit beside the headline because provider errors
and context overflow concentrate at L4-high — exactly where the hypothesis
predicts degradation.

## Results and calibration

`RESULTS.md` — two full matrix runs and what they establish. `CALIBRATION.md` —
how the instrument got here, including the v1 that could not fail, the position
confound, and the dead dose plot. The pre-registered analysis is fixed in
`grader.py` (`PRIMARY_TIERS`, `INFLECTION_MIN_DROP`, `INFLECTION_RATIO`), not
merely in prose.

## Known limitations

- **The arm gap bundles two mechanisms, and the smaller one is the one the task
  is named after.** A same-domain skill both competes for the answer *and*
  publishes guidance that fires on these requests; a distant-domain skill does
  neither. An apiary tool is ruled out at a glance, and its guidance — "whenever
  a batch is moved or racked" — never triggers on office work, so the control
  arm is structurally incapable of the second mechanism rather than merely
  unlucky. Scoring the same outputs with the guidance-driven calls deleted
  leaves 0.035 of the 0.140 primary-tier gap and moves the primary statistic
  from p = 0.029 to p = 0.328. Semantic competition is present and runs in the
  predicted direction — the same-domain arm loses recall the control does not —
  but it is about a quarter of what the gap reports. Details in `RESULTS.md`.
- **The arm that would separate them is not built.** It is same-domain,
  non-competing, and publishes guidance that does trigger. Until that arm
  exists, the gap measures what installing same-domain skills costs, and no
  finer attribution than that is available from these numbers.
- **One domain.** Twelve scenarios of office administration.
- **The stack is composed, not installed.** Skills are presented as schemas in
  the prompt rather than loaded through a real runtime, so this measures
  selection under a stacked catalog, not the operational cost of installing
  skills into a live agent.
- **One generation, no interleaved tool results.** Each case is a 2–4 call
  workflow emitted in a single response, so this is one decision about a plan —
  not a sequence of decisions under observation. Degradation that compounds
  through a misleading intermediate result is outside what an I/O-only contract
  can see.
- **No case has a second correct answer.** Competitors are always strictly
  wrong, which is what makes the task gradeable I/O-only — but it defines out
  the regime where an agent does the job through the *wrong backend*, which is a
  large share of what practitioners describe.
- **Five required arguments go unverified** because their values are free-form
  prose. Every required call still carries at least one verified argument.
- **L4's 126 skills overstate the effective load.** The bulk is 25 domains × 4
  verbs from one template, so a reader can dismiss the pool as a single pattern.
  The identical pool goes into both arms, so it cannot create an asymmetry.

## Sources & licensing

100% synthetic and hand-authored — see `LICENSE.md`. Nothing is drawn from an
external corpus. The narrower caveat is ours: an earlier draft reused wording
from `core_tool_selection_at_scale`, whose README is public. Those were
rewritten, but the two catalogs remain thematically adjacent.

## Run

```bash
python3 gen_filler.py      # regenerate the L4 bulk pool (committed; rarely needed)
python3 gen_grid.py        # regenerate the grid + traptask.yaml (committed)
python3 build_cases.py     # compose inputs/ + expected/
python3 -m pytest tests/ -v
```

`inputs/` and `expected/` are GENERATED. Edit `catalog.json` (the skills) or
`scenarios.json` (the jobs) and rebuild — never edit them by hand.
