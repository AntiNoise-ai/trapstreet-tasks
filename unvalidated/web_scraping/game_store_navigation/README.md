# game_store_navigation

10 questions about a small, entirely original game-storefront mock site
("NebulaKey Store") that solvers must scrape or browser-automate to
answer. Unlike a static-document reading task, several cases can only be
answered by actually executing the page's JavaScript, clicking through UI
state, reading pixels in an image, or persisting state across page loads
-- the point is to discriminate solutions that just fetch raw HTML from
ones that genuinely render/interact with the page, the same distinction
that separates DOM-parsing scrapers (Crawl4AI, ScrapeGraphAI-style) from
vision/interaction-driven browser agents (browser-use, Skyvern-style).

## Why this task

TrapStreet compares community tool approaches on realistic workflow
sub-tasks, not raw model QA. "Scrape this site and answer a question" is
one of the most common real uses of an AI agent, and the interesting
axis isn't "which model is smartest" -- it's "which scraping/automation
*approach* actually works on a page that isn't just static text." Each
case here is designed around one specific thing a pure-HTML-fetch
approach cannot see:

| case | what a static-HTML-only fetch would miss |
|---|---|
| case_01 | catalog is rendered by JS from a token-gated `games.json` -- nothing renders, and the data endpoint 403s, without executing the page |
| case_02 | the sale price is computed from a token-gated `flash-sale.json`, not printed in the HTML and not sitting in a data attribute either |
| case_03 | the discount is pixels in a PNG banner, not text, alt text, or any fetchable data file |
| case_04, case_05 | tier prices/contents come from a token-gated endpoint, fetched only after a button click |
| case_06 | needs correctly disambiguating two similarly-named bundles, each behind its own token-gated endpoint |
| case_07 | needs cross-referencing a game's detail page (DLC) against a separately-listed edition -- deliberately NOT token-gated; see "Why case_07 isn't gated" below |
| case_08 | needs applying filter + sort controls against the token-gated catalog endpoint, updating the DOM without a page reload |
| case_09 | catalog is paginated against the token-gated endpoint; the full answer requires paging through all of it |
| case_10 | price depends on a token-gated `regions.json` + a region selector whose state persists via localStorage across page loads |

### Why a naive scraper actually fails here (and why it didn't at first)

The first version of this task looked JS-gated but wasn't: `games.json`,
`bundle-data*.json`, and the region conversion table in `common.js` were
all directly, unauthenticatedly fetchable static files sitting next to
the HTML -- a scraper that never executed a line of JS could just `curl`
them by their predictable filenames and answer 9 of 10 cases perfectly
(verified empirically; only case_03's image stayed genuinely un-bypassable
by text alone).

The fix, `serve.py`: every HTML page gets a fresh, random session token
injected into a `<script>` tag at serve time (regenerated each server
run, never committed anywhere); the page's own JS sends that token back
as an `X-Nk-Token` header on every fetch to the data endpoints
(`games.json`, `bundle-data.json`, `bundle-data2.json`, `regions.json`,
`flash-sale.json`); the server rejects any request to those paths
without the matching header. A bare `curl <filename>` now gets a 403.

This is deliberately *not* meant to be unbeatable -- it mirrors a real
site's CSRF/session-token-gated internal API, which a sufficiently
determined scraper can still defeat by reading the HTML/JS and replaying
the token correctly (verified: extracting the token from `index.html`
and replaying it via `curl -H "X-Nk-Token: ..."` still works). The point
is to filter out the naive case (guess a filename, fetch it directly)
while staying completely transparent to anything that actually executes
the page (a real browser needs to do nothing extra to get the header
right) -- the same gap that separates a thorough scraper from a naive
one in the real world.

