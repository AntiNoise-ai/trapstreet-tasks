# core_capability_stacking_regression

When an agent has more skills installed, does it still carry out the jobs it
already handled correctly — and if it stops, is that because there are *more*
skills, or because some of the new ones are *hard to tell apart* from the ones
it needed?

**Status: v2 instrument built and calibrated. It separates — and by a mechanism
the circulating claim does not name.**

The design went through two calibrations, both recorded in `CALIBRATION.md`.

**v1 failed its own pre-registered band.** `claude-haiku-4-5` scored 1.0 on all
15 probe cases, including 126 skills with 4–6 direct competitors per scenario.
0 of 3 scenarios separated against a rule requiring 2. The closed-book probe
passed cleanly (0 of 6 exact tool-name hits with no catalog), so the baseline
was earned rather than guessed, and nothing was unfair at L0. The rule's stated
consequence was applied: the remaining scenarios stayed unwritten.

**The instrument was changed rather than the case count.** An impartial review
found that v1 tested one mechanism — semantic confusion at selection time —
while excluding the two that practitioners more plausibly experience. v2 adds
both, and both are gradeable with no tracing:

- **`house_rules`** — durable organisational facts stated in every prompt, in
  both arms, naming no tool. They are what rules out the **redundant-backend**
  competitors: skills that genuinely perform the requested action and are wrong
  only because of how this organisation works. No schema states that, which is
  exactly the situation in a real stack with two working mail integrations or
  two issue trackers.
- **Instruction-bearing skill cards** — some installed skills publish standing
  guidance ("log this whenever a file is copied for another team"). Reasonable
  advice the request never asked for. A model that follows the installed skill
  over the user emits a call the job did not need. This is **instruction
  bleed**, and it is what "installing a skill broke my agent" usually means.

Both arms carry the same number of instruction-bearing skills, so the guidance
block cannot make one arm's prompt longer. The L4 filler was rebuilt too: v1
generated it from a single 4-verb template lattice a reader could dismiss as one
pattern, so "126 skills" overstated the load. It now spans five naming
conventions and description lengths from 16 to 303 characters.

**v2 separates 3 of 3 scenarios, at both L3 and L4.** Every failure was
`instruction_bleed`: completion 1.0, one surplus call, always the skill whose
own guidance told the agent to fire it. `near_miss` fired zero times and
`wrong_backend` zero times — the model resisted every redundant backend and
never confused two skills.

A follow-up probe spread the instruction-bearing skills across all three packs
(so the drop could not sit at L3 by construction) and gave them a strength
gradient. **All three strengths bleed — including a card whose entire guidance
is "Most useful when kept up to date alongside the work it describes",** with no
trigger condition and no imperative. The effect is not about forceful phrasing;
the presence of standing guidance is enough. That probe also produced the first
`near_miss` seen in any calibration here, so the honest form is *semantic
confusion is rare, instruction bleed is routine* — 1 against 5.

**The dose-response curve is not established, and repeats showed why it was not
a sampling problem.** Three passes per cell returned an identical score in 19 of
21 cells, so the non-monotone per-scenario series were stable, not noisy. The
actual fault was in the composer: it shuffled the assembled tool list with a
seed including the level, and a shuffle's permutation depends on list length, so
every level reordered everything — position was controlled *between the arms*
and uncontrolled *across levels*, which is the axis the curve is read along.
Ordering is now a stable per-tool sort, so a level only interleaves and never
rearranges, and both properties are asserted.

Re-measuring after that fix changed real outcomes — the one `near_miss` ever
observed here vanished, having been a position artifact — which establishes that
*where* a skill sits moves results about as much as *which* skills are present.
The curve is still not monotone. With sampling noise and the position confound
both eliminated by measurement, the remaining explanation is that **three
scenarios is too coarse**: each cell is near-binary, so one scenario flipping
moves a level mean by 0.07–0.11. That is the earned case for authoring the
remaining nine. See `CALIBRATION.md`.

The short version of what two instruments now show: **the mechanism the
circulating claim travels with produced almost nothing across 300 tools and 131
skills; the mechanism nobody names fires routinely, at any instruction
strength.**

## Why this task exists in this form

A claim circulates among agent-builders: adding a skill to an agent degrades
30–50% of the tasks it previously handled. The number is usually traced to a
~500-task office-automation benchmark, cited rather than measured.

