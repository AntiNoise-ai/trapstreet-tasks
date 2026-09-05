# frontend_silent_defects — the page looks finished

**Not yet validated.** One arm has run against it and passed everything; it has
never been shown to separate two tools. It stays in `unvalidated/` until it does.

## What it measures

A tool is given a brief and prints one self-contained HTML page. The judge opens
that page in real Chromium and asks things a screenshot cannot answer:

- **behaviour** — click the annual toggle. Do the prices change?
- **responsive** — at 375px, does anything stick out of the viewport?
- **robustness** — swap in a 240-character plan name. Does the layout hold?
- **constraints** — were the explicit prohibitions in the brief actually obeyed?

All of these fail *invisibly*. Two pages scoring 1.00 and 0.33 look the same side
by side, which is the reason this exists: a preference vote cannot find the
difference, because the voter is looking at the same picture.

## The cases

| case | family | what it varies |
|---|---|---|
| 01 | behaviour | baseline — one brief, plainly stated |
| 02 | constraints | constraint count, k≈7 (compositional load) |
| 03 | behaviour | a counterfactual requirement, against the obvious default |
| 04 | constraints | prohibitions — what the page must *not* do |
| 05 | behaviour | same checks as 01, brief padded with irrelevant context |
| 06 | robustness | 13 hostile `window.__DATA__` payloads |
| 07–09 | open | free briefs — landing page, dashboard, form flow |

Cases 07–09 emit `score: null`. They run every check as a floor (loads, throws
nothing, survives 375px) and are reported as `floor_passed`, but nothing ranks
them. There is no gold that settles whether a landing page is good.

## Why contrast and labels are diagnostics, not score

The judge runs axe-core and publishes the counts, but they never move `score`.

A contrast failure is fixed by one bolt-on step: run a checker before returning.
Any tool can copy that the week it sees this board, so a score built on it would
saturate in one release cycle. Behaviour and robustness have no such step — a
dead toggle is fixed by building it right.

There is a second reason, found while testing rather than argued: on
`fixtures/broken.html` — a page with an unlabelled email input and two `<div>`s
acting as buttons — **axe's entire ruleset reports one thing, contrast.** `label`
does not fire, because a `placeholder` counts as an accessible name;
`button-name` does not fire, because a `<div>` has no button role to name. So the
a11y family is both the most gameable *and* the least sensitive. It rides along
because the counts are worth seeing, and for nothing else.

## Layout

```
check/inspect.mjs   the browser half — puppeteer-core against system Chrome,
                    axe-core injected. Emits per-check results, one tiled
                    capture per UI state, and rects.json (the gallery
                    overlay's boxes).
check/panel.py      an LLM judge panel. NOT WIRED IN — see below.
check/anchors/      seven screenshots the panel used, sorted blind on a 1-3
                    scale. Superseded: two are contradicted by labels/. Kept as
                    record; nothing reads them.
labels/             human judgments over the open-brief pages, with the
                    instrument and the caveats that come with them.
judge.py            pulls the page out of stdout, calls the inspector,
                    turns one family into one score.
fixtures/           good / broken / counterfactual / wizard — the judge's own
                    test set.
inputs/case_NN/     the brief handed to the solution.
expected/case_NN/   which family decides this case, and its assertions.
```

The inspector needs Node and a Chrome on the machine; it downloads no browser.
Set `CHROME_PATH` if Chrome is not at the macOS default.

```bash
npm install --prefix check
node check/inspect.mjs fixtures/broken.html check/spec.example.json /tmp/out
```

## First real run, 2026-08-31 — and the judge bug it found

One arm (`opus-ceiling`, a bare `claude-opus-5` relay) over the six scored cases.

**It passed everything.** 20/20 on the five levers, then 13/13 on the hostile-data
case. The task does not currently separate anything at the frontier.

The hostile-data case *appeared* to catch it — 0.0, "1 element(s) clip their
content" on the 240-character plan name. That was the judge being wrong. The page
had line-clamped the heading to three lines, added an ellipsis, and put the full
string in a `title` attribute: correct handling, better than this repo's own
`fixtures/good.html`, which simply wraps. The check now fires only when content
vanishes with **no** affordance — no ellipsis, no title, no aria-label.