`serve.py` never prints the token to its own stdout/stderr (only "Serving
NebulaKey Store at ..."). This matters because the solution process is
usually the one that launches `serve.py` in the first place -- if the
token appeared in the launcher's own console output, reading it back from
the child process's stdout would be a lower-effort bypass than the
HTML-parsing one above, undoing the point of gating it at all.

### Why case_07 isn't gated

Product prices on a real storefront's own page are ordinary, publicly
visible information -- any visitor sees them without logging in or
executing anything special. Gating them would be unrealistic (real sites
don't hide their own prices from visitors) and wouldn't test anything
useful; case_07's actual discriminator is correctly finding and combining
three numbers spread across a page, not scraping architecture.

## Provenance

**100% original, synthetic content.** "NebulaKey Store" and every game,
studio, and bundle name in it are invented for this task -- nothing is
scraped from or references any real storefront, game, or company. This
sidesteps ToS/copyright questions around scraping or reproducing a real
site's content, and keeps the ground truth permanently stable (a real
site's prices/catalog would drift and break this task's answers over
time). See `references/ground-truth-sourcing.md` (trapstreet-task-scaffold
skill) -- synthetic data trades zero leakage/licensing risk for the
authoring effort of making it feel authentic; the tiered-bundle and
region-pricing mechanics here are modeled on real storefront patterns
(Fanatical/Humble-style "pay more, unlock more tiers" bundles with
non-linear per-item pricing; Steam-style per-region storefront pricing)
without copying any real bundle, price, or catalog.

## Input / output contract

Each case's `inputs/<id>/` contains a full, self-contained copy of the
site's static files (HTML/CSS/JS/JSON/one PNG) plus `serve.py` and
`question.txt`. The solver must:

1. Start a local server (`python3 serve.py`, or pass a port number) --
   the site's fetch()-based pages need `http://`, not `file://`.
2. Navigate/scrape the site however it likes (DOM parsing, a headless
   browser, a vision-driven agent -- the task doesn't care) to answer the
   question in `question.txt`.
3. Print **only the final numeric answer** to stdout -- a bare number,
   optionally with a leading currency symbol ($ or €). No extra prose.

## Scoring

`judge.py` extracts the first *qualifying* number from stdout and compares
it to gold with 1% relative tolerance. "Qualifying" excludes any number
that already appears in the question text (e.g. "top tier" language was
chosen specifically to avoid a case where a literal "Tier 3" in the
question would otherwise collide with a same-valued answer -- see
`build_cases.py`'s docstring and `tests/test_judge.py`'s
`test_known_limitation_...` test). It also accepts either the literal or
magnitude-scaled reading of a number with a trailing unit word (e.g.
"$5,466 million" when gold is a bare, already-in-millions number).

This logic -- and both of those specific fixes -- is carried over from
this repo's `financebench` task, which found the same "first number wins"
matcher breaks on realistic answer phrasing (see
`tasks/financebench/README.md`, "First qualifying number").

**Known limitation:** if a case's gold answer's numeric value happens to
coincide with a number already in the question, the exclusion logic
treats *every* occurrence of that value as a confound -- including a
correct answer, if the response never restates the figure any other way.
This fails closed (never a false positive from a solver just echoing the
question) at the cost of such cases being permanently unscoreable. The
fix applied here was to avoid the collision at the question-authoring
level (case_05, case_06) rather than rely on this behavior.

**Fourth bug, specific to this task:** case_08 and case_09 are the first
cases in this repo whose question wording itself contains a percent
("rated 90% or higher"). `is_pct` was originally computed once for the
whole prediction string; a solver restating that filter before its real
dollar answer got the unrelated "90" misread as 0.9 and scored a false
miss. Fixed by scoping `is_pct` to each matched number's own tail (same
principle as the magnitude-scale check) and by having the confound set
include the percent-scaled reading of any question-side number followed
by '%', not just its literal value. See
`tests/test_judge.py::test_restated_percent_from_question_does_not_get_misread_as_the_answer`.

No `grader.py` customization beyond pointing its category breakdown at
`mechanism` (the field `judge.py`'s `score_case()` emits) -- the
aggregation logic itself is the same as every other task in this repo.

## Run

```bash
python3 build_cases.py                 # (re)generate inputs/ + expected/ from gold.cases.json
python3 -m pytest tests/ -v            # unit tests
```