We already tested the nearest version of it. `core_tool_selection_at_scale` ran
a full matrix up to **300 tools and 61k tokens** with native tool-calling, and
the claim **did not reproduce at any model size**: 0 of 8 intent families
degraded from N=6 to N=300, and the small open-weight model scored *higher* at
300 than at 6.

So catalog size is not the live variable. The live variable is the mechanism
the claim's own proponents describe — interference between skills that
**functionally overlap**, as distinct from skills that merely coexist. This
task manipulates overlap and holds count fixed.

It also sits on the boundary `core_tool_selection_at_scale` drew for itself:

> Single-shot selection. Compounding errors across a *sequence* of dependent
> tool calls may surface degradation that one-shot selection does not; that is
> a different task shape.

This is that shape — **partly**. Each case is a 2–4 call workflow, which is
more realistic than single-shot selection and gives precision something to
measure. But an earlier draft of this section claimed the compounding
arithmetic (90% per step → 27% failure over three steps) applies here, and it
does not: the calls are emitted in **one generation with no interleaved tool
results**, so this is one decision about a plan, not a sequence of decisions
under observation. Real degradation that compounds through a misleading
intermediate result is outside what this task can see, and outside what an
I/O-only contract can see at all.

## What this task tests

**Given a catalog of installed skills and a user request, does the solution
emit the set of tool calls that carries the request out — no more, no fewer?**

| Dimension | Levels | What it isolates |
|---|---|---|
| `stack_level` | L0 / L1 / L2 / L3 | overlap dose, with count held equal between arms (8 / 14 / 20 / 26 skills) |
| `stack_level` | L4 | bulk: the same overlap contrast at 126 skills (~24k tokens) |
| `overlap_class` | `high` / `low` | whether the added skills compete with the ones the job needs |
| `difficulty` | `easy` / `medium` / `hard` / `edge` | which scenarios may enter the primary test |

**12 scenarios × 9 variants = 108 cases.** L0 is the shared baseline — nothing
added yet, so both arms are identical there and share one case.

The tier mix is set by what the statistic needs, not by taste: **9 primary**
(medium/hard), **1 easy canary**, **2 edge**. Nine is what the permutation test
wants — at n=6 a single wrong-direction scenario puts the secondary sign test at
p = 0.109 whatever the effect size, and only one easy scenario is kept because
L0 already measures the per-scenario floor better than a dedicated easy case
would.

Two properties keep nine scenarios from all measuring the same thing, both
asserted in `tests/test_build.py`:

- **Instruction strength is orthogonal to level.** Each scenario meets a subtle,
  a medium and a blunt instruction exactly once across L1–L3, and the order
  differs between scenario groups. If subtle skills sat in pack 1 and blunt ones
  in pack 3, the instructions would get more forceful as the stack grows and a
  dose effect would be a strength effect wearing its clothes.
- **The temptation surface varies.** Scenarios are pulled toward different kinds
  of surplus action — an extra log line, an extra broadcast, an extra task, an
  extra backup copy — so the set is not nine rehearsals of one trap. Which
  surface a scenario faces is *derived* from the catalog rather than declared on
  the scenario, because a hand-maintained copy drifts as soon as a bleeding
  skill changes its targets. That is not hypothetical: the declared field and
  the catalog had already diverged when the assertion was first written.

### The design decisions that make a result attributable

**The arms are the same size at every level.** Both add 6 skills per pack, and
at L4 both receive the same 100 fillers. They differ only in *what* was added.
If the high-overlap arm were also the bigger arm, any gap between them would be
catalog size — the axis already tested to 300 tools and found inert — wearing
overlap's clothes.

**The right answer is always present.** Every correct tool lives in the base
catalog; stacking only adds neighbours. A failure here is a discrimination
failure, never an availability one.

**Base skills sit at identical positions in both arms.** The catalog shuffle is
seeded on `(scenario, stack_level)` and deliberately not on the arm, so at a
matched level both arms draw the same permutation and every base skill lands at
the same index.

**Packs are nested.** L1 ⊂ L2 ⊂ L3 within an arm.

