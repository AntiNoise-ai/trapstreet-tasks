"""Generate inputs/<id>/... and expected/<id>/answer.json from
gold.cases.json, validating authoring invariants first.

Run:  python3 build_cases.py
inputs/ and expected/ are GENERATED -- never edit them by hand.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOLD = HERE / "gold.cases.json"

REQUIRED_FIELDS = [
    "id", "intent", "query", "tool_catalog", "correct_tool_name",
    "expected_args", "n_tools", "position", "position_index", "category",
]

PROMPT_TEMPLATE = """You are an AI agent that selects exactly one tool to call to satisfy a user request.

# Available tools

```json
{tools_json}
```

# User request

{query}

# Your task

Output ONLY a single JSON object of the form:
{{"name": "<tool_name>", "arguments": {{"<arg>": <value>, ...}}}}

Call exactly one tool -- the one that correctly satisfies the request. Output
ONLY the JSON object. No explanation, no markdown fences, no array.
"""


def validate_case(case: dict) -> None:
    """Fail loudly on authoring mistakes -- this is what keeps the N/position
    dimensions actually controlled instead of silently confounded."""
    missing = [f for f in REQUIRED_FIELDS if f not in case]
    if missing:
        raise ValueError(f"case {case.get('id', '?')}: missing fields {missing}")

    catalog = case["tool_catalog"]
    n_tools = case["n_tools"]
    if len(catalog) != n_tools:
        raise ValueError(
            f"case {case['id']}: n_tools={n_tools} but tool_catalog has {len(catalog)} entries"
        )

    names = [t["name"] for t in catalog]
    if len(names) != len(set(names)):
        dupes = {n for n in names if names.count(n) > 1}
        raise ValueError(f"case {case['id']}: duplicate tool name(s) in catalog: {dupes}")

    correct = case["correct_tool_name"]
    if names.count(correct) != 1:
        raise ValueError(
            f"case {case['id']}: correct_tool_name {correct!r} must appear exactly once "
            f"in tool_catalog, found {names.count(correct)}"
        )

    idx = case["position_index"]
    if not (0 <= idx < n_tools):
        raise ValueError(f"case {case['id']}: position_index {idx} out of range for n_tools={n_tools}")
    if names[idx] != correct:
        raise ValueError(
            f"case {case['id']}: tool_catalog[{idx}] is {names[idx]!r}, expected correct_tool_name "
            f"{correct!r} at that index -- position control is broken for this case"
        )

    if case["position"] not in ("early", "mid", "late"):
        raise ValueError(f"case {case['id']}: position must be early/mid/late, got {case['position']!r}")

    if not case["expected_args"] or not isinstance(case["expected_args"], dict):
        raise ValueError(f"case {case['id']}: expected_args must be a non-empty dict")
    for arg_name, accepted in case["expected_args"].items():
        if not isinstance(accepted, list) or not accepted:
            raise ValueError(
                f"case {case['id']}: expected_args[{arg_name!r}] must be a non-empty list of accepted values"
            )

    # Every tool in the catalog must itself be well-formed enough to show a
    # solution -- catches copy-paste mistakes in the filler pool.
    for t in catalog:
        if "name" not in t or "description" not in t or "parameters" not in t:
            raise ValueError(f"case {case['id']}: malformed tool schema entry: {t}")


def render_prompt(case: dict) -> str:
    tools_json = json.dumps(case["tool_catalog"], indent=2)
    return PROMPT_TEMPLATE.format(tools_json=tools_json, query=case["query"])


def build() -> None:
    data = json.loads(GOLD.read_text())
    seen_ids: set[str] = set()
    for case in data["cases"]:
        validate_case(case)
        cid = case["id"]
        if cid in seen_ids:
            raise ValueError(f"duplicate case id: {cid}")
        seen_ids.add(cid)

        in_dir = HERE / "inputs" / cid
        in_dir.mkdir(parents=True, exist_ok=True)
        (in_dir / "prompt.txt").write_text(render_prompt(case))

        exp_dir = HERE / "expected" / cid
        exp_dir.mkdir(parents=True, exist_ok=True)
        answer = {
            "id": cid,
            "correct_tool_name": case["correct_tool_name"],
            "expected_args": case["expected_args"],
            "n_tools": case["n_tools"],
            "position": case["position"],
            "position_index": case["position_index"],
            "intent": case["intent"],
            "category": case["category"],
        }
        (exp_dir / "answer.json").write_text(json.dumps(answer, indent=2))

    print(f"Built {len(data['cases'])} cases.")


if __name__ == "__main__":
    build()
