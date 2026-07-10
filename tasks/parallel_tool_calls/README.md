# parallel_tool_calls — Can the Model Plan Multiple Tool Calls at Once?

An open-source evaluation task for **multi-tool orchestration** — given a user request that requires multiple tool calls, does the model correctly identify which tools to call and with what arguments?

Useful as a basic sanity check when building AI agents that chain tool calls: task-executing agents, multi-step assistants, workflow automators, code agents that combine multiple operations.

20 cases sampled from Berkeley Function Calling Leaderboard (BFCL) parallel non-live subset.

## What this task tests

**Given a user request like "Play Taylor Swift for 20 minutes AND Maroon 5 for 15 minutes on Spotify", can the model produce a correct list of parallel tool calls (2 different `spotify.play` calls with the right args)?**

Real agent failure modes this exposes:

1. **Wrong number of calls** — Model outputs 1 call when 2 were needed, or 3 when 2 were needed
2. **Wrong function selected** — Model picks a similar-but-wrong tool from the pool
3. **Wrong arguments** — Right function, wrong values (Taylor Swift → 15 min instead of 20 min)
4. **Formatting errors** — Model outputs prose instead of clean JSON, or wraps in markdown fences

## Case structure

| Difficulty | Cases | # of parallel calls | What it tests |
|---|---|---|---|
| **short** | 6 | 2 | Baseline — recognize 2 calls needed |
| **medium** | 8 | 3 | 3 parallel calls — order-independent set |
| **long** | 6 | 4 | 4 parallel calls — largest scope |

Each case has 15+ available tools; the model must pick the right N and configure each correctly. Tool schemas are provided in the input prompt as JSON.

## Input

Per case:
- `INPUTS["question.txt"]` — user request + available tool schemas (JSON) + instruction to output JSON array of tool calls

Example prompt structure:
```
# Available tools
[{"name": "spotify.play", "description": "...", "parameters": {...}}, ...]

# User request
Play songs from Taylor Swift for 20 min and Maroon 5 for 15 min on Spotify.

# Your task
Output a JSON array of tool calls to execute.
```

## Expected output

A JSON array of tool call objects:
```json
[
  {"name": "spotify.play", "arguments": {"artist": "Taylor Swift", "duration": 20}},
  {"name": "spotify.play", "arguments": {"artist": "Maroon 5", "duration": 15}}
]
```

The judge enforces:
- `parallel_tool_calls` — parses agent JSON, matches each call to ground truth (set-based, order doesn't matter, args must be in accepted values list)
- `no_hedge` — rejects "I can't help with that" responses

Each case scores 1.0 / 0.0. Run passes if ≥80% pass.

## Judge match rules

Each ground truth call is `{"func_name": {"arg1": [acc_val1, acc_val2, ...]}}` — args have LISTS of accepted values because natural language can map to multiple valid representations ("California" and "CA" both fine).

For a match:
- Function name matches exactly
- Each required arg's value is in the accepted values list (with int/float coercion, case-insensitive string, list-equality)
- Args with `""` in accepted list can be omitted

Matches are set-based: agent calls need to cover all ground truth calls, but order doesn't matter (these are parallel calls).

## Why this is hard

- **Tool selection under distraction.** 15+ tools available, only 2-4 relevant. Model can pick similar-looking wrong tool.
- **Argument extraction from natural language.** "For 20 minutes" → `duration: 20`. Easy if the pattern is stated cleanly, tricky when phrasing is loose.
- **Multi-value support.** Natural language ambiguity means "Los Angeles" and "LA" both refer to the same city — model outputs may match some but not others.
- **JSON formatting.** Agents that wrap output in markdown fences, add explanation, or output tool calls in a non-standard schema fail here.

## Cost

Per case: input includes tool schemas (~500-2000 tokens) + user request (~50 tokens). Output is 20-200 tokens. Full 20-case run: **~$0.05-0.50 depending on model**.

## Honest limitations

- **Parallel calls only, not sequential loops.** Cases assume all calls can execute in parallel (agent outputs them all at once). Real agent workflows often have call-response-next-call loops. This tests planning, not runtime iteration.
- **No real tool execution.** Agent's calls are graded against ground truth, not executed. A real tool-use loop would run each call, feed the response back, and iterate. That would require a full mock environment.
- **BFCL contamination risk.** BFCL is a well-known benchmark; models may have seen it in training. However the specific parallel test cases used here are not published widely.
- **Argument matching heuristic.** The judge accepts case-insensitive and numeric-coerced matches but may be over-strict for some semantic-equivalent phrasings.

## Data source & license

20 cases sampled from `hjshah/bfcl_non_live_parallel` on HuggingFace (Apache 2.0, derived from Berkeley Function Calling Leaderboard v3). See [LICENSE.md](LICENSE.md).