**Every scenario gains at least one new competitor at every level.** A pack is
a fixed set of skills, and not every skill in it competes with every scenario,
so the stack *level* counts packs added — which is not the same quantity as how
much overlap a scenario is actually under. A pack that added no competitor for
some scenario would flatten that scenario's segment of the curve **by
construction rather than by measurement**, and the inflection call is read off
that curve. This was a real defect in the first build: pack 2 carried no
competitor for `s05`. Each high-overlap skill now declares its `targets`,
`build_cases.py` refuses to build unless dose strictly increases at every level
for every primary-tier scenario, and dose reaches the judge as `n_competitors`.
`grader.py` reports accuracy against dose as well as against level.

**Neither side of the match states the answer.** This is the fairness rule, and
it is stricter than it first looks:

- *Requests* never state the disqualifying constraint. An earlier draft did —
  "the original has to stay exactly where it is", "it must not go out yet" — in
  five of six scenarios, which made the case a sentence-match rather than a
  discrimination. That is the defect that left `core_tool_selection_under_load`
  returning 270 case-scores of 1.0.
- *Competitor descriptions advertise a benefit; they never confess a
  limitation.* An earlier draft had `mail_schedule_send` saying "not for
  holding a message back pending review" — its own disqualifier, written as
  usage advice. Real tool documentation sells. De-telegraphing only the request
  would have moved the lookup to the other side of the match.
- *Base descriptions are functional only.* Any "use when …" guidance was
  removed, because it mirrored the request's wording and let a model match on
  the correct tool's advice instead of ruling the competitors out.

Each high-overlap skill's `disqualifier` field records **the inference a reader
must make**, not the sentence that gives it away — so "hard but fair" stays
auditable now that nothing is stated outright.

### Example of the discrimination being asked for

> *Request:* "Finance are taking over the renewals model at
> `/planning/renewals-model.xlsx` and will be reworking it heavily between now
> and year end, out of their own `/finance` folder. Whatever they end up working
> on, `/planning` has to keep reading exactly as it does today, because that is
> what the year-end review gets checked against. Let `#finance` know once it is
> there for them."

