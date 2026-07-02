# core_json_schema_output — Output Strict JSON Matching a Schema

Part of TrapStreet's **Foundation 11** — basic mechanics every AI agent needs.

A trap-compatible task that tests whether a model can produce **valid JSON conforming to a given function-call schema**. 20 cases from the Berkeley Function Calling Leaderboard (BFCL).

## What this task tests

**Can the model output JSON that's both syntactically valid AND semantically correct against a schema?**

This is the single most common failure mode in production agent stacks: model returns prose, or returns markdown-wrapped JSON, or returns JSON with the wrong field names, or with a value of the wrong type. Every LangChain / LangGraph / AutoGen / OpenAI Tools build needs this to work reliably.

If a model fails this task, almost no agent framework built on top of it will work without a wrapper / retry loop / custom prompting.

## Case structure

| Difficulty | Count | What's different |
|---|---|---|
| **easy** | 10 | Every gold arg has exactly one accepted value — strict match |
| **medium** | 10 | At least one gold arg has multiple accepted values (e.g. optional defaults, alternate phrasings) — tests whether model can handle "the optional `unit` param can be omitted OR set to `units`" correctly |

Functions span calculator-style operations: triangle area, quadratic roots, kinematics, finance, physics.

## Input

Per case:
- `INPUTS["question.txt"]` — user natural-language request + the function spec as JSON

## Expected output

ONE JSON object on stdout, formatted as:

```json
{"name": "<function_name>", "arguments": {"<arg>": <value>, ...}}
```

No explanation, no markdown fences, no preamble.

## Judge: `json_call` matcher

A custom matcher (added to `judge.py` for this task) that:

1. Strips optional ` ```json ` markdown fences before parsing
2. Parses the answer as JSON via `json.loads()` — invalid JSON → fail
3. Verifies the top-level key `name` (or `function` / `function_name`) matches the gold function exactly
4. For each gold-required arg:
   - Model's value must be in the gold's `args_accepted` list (with int/float numeric coercion)
   - If `""` is in the accepted list, the arg can also be omitted (optional default)
5. Extra args in model's call are NOT penalised
6. Wrapped with `no_hedge` rejection on top

Each case scores 1.0 / 0.0. Run passes if ≥80% pass.

## Why this is hard

Looks trivial — until you actually try it. Common failure modes:

- Model wraps output in ` ```json fences ` (judge strips, model recovers — but only the first level)
- Model returns multi-key JSON like `{"function_call": {...}, "explanation": "..."}` (wrong structure)
- Model uses `parameters` instead of `arguments` (judge accepts both)
- Model coerces `int 10` to `string "10"` (judge does numeric coercion BOTH ways but only for int/float, not string-int)
- Model omits the optional param when gold's list has `""` AND a real value — judge allows
- Model invents a `unit: "meters"` when gold accepts only `["units", ""]` — fail

## Cost

20 small text-only cases. ~$0.02-0.10 per full run on most models. Cheapest task in TrapStreet.

## Honest limitations

- **Single function call only** (BFCL's `simple_python` subset). Real agent workflows often need multi-step / multi-function / nested calls — BFCL has those (`parallel`, `multiple`, `multi_turn`) but they're harder to grade strictly.
- **Python-style schemas only.** A v2 should also test BFCL's `java` and `javascript` variants since type system differences matter.
- **No tool-call FORMAT diversity.** Models trained to use OpenAI's tool-call format, Anthropic's tool_use, or generic JSON all converge to a similar output but real production code needs to parse multiple wrappers. This eval tests the underlying capability, not the wrapper-specific format.

## Data source & license

All 20 cases are sampled from BFCL v4 `simple_python` (Apache 2.0). See [LICENSE.md](LICENSE.md).
