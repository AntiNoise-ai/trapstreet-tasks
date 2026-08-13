# core_tool_selection_under_load

Does tool-selection accuracy hold up as the number of available tools grows —
and is any drop actually about *how many* tools are stacked in context, or
just about *where* the right one happens to sit?

## Why this task

A claim has been circulating among agent-builders: naively stacking new
tools/skills into a single runtime causes a 30-50% accuracy regression on
tasks the agent used to handle fine, attributed to "U-shaped attention"
degradation over long context. We went looking for a runnable source for
that number and couldn't find one — every citation we traced led back to
another citation, not a benchmark. So instead of repeating the figure, this
task is the instrument for actually checking it.

Every real case in this repo is one AI agent picking one tool for one
request. Whether that stays reliable as the tool catalog grows from a
handful to a few dozen is directly relevant to anyone building an agent
that accumulates skills/integrations over time — the practical question
isn't "does this model score well on paper", it's "does it still pick the
right tool once I've added 30 more".

## What this task tests

**Given a user request and a catalog of N tool schemas, does the solution
call the one tool that correctly satisfies the request, with correct
arguments?**

Two dimensions are controlled independently so a score drop can be
attributed correctly instead of guessed at:

- **`n_tools`** — catalog size: 4 / 16 / 40 tools (`tier1_n4` / `tier2_n16` / `tier3_n40`)
- **`position`** — where the correct tool sits in the catalog: `early` / `mid` / `late`

The same query, for the same intent, is repeated across all 9 combinations
of size × position — only the surrounding catalog changes. That separates
two different failure stories that get conflated if you only vary catalog
size: "more tools in context genuinely dilutes selection accuracy" vs. "the
correct tool just happened to be less findable at its position" (the
U-shaped-attention hypothesis specifically predicts a position effect, not
just a count effect — this task can tell those apart).

3 intents × 3 sizes × 3 positions = 27 cases. Each of the 3 target tools
(`calculate_percentage`, `convert_distance`, `get_local_time`) is also used
as a plausible-but-wrong distractor for the other two intents' queries.

## Input / output contract

Per case, `inputs/<id>/prompt.txt` contains:
- the full tool catalog as a JSON schema list (`# Available tools`)
- the user request (`# User request`)
- an instruction to output exactly one tool call as JSON

The solution must print **one** JSON object to stdout:
```json
{"name": "<tool_name>", "arguments": {"<arg>": <value>, ...}}
```

## Scoring

Deterministic, no LLM-as-judge. A case scores **1.0** iff the tool name is
an exact match AND every expected argument is present with a value matching
one of the case's accepted values (numeric values compared with tolerance,
strings compared case/whitespace-insensitively) — otherwise **0.0**. No
partial credit: picking one tool out of a catalog doesn't have an orderable
notion of "how close", so binary is the honest scoring model here.

**Anti-shotgun**: if the solution's output is a JSON array (multiple tool
calls), only the *first* element is scored. A solution can't list several
plausible tools and get credit for whichever one turns out right.

**Known limitation**: the tool catalog is synthetic and deliberately
everyday/non-technical (weather, calendar, unit conversion, etc.) so cases
stay graspable without an ML background. This favors clean argument
extraction over messy real-world tool schemas — a real integration surface
with overlapping, ambiguously-named tools would likely be harder than what
this task measures. Treat results here as a lower bound on the effect, not
the full picture.

## Sources & licensing

100% synthetic / hand-authored — see `LICENSE.md`. No external corpus,
dataset, or real tool catalog is used, so there is no leakage risk from
model training data by construction.

## Run

```bash
python3 build_cases.py                 # (re)generate cases
python3 -m pytest tests/ -v            # unit tests
```
