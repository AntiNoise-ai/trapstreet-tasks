# influencer_marketing_disclosure

Given a self-contained influencer/creator-partnership scenario, the solution
must give correct guidance on the parts of influencer marketing that have
actual right answers: whether FTC disclosure is required, how to set up
attribution when links aren't clickable, whether to write a verbatim script
(don't), and whether to just pay a macro creator's flat rate without
negotiating terms (don't do that either). Like `ab_test_planning`, scoring
is scoped to the objective core of the discipline, not the parts where two
competent practitioners could reasonably disagree.

## Why this task

Same motivation as `ab_test_planning`: test whether a community "influencer
marketing" Claude Skill adds real value over a bare model, not whether it
produces plausible-sounding advice (any frontier model can do that). Four
skills are being compared, plus a no-skill baseline:

- `coreyhaines31/marketingskills` — `skills/influencer-marketing` (the
  newest skill in that repo as of this task's design, 1.0.0)
- `nexscope-ai/eCommerce-Skills` — `tiktok-influencer-marketing`
- `mohitagw15856/pm-claude-skills` — `skills/influencer-brief`
- `cgallic/kai-cmo-harness` — `harness/skills/kai-influencer`
- `baseline-no-skill` — bare model, no system prompt

Two honest notes about this lineup, found by reading each skill's actual
content before writing a single case (same discipline as `ab_test_planning`):

- **Unlike the ab-testing lineup, these four are NOT near-clones of each
  other.** A keyword scan of each skill's disclosure/FTC/gifting coverage
  found real, structural differences: `nexscope-ai`'s skill has **zero**
  mentions of disclosure, FTC, or gifting anywhere in it — a genuine content
  gap, not a manufactured one, and it should show up directly on the
  `gifting_disclosure` cases below. `mohitagw15856` and `cgallic` both cover
  disclosure to varying depth. This should make skill-vs-skill separation
  easier here than it was for ab-testing's forked-template problem.
- **`mohitagw15856/influencer-brief` has a narrower job-to-be-done** than
  the other three — it's specifically a campaign-*brief-document generator*,
  not a full advisory skill across sourcing/vetting/deal-structuring. Worth
  watching in particular on the `no_script` cases: a skill whose entire
  purpose is producing detailed creator briefs could plausibly lean toward
  over-specifying wording rather than correctly declining a literal
  word-for-word script request. That's a real thing to observe, not
  something to editorialize about in the scoring.

## Input / output contract

`inputs/<id>/question.txt` is a self-contained prompt: role framing, a
realistic creator-partnership scenario, and the exact required JSON output
shape. The solution must print **only** a JSON object to stdout:

```json
{
  "requires_disclosure": true,
  "findings": [
    {"description": "free-text recommendation, caution, or correction"}
  ]
}
```

`requires_disclosure` asks whether the situation described involves a
material connection (payment, free product, family/personal relationship,
or any other benefit) that requires disclosure under FTC endorsement
guidelines. Only the first 5 `findings` entries are scored, stated in the
prompt.

## Scoring

Fully deterministic, no LLM judge (`judge.py`). Each case scores 0.0–1.0
across two components:

- **0.4 — disclosure fact.** `requires_disclosure` correctly identified.
  This is a real FTC Endorsement Guide fact, not a matter of opinion: any
  material connection between a brand and a creator — payment, free
  product/gifting, a family or personal relationship, even a free trial —
  requires disclosure. Only a genuinely unprompted, uncompensated post
  (no product, no payment, no relationship the brand orchestrated) does
  not. This task tests against these well-established, stable Endorsement
  Guide basics — the same facts already stated correctly in every skill's
  own source material where covered — not novel or contested legal
  interpretation. It is not a substitute for legal advice.
- **0.6 — trap handling.** Every case belongs to one of five categories:
  - `gifting_disclosure` (3 cases) — the scenario describes a free-product,
    free-service, or family/personal arrangement where the team assumes no
    disclosure is needed because "nothing was paid." Full credit requires a
    finding matching a curated phrase list around "not a loophole,"
    "material connection," "clear and conspicuous," etc.
  - `attribution` (2 cases) — a podcast or video sponsorship where the
    naive plan (just watch for link clicks) misses the real attribution
    picture. Full credit requires recommending unique promo codes, UTM
    links, vanity URLs, or a post-purchase survey.
  - `no_script` (2 cases) — the team asks for a literal word-for-word
    script. Full credit requires declining and offering a brief structure
    instead (talking points, creative freedom).
  - `macro_flat_fee` (2 cases) — a naive flat-fee-only deal with a large
    creator, no other terms discussed. Full credit requires recommending
    hybrid compensation, usage rights/whitelisting, or a micro/nano
    portfolio alternative.
  - `clean_control` (2 cases: one genuinely unprompted organic advocate
    with zero material connection, one already-correctly-run gifting
    program asked a different, unrelated question) — full credit requires
    **not** raising any of the four trap warnings above. This is the
    precision check: a solution that reflexively raises every trap on
    every response scores well on the 9 trap cases but fails both
    `clean_control` cases, so blanket shotgunning nets out worse than
    staying quiet when the situation is already handled correctly.

**Known ceiling, stated plainly:** phrase matching cannot distinguish
"correctly flags the issue" from "mentions the issue while denying it
applies" — the same structural limitation documented in `ab_test_planning`
(see `tests/test_judge.py`'s `test_disclaiming_sentence_does_not_false_match`,
which documents this rather than pretending it's solved).

Things this task deliberately does **not** grade: creator-tier compensation
range accuracy (published rates vary too widely by niche/geography to have
a single right answer), vetting-checklist completeness beyond the fake-
follower/engagement-quality core, ambassador-program design quality, or
outreach message tone. Scoring is scoped to the four traps above plus the
disclosure fact.

## Sources & licensing

Every scenario is 100% original — fictional brands, creators, and
situations, not sourced from Corey Haines' own 6 published eval prompts or
anywhere else. The disclosure *rules* a correct answer must state (material
connection, clear-and-conspicuous placement, brand liability, gifting is
not exempt) are drawn from well-established, publicly available FTC
Endorsement Guide principles — public regulatory information, not anyone's
proprietary content, and not obscure or unsettled law. Zero leakage risk on
the scenarios (nothing to have been seen in training) and zero IP exposure.

## Run

```bash
python3 build_cases.py                 # (re)generate inputs/ + expected/ from gold.cases.json
python3 -m pytest tests/ -v            # unit tests (30 cases: build validation + judge scoring + exploits)
```
