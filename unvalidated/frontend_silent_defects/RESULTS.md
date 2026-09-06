# Does it discriminate? No.

**2026-09-06. Three arms, six scored cases, eighteen scores, all 1.00.**

| case | lever | opus-relay | gpt-terra | kimi-k3 |
|---|---|---|---|---|
| case_01 | baseline | 1.00 | 1.00 | 1.00 |
| case_02 | constraint count (k≈7) | 1.00 | 1.00 | 1.00 |
| case_03 | counterfactual | 1.00 | 1.00 | 1.00 |
| case_04 | prohibitions | 1.00 | 1.00 | 1.00 |
| case_05 | no-op distractor | 1.00 | 1.00 | 1.00 |
| case_06 | 13 hostile payloads | 1.00 | 1.00 | 1.00 |
| | | **6/6** | **6/6** | **6/6** |

`claude-opus-5`, `openai/gpt-5.6-terra-pro`, `moonshotai/kimi-k3`. Identical bare
relays — same `solution.py`, no system prompt, no tools, `max_tokens=16000` —
differing only in the model. Arms at
[Ruqii/trapstreet-solutions@d2693d8](https://github.com/Ruqii/trapstreet-solutions/tree/d2693d8/frontend_silent_defects).

The rule was written before the run: two arms differing on two or more cases
means it discriminates; everything passing everything means it does not ship.

**It does not ship.**

## The checks were not a no-op

Worth stating, because "everything passed" and "nothing ran" produce the same
number. Every case ran its full set and every check in it passed:

```
case_01  behaviour 2/2   robustness 1/1                  responsive 1/1
case_02  behaviour 7/7   robustness 1/1                  responsive 1/1
case_03  behaviour 2/2   robustness 1/1  constraints 2/2 responsive 1/1
case_04  behaviour 2/2   robustness 1/1  constraints 3/3 responsive 1/1
case_05  behaviour 2/2   robustness 1/1                  responsive 1/1
case_06  behaviour 2/2   robustness 13/13                responsive 1/1
```

Thirteen adversarial `__DATA__` payloads — empty strings, 240-character names,
HTML in a price field, missing keys — survived by all three. Zero console
errors, zero horizontal overflow at 375px, across the board.

## The one thing that did separate, and why it stays unscored

The a11y diagnostics moved, and not in the same direction for each arm:

| | case_01 | 02 | 03 | 04 | 05 | 06 |
|---|---|---|---|---|---|---|
| **contrast** opus-relay | 0 | 3 | 0 | 0 | 0 | 0 |
| gpt-terra | 0 | 2 | 4 | 2 | 0 | 4 |
| kimi-k3 | 0 | 0 | 0 | 1 | 0 | 0 |
| **naming** opus-relay | 5 | 0 | 4 | **19** | 0 | 0 |
| gpt-terra | 0 | 0 | 0 | 0 | 0 | 0 |
| kimi-k3 | 0 | 0 | 0 | 2 | 0 | 0 |

The arms are genuinely different here: gpt-terra never leaves an unlabelled
control and has the most contrast failures; opus-relay is the reverse, with 19
naming violations on the prohibitions case; kimi-k3 is cleanest on both.

This is not a rescue, and it is not being promoted to `score`. The reason a11y
was excluded is in the README and it has not changed: a contrast or label
failure is fixed by running a checker before returning — one bolt-on step, which
any tool can copy the week it sees the board. A column that separates today and
saturates on the next release is worse than no column, because the ranking it
produces reverses without anything real having changed. Moving it into the score
now, *because* it is the only thing that moved, is the exact post-hoc adjustment
the pre-registered rule exists to prevent.

## Why this was the expected outcome

The first probe passed 20/20, and METR's measurement is that task length
dominates agent success (R²=0.83), with frontier models near-100% under about
four human minutes. This brief is a ten-minute job. Adding constraints does not
change its length, and case_02 (k≈7) is the proof: seven simultaneous
requirements, all three arms clean.

The finding is not "frontend cannot be benchmarked". It is narrower and it is
the one worth writing down: **at a ten-minute brief, deterministic frontend
checks do not separate frontier models.** Everything the instrument can see —
behaviour, robustness, responsive, constraint compliance — they all already do.

## What this run also settles

The three open briefs are not rescued by this either. The judge that would have
read them scored at chance (`labels/gate_stage1.json`), and the deterministic
floor they *are* scored against was cleared by every arm here.

So the task has no scored dimension that separates and no unscored one that can
be trusted. It stays in `unvalidated/` permanently.

## Cost

trap-cli recorded `cost_usd_total: null` for all three — the SDK paths this
relay uses are not wired into its cost tracking. Estimated from output size
(~13KB of HTML per page, 18 pages): well under $1.50.

---

# The rebuilt version — one arm so far

**2026-09-06, `kimi-k3` against Moonshot directly.** Seven scored cases, dense
scoring, the generated hostile family and the budget case both live.

| case | lever | score | checks |
|---|---|---|---|
| case_01 | baseline | 1.000 | 2/2 |
| case_02 | constraint count (k≈7) | **0.571** | 4/7 |
| case_03 | counterfactual | 1.000 | 2/2 |
| case_04 | prohibitions | 1.000 | 3/3 |
| case_05 | no-op distractor | 1.000 | 2/2 |
| case_06 | 13 written + **40 generated** payloads | 1.000 | **53/53** |
| case_10 | budget (70 / 42 / 10,500) | 1.000 | 3/3 |

**The two new mechanisms did not bite.**

*Generated hostile data:* 53/53. All forty generated payloads survived —
prototype pollution, lone surrogates, 300 combining marks, whole-`__DATA__`
type swaps, five injection strings. The generator is not toothless: it found a
live XSS in this repo's own `fixtures/good.html` on its first run. The model's
page is simply better than our fixture was.

*Budget:* 3/3. Stated in the brief, the ceiling is easy to hold. It separates
budgeted from unbudgeted output — `fixtures/overbuilt.html`, real output from
the morning run, misses all three limits — but that is not a capability
difference, it is the difference between being told and not being told.

**The one that moved is the one we already had, and it wobbles.** case_02 is the
seven-constraint case. Three runs of the same model:

| run | endpoint | case_02 |
|---|---|---|
| 10:49 | OpenRouter | 7/7 |
| 16:42 | OpenRouter | 6/7 |
| 17:58 | Moonshot direct | 4/7 |

The 4/7 failure is real, not a judge artifact — the page is complete (ends in a
proper `</html>`, 12,601 bytes) and simply never emits `data-testid="tier"` or
`data-testid="price"`. It dropped the tier-rendering requirement outright.

Two readings are still open and one run cannot separate them: run-to-run
variance, or a difference between the routed and the direct endpoint. What is
already clear is that **a case whose score moves 7/7 → 4/7 across runs of one
model cannot be read from a single run**, which puts a question over the
morning's 18/18 as well. Repeats come before more arms.
