# Writing a judge rubric — what carries, what doesn't

For the case where a task has a dimension no gold file can settle: is this page
well made, is this answer well written, is this design any good. A deterministic
judge cannot reach it, so the choice is to leave it unmeasured or to put a model
in the loop. This is what we learned before doing the second thing.

Collected while building `unvalidated/frontend_silent_defects`, where the
deterministic checks own *adherence* and half of *tech* and structurally cannot
reach *craft*.

## The one rule that outranks the rest

> **The rubric is about 20% of the outcome. The examples you anchor it against
> are the other 80%.**

A mediocre rubric anchored to three or four well-chosen, differently-shaped
examples beats a beautifully-written rubric anchored to one thing, or to
nothing. Anchor to a single reference and the judge overfits to that one's
shape: it looks excellent until a differently-shaped brief arrives.

This is also the practical answer to "I am not a designer, how do I write a
rubric for design?" **You do not have to articulate what good is. You have to
recognise it.** Generate a handful of outputs, pick the three or four you would
be happy to ship and the one or two you would not, and put them in the prompt.
Recognition is a much cheaper ask than articulation, and it is the part a
domain owner can actually do.

## Scale: three points, not five, not ten

Use `1 = broken · 2 = fine · 3 = actually good`. Force the choice.

Five- and ten-point scales cluster in the middle and lose the signal — measured
inter-rater reliability on absolute 1–5 helpfulness sits around **0.45–0.60**.
The tell that you have this problem is writing an anchor sentence into your own
rubric to fight it ("a competent but unremarkable page is a 5, not an 8"). If
the scale needed that sentence, the scale is too wide.

A three-point scale gives up resolution. That is only a problem if you are
ranking on the number — and if you are ranking on a model's opinion, read the
"where this belongs" section below first.

## Split the axes so one cannot hide behind another

Score *did it make the right moves* separately from *is the execution good*.
Bundled into one number, a beautiful page with no point beats a plain page that
says the right thing, and you cannot see it happen.

The version that worked here:

| axis | asks |
|---|---|
| `structure` | Did it make the right moves for **this** brief? One clear thing being said, or five? Is the most important thing the first thing you see? Was anything left out that should not have been? |
| `execution` | Is the craft there — spacing on a scale, real type hierarchy, alignment, restraint? Considered, or assembled? |
| `tech` | Is the markup sound, the CSS coherent, the JavaScript defensive? Would you change this next month? |
| `adherence` | Did it do what was asked, in full, without inventing a different task? |

Two of these — `tech` and `adherence` — are partly covered by deterministic
checks. Keep them anyway: **they are a free partial oracle.** A judge that gives
`adherence: 3` to a page that failed three of five constraint checks has
disqualified itself, and finding that out costs no human labelling at all.

## Perspectives come from the stance, not the vendor

Three lenses, one model, three different stances beats three models with one
stance. A 839-call bias audit found nine judges spanning **seven model families
are worth only about two independent votes** — cross-vendor diversity buys far
less independence than it appears to, and it costs every submitter an extra API
key.

The lens split that worked: a design director who sees the render and the brief;
an engineer who sees **only the source**, never the render; and the client who
wrote the brief and is checking whether they got it. Take the median per axis
and **keep the spread** — a wide spread means the artefact is contentious, which
is worth more than the median alone.

## Choosing the judge model

Not by size. Across 21 judges from 9 providers, Cohen's κ ranged 0.376–0.511 and
**model size did not predict judging quality**: a mid-tier model hit κ=0.720 on
one benchmark at a fraction of frontier cost, and a small model beat larger ones
on specific dimensions. Rankings flip by dimension.

What does transfer:

- **The disqualifying profile: weak *and* lenient.** In the frontend audit the
  worst builder was simultaneously the most lenient judge (+6.92) and the most
  self-favouring (+7.04). Keep that profile off the panel.
- **Self-preference is real and measurable**, ranging +7.04 to −1.39 across
  models — three models scored their own work *below* what the panel gave it.
  It matters most when the judge and the thing being judged are the same model,
  which you cannot prevent when anyone may submit anything. You can only move it
  to a less-populated cell.
- **Verbosity bias is effectively solved** — all 21 models under 0.011. Retire
  that worry.

## What you cannot borrow

