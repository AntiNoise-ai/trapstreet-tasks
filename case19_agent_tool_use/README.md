# Case 19: Agent Tool Use / Function Calling

> Live demo flow for this case: see [DEMO.md](./DEMO.md).

**Concept:** "Every 'autonomous agent' claims to use tools. Did it actually call the right function with the right arguments?"

A user query goes in, along with a list of available functions (name + JSON Schema). The agent must return the correct function call — function name and parameter values. Or correctly *not* call anything when no function applies. This is the foundational sub-step for every "one-person company" agent claim: if function calling fails, every workflow built on top is theater.

---

## Dataset

| Field | Value |
|-------|-------|
| Name | Berkeley Function Calling Leaderboard (BFCL) v4 |
| Curator | Berkeley Sky Computing Lab (Gorilla project) |
| GitHub | https://github.com/ShishirPatil/gorilla/tree/main/berkeley-function-call-leaderboard |
| Live leaderboard | https://gorilla.cs.berkeley.edu/leaderboard.html |
| Paper | ICML 2025 — https://openreview.net/forum?id=2GmDdhBdDk |
| License | Apache 2.0 ✅ |
| Total questions | 5,000+ across 20 categories |

---

## Categories (pick the slice that fits your eval)

The dataset is split by category. Each category targets a specific agentic capability.

| Category | Tests | File (raw URL prefix below) |
|----------|-------|------------------------------|
| `simple_python` | Single function call, Python | `BFCL_v4_simple_python.json` |
| `multiple` | Pick correct function from N options | `BFCL_v4_multiple.json` |
| `parallel` | Multiple calls in one turn | `BFCL_v4_parallel.json` |
| `parallel_multiple` | Multiple calls, pick from N options | `BFCL_v4_parallel_multiple.json` |
| `live_*` | User-contributed real prompts | `BFCL_v4_live_*.json` |
| `irrelevance` | **Should NOT call any function** | `BFCL_v4_irrelevance.json` |
| `live_relevance` | Should call when relevant | `BFCL_v4_live_relevance.json` |
| `multi_turn_base` | Multi-turn tool use | `BFCL_v4_multi_turn_base.json` |
| `multi_turn_long_context` | Long-context multi-turn | `BFCL_v4_multi_turn_long_context.json` |
| `multi_turn_miss_func` | Required function NOT in schema (should refuse) | `BFCL_v4_multi_turn_miss_func.json` |
| `multi_turn_miss_param` | Required argument missing from user input (should ask) | `BFCL_v4_multi_turn_miss_param.json` |
| `simple_java` / `simple_javascript` | Cross-language | `BFCL_v4_simple_java.json` / `_javascript.json` |
| `web_search`, `memory`, `format_sensitivity` | Specialty subsets | matching filenames |

**Where 2026 frontier models still diverge:** `multi_turn_*` and `irrelevance`. Top models ace `simple_*` but split-brain on multi-turn memory and decide-when-not-to-act.

---

## Input / Output Schema

### Input

Each row in `bfcl_eval/data/BFCL_v4_*.json` has:

| Field | Description |
|-------|-------------|
| `id` | Unique identifier (e.g. `"simple_python_0"`) |
| `question` | Doubly-nested array of message objects (for multi-turn support). For single-turn, one `[{"role": "user", "content": "..."}]` |
| `function` | List of available functions — each with `name`, `description`, `parameters` (JSON Schema) |

```json
{
  "id": "simple_python_0",
  "question": [[{"role": "user", "content": "Find the area of a triangle with a base of 10 units and height of 5 units."}]],
  "function": [{
    "name": "calculate_triangle_area",
    "description": "Calculate the area of a triangle given its base and height.",
    "parameters": {
      "type": "dict",
      "properties": {
        "base":   {"type": "integer", "description": "The base of the triangle."},
        "height": {"type": "integer", "description": "The height of the triangle."},
        "unit":   {"type": "string",  "description": "The unit of measure (defaults to 'units' if not specified)"}
      },
      "required": ["base", "height"]
    }
  }]
}
```

### Output (gold)

Gold answers live in a parallel `possible_answer/BFCL_v4_*.json` file. Each parameter has a *list* of acceptable values — the model's call is correct if its arg matches any value in the list. This is the AST grading approach.

```json
{
  "id": "simple_python_0",
  "ground_truth": [
    {"calculate_triangle_area": {"base": [10], "height": [5], "unit": ["units", ""]}}
  ]
}
```

For `irrelevance` rows, the correct behavior is **no function call at all** — the model should respond in natural language.

---

## Data Access

| File | URL |
|------|-----|
| Question + functions (per category) | `https://raw.githubusercontent.com/ShishirPatil/gorilla/main/berkeley-function-call-leaderboard/bfcl_eval/data/BFCL_v4_<category>.json` |
| Gold ground truth (per category) | `https://raw.githubusercontent.com/ShishirPatil/gorilla/main/berkeley-function-call-leaderboard/bfcl_eval/data/possible_answer/BFCL_v4_<category>.json` |

> **Do NOT use HuggingFace `load_dataset()`** — the dataset isn't HF-compatible. Read the JSON files directly.

```python
import json, urllib.request

def load_jsonl(url):
    with urllib.request.urlopen(url) as f:
        return [json.loads(line) for line in f]

CAT = "simple_python"
BASE = "https://raw.githubusercontent.com/ShishirPatil/gorilla/main/berkeley-function-call-leaderboard/bfcl_eval/data"

questions = load_jsonl(f"{BASE}/BFCL_v4_{CAT}.json")
answers   = {a["id"]: a["ground_truth"] for a in load_jsonl(f"{BASE}/possible_answer/BFCL_v4_{CAT}.json")}

row = questions[0]
input_messages = row["question"][0]      # → user messages
input_functions = row["function"]        # → tool schema for the model
gold = answers[row["id"]]                # → list of accepted function calls

# Send (input_messages, input_functions) to the model. Compare its function call to gold.
```

---

## Eval Notes

- **Grading:** AST-based — parse the model's call, check function name matches, check each arg matches an accepted value in the gold list. The official Gorilla repo ships a runnable evaluator (`bfcl-eval` CLI). Reuse it rather than re-implementing.
- **Headline metrics (track separately, don't average):**
  - **Simple-call accuracy** — solved by 2026 frontier models; included for baseline
  - **Multi-turn accuracy** — where the real divergence is
  - **Irrelevance / relevance accuracy** — measures "decide when not to act," the silent failure mode
  - **Hallucinated function rate** — model invented a function name not in the schema. Catastrophic in production.
- **2026 leaderboard snapshot (overall):** Llama 3.1 405B 88.5% • Claude Opus 4.1 70% • GPT-5 59% — ~30 percentage points of real signal between top models on the same questions.
- **Why span-level matters here:** the value of an "AI agent" isn't "yes, it called something" — it's "did it call the right thing with the right args." A wrong arg in production is a wrong booking, a wrong charge, a wrong email recipient.
- **Watch for:** safety-tuned products that refuse to call any function. Track refusal rate separately — it's not the same failure as a wrong call, but it's not a success either.