Two things follow. The repo's claim that every task's first real run turns up a
judge defect held again. And the axis is wrong: METR measures task length as the
dominant predictor of agent success (R²=0.83), with frontier models near-100%
under about four human-minutes. This brief is a ten-minute job. No number of
extra constraints closes that gap.

## The judge panel, and why it is not wired in

`check/panel.py` is a three-lens LLM judge — a design director who sees the
render, an engineer who sees only the source, a client checking the brief — over
four axes on a 1–3 forced choice, calibrated against seven screenshots the task
owner sorted blind on that same scale. The method is written up in
[docs/writing-a-judge-rubric.md](../../docs/writing-a-judge-rubric.md).

It was run twice over nine pages from three different labs, authors hidden, and
appeared to fail badly: two pages sitting in its own prompt labelled "2" came
back 3.00 and 2.75, its ranking contradicted the owner's held-out judgments, the
mean swing between runs was 0.36 on a 1–3 scale, and `1` was never used once
across 72 scores.

**Then the ground truth turned out to be partly wrong.** Elicited pairwise
instead — nine same-brief pairs, each shown twice with the sides swapped — the
owner agreed with herself 9/9 with no position bias, and every brief came out
transitive. Two of the three briefs reproduced her earlier overall sort. The
landing brief inverted completely: `good_landing.jpg`, the level-3 landing
anchor, is the page she now ranks *last* of three. So "it contradicted its own
anchors" was, on that page, the anchor being wrong.

Scored against the pairwise order instead, the panel gets **5 of the 7 non-tie
comparisons** in run 2 — and 7 comparisons cannot separate a working judge from
a coin. That is the honest state: not refuted, not shown to work. It stays out
of the score *and* out of the diagnostics until a gate passes it, because a
column published beside real measurements gets read as information.

Three findings survive, and the first is the one worth carrying:

1. **Check the labels before blaming the judge.** Her pointwise good/bad labels
   inverted on a third of the material; her pairwise ones held 9/9. Ask a human
   for comparisons, not grades.
2. **A within-brief order is ordinal, not absolute.** Knowing 07B beats the
   other two landings does not make it a "3", so `anchors.json` cannot be
   rebuilt from this data — which is the real argument for moving both the
   elicitation and the judge to pairwise, more than anchor count ever was.
3. **The form cases were never judgeable from an image at all**: those pages are
   exactly one viewport tall because steps 2–4 do not exist until a click, so
   every capture showed two of eleven fields. That one was a defect in the
   *input*, not the judge, and it is fixed — see below.

## Capturing a UI that has states

Fixed 2026-09-05, after the panel run made the cost visible.

The inspector now **walks** the page instead of photographing it once. It fills
the visible fields with plausible values, presses the control that reads like
"next", and captures again — up to four states, stopping the moment a click
changes nothing or would leave the page. Each state is captured as 1280×1600
tiles, so neither the fold nor legibility is lost. `states_captured` and, per
state, the label it pressed are reported.

Open briefs cannot declare a click path — we do not know the selectors — so this
is a heuristic and it is honest about being one: it reports what it pressed, and
a page it cannot advance simply reports one state. `fixtures/wizard.html` is a
three-step form whose steps 2 and 3 are not in the DOM until step 1 validates,
and `tests/test_judge.py` fails if the walker stops short of it.

This does not rescue the panel. It removes one reason the panel had no chance.

## Known open questions

- **Does it discriminate?** Still unrun with more than one arm. The gate is
  per-case zero-variance: any case every arm passes, or every arm fails, gets
  cut. Point-biserial comes later, when there are enough arms for a correlation
  to mean anything.
- **A "cheat arm" is planned** — a solution that runs axe-core on its own output
  before returning. Whichever family it tops is a family with a short life.
- **`expected/` is readable by solutions.** trap-cli runs solutions unsandboxed
  with an absolute `inputs_dir`, and the assertions are in `expected/`. For a
  build task that is less broken than it sounds (satisfying the assertions *is*
  the job), but a solution can target the exact checks instead of building well,
  and that has to be handled before this ships.
- **Cases 07–09 have never run through `tp run`.** They were generated out of
  band for the anchor set. Note that an arm with a low `max_tokens` will truncate
  on an open brief and score `no_html` — a contract miss, not a capability
  failure, and `contract_miss` marks it as such.
