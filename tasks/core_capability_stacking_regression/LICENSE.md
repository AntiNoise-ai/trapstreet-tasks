# Sources & licensing

Every artifact in this task is original and hand-authored for it.

| Component | Source | Licence |
|---|---|---|
| `catalog.json` — 8 base skills, 3 high-overlap packs, 3 low-overlap packs (44 schemas) | written for this task | original |
| `filler_pool.json` — 100 bulk skills added at L4 to both arms | templated by `gen_filler.py` for this task | original |
| `scenarios.json` — 6 office-automation jobs and their expected calls | written for this task | original |
| `inputs/`, `expected/` | generated from the two files above | original |

No external corpus, dataset, API specification or real tool catalog was used.
No real product, company or service names appear in any schema or request. The
people named in the requests (Priya, Marco, Dana Whitfield, Rob, Aisha) are
invented.

Two consequences worth stating plainly:

- **No third-party material.** There is no external corpus here to have been
  trained on. One narrower caveat is ours rather than anyone else's: an earlier
  draft reused a request and several tool descriptions close to verbatim from
  `core_tool_selection_at_scale`, whose README is public. Those were rewritten,
  but the two catalogs stay thematically adjacent, so "zero leakage" overstates
  it.
- **The credibility case has to be made, not assumed.** Synthetic material buys
  freedom from leakage at the cost of having to argue that performance here
  predicts performance on real skill catalogs. The argument this task rests on
  is that the schemas read like real MCP / OpenAPI tool definitions —
  advertising what they are for rather than confessing what they are not — and
  that each wrong answer is ruled out by a consequence the reader has to derive
  from that advertising, not by being obviously unrelated. A reader who
  disagrees can check directly: every high-overlap skill's `disqualifier` field
  records the inference required, and no competitor description states its own
  limitation.