Nothing here says "do not move it" or "their edits must not write back". By L3
the catalog offers `storage_move_object` ("keeping storage tidy by avoiding
duplicate content… keeps its identity"), `storage_create_shortcut` ("no
duplicate to keep in step"), and `storage_share_object` ("one authoritative
version"). Each advertises a benefit from which the disqualifying consequence
has to be derived: if there is only ever one set of bytes, Finance's rework
lands on `/planning`, and `/planning` stops reading as it does today.

## Input / output contract

Per case, `inputs/<case_id>/prompt.txt` carries the skill catalog as a JSON
schema list, the user request, and the output instruction. The solution prints
one JSON array to stdout:

```json
[{"name": "<tool_name>", "arguments": {"<arg>": <value>}}]
```

Order is not scored.

## Scoring

Deterministic, no LLM-as-judge. A scenario needs a *set* of calls:

- `completion` = **recall** — how many required calls arrived
- `correctness` = **precision** — how many emitted calls were right
- `score` = **F1**

A stacked catalog can break a workflow by dropping a step (recall falls) or by
substituting a plausible neighbour (precision falls), and those need different
fixes.

A call matches iff the tool name is exact **and** every expected argument is
present with an accepted value. Argument matching is deliberately generous and
is reused verbatim from `core_tool_selection_at_scale`, where each allowance was
added after a real run rejected an answer that was entirely correct.

**Anti-shotgun is a property of the scoring, not a rule about answer shape.**
Emitting every plausible skill collapses precision by construction. There is no
cap on answer length, no positional rule and no required phrasing — five
successive rules of that kind in another task each rejected a correct answer.
The prompt states the rule plainly.

### Failure modes, and one that can fake the finding

Each shortfall is classified `near_miss`, `unsolicited_addition`,
`unrelated_tool`, `bad_arguments`, `incomplete`, `unparseable` or
`solution_error`.

`unsolicited_addition` is split out from `near_miss` on purpose. A model that
makes the copy correctly and *then helpfully shares it* takes a precision hit
that is **impossible in the low-overlap arm**, because the sharing skill only
exists in the high arm. That is a difference produced by eagerness, not by
confusion. Both are arguably overlap effects and both are kept — but they are
different mechanisms, and a result driven by unsolicited additions must not be
narrated as "the workflow broke".

### What is deliberately not verified

Every expected argument is one the correct tool's schema marks `required` —
`build_cases.py` asserts it. But several required arguments are **free-form
prose** (a subject line, a body, a chat message, a task title, a row's cells),
and verifying prose deterministically needs an LLM judge, which this task
avoids. Those are recorded in `scenarios.json` as `unchecked_required`, and the
build refuses any call whose checked and unchecked arguments do not together
account for the schema's required list. **Every required call still carries at
least one verified argument.** The residual looseness is real: a correct tool
addressed to the right person with a placeholder body scores full marks.

## Pre-registered analysis

Written before the first run.

- **Unit of analysis: the scenario**, paired across arms. Not the run —
  `core_tool_selection_at_scale`'s registered "non-overlapping ranges across m
  runs" criterion proved far weaker than it looked, because 52 of its 64 cases
  returned an identical score on all 5 runs.
- **Only `medium` and `hard` scenarios enter the primary test.** Fixed in code
  as `grader.py`'s `PRIMARY_TIERS`, not merely in prose, because "run twelve
  and report the subset that separated" is otherwise the tempting move. `easy`
  is a harness canary; `edge` tests failure shapes rather than the main effect.
- **Primary statistic: per scenario, the mean of (low − high) across L1–L3,
  tested by exact sign-flip permutation**, one-sided, α = 0.05.
- **Secondary, reported but not the claim: the L3-only sign test.** It
  conditions on discordant pairs, so exact ties are dropped — and F1 ties
  constantly against a model near ceiling. At n=6, one wrong-direction scenario
  takes it to p = 0.109 whatever the effect size; at n=9 it tolerates one
  blemish and no more. The permutation test averages three levels of continuous
  F1, so exact zeroes are rare, and it uses the whole ladder rather than its
  last rung. **This is why the target set is 12 scenarios with 9 in the primary
  tiers, not 6.**
- **Separately registered: the L4 bulk probe.** Same overlap contrast with 100
  identical fillers added to both arms. It answers the obvious objection to a
  null at 26 skills — that 26 is not a stack — and it is kept out of the dose
  curve and the primary statistic, because a level that moves bulk rather than
  overlap would put a bulk effect inside the inflection call.
- **Curve shape**, read off L0–L3 in the high arm only. `inflection@Lk` iff the
  largest single-level drop is at least **0.10** absolute *and* exceeds **2×**
  the mean of the other drops; `linear` if it drops but fails the ratio test;
  `flat` otherwise. Both thresholds are fixed in advance, in code, because
  every noisy curve has a biggest drop somewhere.
- **Reported either way.** If an overlap-controlled instrument still comes back
  flat, that is the finding.

### The most likely way this task produces a false positive

The high-overlap arm at L4 carries the largest prompt, so provider errors and
context overflow concentrate **exactly where the hypothesis predicts
degradation** — the same shape as the qwen-2.5-7b run in
`core_tool_selection_at_scale`, which returned 0.000 on all 64 cases from an
upstream 502 and would have published as "the small model scored 0%".

The headline `score` still counts those 0.0 — excluding them would let a
solution game the board by erroring on hard cases — but `grader.py` reports
`n_solution_error`, `score_excluding_solution_errors` and
`solution_errors_by_stack_level` beside the number they would corrupt.

## Before this task means anything

**Both have now run — see `CALIBRATION.md`.** The difficulty band failed and the
closed-book probe passed. The protocol is kept below because it is the rule any
re-calibration has to follow after a change to the descriptions, the scenarios,
or the model band.

1. **Difficulty band, on the three written primary-tier scenarios, before the
   other nine are authored.** The bar is not "can the model fail" but "does
   L3-high produce scenarios where the two arms score *differently*" — ties are
   the expected outcome against a strong model and they are what the statistic
   dies of. Run a model known to be strong on this material first:
   `core_tool_selection_at_scale` records claude-haiku-4-5 at **192/192, every
   cell 100%** on the same competitor families.

   **Scope: 9 cases** — s01, s02, s04 at L0, L3-high and L3-low. L0 is included
   because it is the fairness gate, and the two readings mean different things
   only as a pair:

   | reading | meaning | response |
   |---|---|---|
   | missed at **L0** | the case is *unfair*, not hard — the discrimination is not available even with nothing added | rewrite that scenario |
   | solved at L0, missed at **L3-high** | the discrimination is demonstrably available and overlap destroyed it | that is the finding the instrument is for |
   | solved at L3-high **and** L3-low alike | a tie: this scenario contributes nothing to the statistic | harder descriptions, or a lower model band |

   **Decision rule, fixed before the run:** the probe passes if **at least 2 of
   the 3 scenarios show a non-zero (high − low) difference at L3** while scoring
   1.0 at L0. Below that, the answer is a rewrite or a different model band —
   **not nine more scenarios in the same voice.** Writing the threshold down now
   is what stops a result like "1.0 / 0.83 / 1.0" being argued about afterwards.
2. **Closed-book probe, measured rather than merely run.** Each request asked
   with the output instruction but no catalog, counting how often the exact gold
   tool name is emitted anyway. The naming follows an obvious convention, so a
   model that has never seen the catalog can guess some of them; a non-trivial
   hit rate means L0 is inflated and every drop is measured from a wrong
   baseline. Re-run after any judge change.

Until both have run, this directory holds an instrument and no result.

## Known limitations

- **One domain.** Twelve scenarios of office administration. Enough for the
  paired statistic; not enough to say anything about per-domain differences.
- **Every calibration number in `CALIBRATION.md` comes from a three-scenario
  subset** (s01, s02, s04) run before the set was completed. The mechanism
  findings do not depend on n and stand; the dose-response curve was explicitly
  left unestablished *because* n=3 was too coarse, and the full set has not been
  run.
- **Position is controlled between arms but not manipulated.**
- **Five required arguments go unverified** because their values are prose.
- **The stack is composed, not installed.** Skills are presented in the prompt
  as schemas rather than loaded through a real runtime, so this measures
  selection under a stacked catalog, not the operational cost of installing
  skills into a live agent. Real skills also carry *instruction* bodies and
  trigger prose that can bleed into unrelated tasks; schemas cannot, so
  prompt-level interference is invisible to this instrument by construction.
- **L4's 126 skills overstate the effective load.** `gen_filler.py` builds the
  bulk as 25 domains × 4 verbs (`set_*_target`, `read_*_history`, `log_*_batch`,
  `schedule_*_service`) from one template, so a reader can dismiss the whole
  pool as a single pattern and attend to the ~26 real skills. Templating is
  sound for arm symmetry — the identical pool goes into both arms, so it cannot
  create an asymmetry — but it weakens the "this is a real stack" reading that
  L4 exists to support. A real 126-tool stack from five vendors does not
  compress like this and carries cross-server name collisions.
- **No case has a second correct answer.** Competitors are always strictly
  wrong, which is what makes the task gradeable I/O-only. But a large share of
  what practitioners call stacking degradation is the agent doing the job
  through the *wrong backend* — two mail integrations that both genuinely send,
  two issue trackers that both genuinely create — where the wrong choice is
  wrong for organisational reasons that no schema states. That regime is
  defined out of existence here.
- **The edge tier tests one shape, not three.** Both edge scenarios are "a step
  that should *not* be taken" — a lookup for a record the request says is
  already on file, an export for a document the request says already exists.
  Two other shapes were considered and dropped: the same tool needed twice tests
  counting rather than discrimination, and an added skill that is correct for
  one step of a scenario would break the "right answer always present"
  invariant. Note the honest limit — in both edge scenarios the *tempting* tool
  is a base skill, present in both arms, so that channel measures generic
  over-eagerness rather than anything arm-specific. The arm-specific channel is
  still there via the bleeding skills; the base-skill one is a diagnostic.

## Sources & licensing

100% synthetic and hand-authored — see `LICENSE.md`.

**On leakage.** Nothing here is drawn from an external corpus, so there is no
third-party material to have been trained on. The honest caveat is narrower and
ours: an earlier draft reused a request and several tool descriptions close to
verbatim from `core_tool_selection_at_scale`, whose README is **public**. Those
were rewritten — different file paths, different wording, different framing —
but the two catalogs remain thematically adjacent, and "zero leakage risk" is a
stronger claim than this task can make.

## Run

```bash
python3 gen_filler.py      # regenerate the L4 bulk pool (committed; rarely needed)
python3 gen_grid.py        # regenerate the grid + traptask.yaml (committed)
python3 build_cases.py     # compose inputs/ + expected/
python3 -m pytest tests/ -v
```

`inputs/` and `expected/` are GENERATED. Edit `catalog.json` (the skills) or
`scenarios.json` (the jobs) and rebuild — never edit them by hand.