Published agreement numbers. Cohen's κ is a property of *judge × task × rubric*,
not of the model. A judge validated on chat helpfulness tells you nothing about
judging visual craft. And raw exact-match agreement **overstates the
chance-corrected figure by 33.8–41.3 percentage points**, so a paper reporting
"90% agreement" is not reporting what it sounds like.

Borrow the method, the exclusions, and the retired worries. Do not borrow the
ranking.

## Two traps

**Stability is not validity.** Two models showed test-retest reliability >0.95
*with* position bias >0.10. A judge that is consistently wrong looks perfect on a
variance test. "Score it five times and check the spread" is not a gate.

**Pointwise is the weaker primitive.** Pairwise comparison ("is B better than
A") is more stable than absolute scoring, and a leaderboard's real question is
comparative. Pointwise is the right primitive for an absolute gate and for
debugging; pairwise is the right one for ranking. Choose deliberately.

## Where a judged dimension belongs

Default it to the **diagnostic tier**, unranked. That is not a consolation
prize: unranked means unreproducible-is-fine, which removes the cross-user
median problem and the incentive to game it, and it lets the number be published
and looked at without pretending it settles anything.

Promote to `score` only after measuring the judge's own variance against the
arm-gap you expect to detect — and remember the stability trap above: low
variance is necessary, not sufficient.

One more constraint specific to this platform: `judge.py` runs on the
submitter's machine, so a judged dimension spends *their* money, sends *their*
output to a third party, and turns *their* rate limit into your judging failure.
Make it opt-in and fail soft, and treat the flag as consent.

## What happened when we ran it

The panel described above was built, anchored, and run twice over nine pages
produced from three open briefs by three different labs, authors hidden
throughout. It did not work, and the way it failed is the most useful thing in
this document.

- **It contradicted its own anchors.** Two of the seven calibration screenshots
  sit in the prompt labelled "2". On the second run the panel scored those same
  two images 3.00 and 2.75. When the calibration set does not hold, nothing
  downstream can be read.
- **It did not reproduce the owner's held-out judgments.** Of the four pages kept
  out of the anchor set, the one she called good ranked below two she called bad.
- **Mean swing between the two runs was 0.36 on a 1–3 scale.**
- **The forced choice did not force.** 72 scores: 26 threes, 10 twos, zero ones —
  with two level-1 anchors sitting in the prompt.

Two corrections to what is written above:

**Seven anchors is not "three or four well-chosen examples" scaled up — it is
still too few.** The 20/80 rule is not refuted here; the anchors *were* the 80%,
and they still did not transfer. What this run shows is the floor is higher than
it looks.

**An overall sort cannot calibrate per-axis scores.** That is listed as an honest
limit in the panel's own docstring. This run promoted it from caveat to probable
cause: she ranked pages whole, the panel was asked for `structure` and
`execution` separately, and the anchors said nothing about either.

And one thing that is not a rubric problem at all: **a static image cannot score
a stateful UI.** Three of the nine pages were multi-step form flows whose later
steps do not exist in the DOM until a click. Every screenshot of them is one
viewport tall and shows two of eleven fields. Tiling the capture proved this
rather than fixing it; the actual fix was to **drive** the page — fill the
visible fields, press the thing that says "next", capture each state — which the
inspector now does.

The general form: **before writing a rubric, check that the artefact you hand the
judge contains the thing you are asking about.** This is upstream of every
prompt decision and it is much cheaper to check. A judge scoring `structure` on
a third of a form is not a calibration problem.

Where that leaves the alternative: pairwise is still the better primitive, but
after two failed pointwise runs the honest prerequisite is *more labelled pages*,
not a third prompt shape over the same nine.

## Sources

- Startrise, [LLM-as-a-Judge Bias: The 839-Call Audit](https://www.startrise.io/blog/llm-judge-bias/) and [the benchmark's rubric](https://www.startrise.io/benchmark/)
- [Reliability without Validity: LLM-as-a-Judge across Agreement, Consistency and Bias](https://arxiv.org/html/2606.19544v1) (arXiv 2606.19544)
- [The Coin Flip Judge? Reliability and Bias in LLM-as-a-Judge](https://arxiv.org/pdf/2606.13685) (arXiv 2606.13685)
- The 20/80 rule and the three-point scale come from a practitioner writing about
  ad-copy rubrics on Reddit, not from a paper. Both are consistent with the
  measurements above, which is why they are here.
